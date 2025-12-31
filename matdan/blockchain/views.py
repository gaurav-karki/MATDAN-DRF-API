"""
Blockchain API Views

These views expose blockchain functionality through REST API endpoints.

ENDPOINT SUMMARY:
    GET  /api/v1/blockchain/status/                    - Check connection
    POST /api/v1/blockchain/elections/<id>/sync/       - Sync election to blockchain
    POST /api/v1/blockchain/elections/<id>/activate/   - Activate/deactivate election
    GET  /api/v1/blockchain/elections/<id>/results/    - Get results from blockchain
    GET  /api/v1/blockchain/votes/verify/              - Verify a vote
"""

import logging
import time

from django.shortcuts import get_object_or_404
from elections.models import Candidate, Election
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    BlockchainConnectionError,
    ContractNotLoadedError,
    get_blockchain_service,
)

logger = logging.getLogger("blockchain")


class BlockchainStatusView(APIView):
    """
    GET /api/v1/blockchain/status/

    Check blockchain connection status.
    No authentication required - useful for health checks.

    Response:
    {
        "status": "success",
        "data": {
            "connected": true,
            "chain_id": 1337,
            "latest_block": 42,
            "contract_loaded": true,
            ...
        }
    }
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        logger.info("Blockchain status check requested.")
        try:
            service = get_blockchain_service()
            status_data = service.get_status()

            logger.debug(f"Blockchain status data: {status_data}")
            return Response(
                {
                    "status": "success",
                    "message": "Blockchain connection status",
                    "data": status_data,
                }
            )

        except BlockchainConnectionError as e:
            logger.exception("Blockchain connection failed.")
            return Response(
                {
                    "status": "error",
                    "message": f"Cannot connect to blockchain: {str(e)}",
                    "data": {"connected": False, "error": str(e)},
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        except Exception as e:
            logger.exception("Unhandled error in BlockchainStatusView")
            return Response(
                {
                    "status": "error",
                    "message": "Internal service error.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SyncElectionToBlockchainView(APIView):
    """
    POST /api/v1/blockchain/elections/<election_id>/sync/

    Sync an election and its candidates to the blockchain.

    WORKFLOW:
    1. Get election from Django database
    2. Create election on blockchain
    3. Add each candidate to blockchain
    4. Save blockchain IDs to Django models

    Only admins can call this endpoint.

    Response:
    {
        "status": "success",
        "message": "Election synced to blockchain",
        "data": {
            "election": {"id": "...", "tx_hash": "0x..."},
            "candidates": [
                {"id": "...", "blockchain_id": 1, "tx_hash": "0x..."},
                ...
            ]
        }
    }
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request, election_id):
        # Get election from Django
        election = get_object_or_404(Election, pk=election_id)
        logger.info(f"Sync election started | election_id = {election_id}")

        # CHECK IF ALREADY SYNCED
        if election.blockchain_synced:
            logger.warning(
                f"Election already synced to blockchain | election_id={election_id}"
            )
            return Response(
                {
                    "status": "error",
                    "message": "This election has already been synced to the blockchain",
                    "data": {
                        "election_id": str(election.id),
                        "blockchain_tx": election.blockchain_tx,
                        "synced": True,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = get_blockchain_service()
        except (BlockchainConnectionError, ContractNotLoadedError) as e:
            logger.exception("Blockchain connection failed.")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        results = {"election": None, "candidates": [], "errors": []}

        # Step 1: Create election on blockchain
        success, tx_result = service.create_election(str(election.id), election.title)

        if success:
            logger.info(
                f"Election created on blockchain | election_id={election.id} | tx={tx_result}"
            )
            # Mark as synced and save transaction hash
            election.blockchain_synced = True
            election.blockchain_tx = tx_result
            election.save()

            results["election"] = {
                "id": str(election.id),
                "title": election.title,
                "tx_hash": tx_result,
            }
        else:
            logger.error(
                f"Election creation failed | election_id={election.id} | error={tx_result}"
            )
            return Response(
                {
                    "status": "error",
                    "message": f"Failed to create election on blockchain: {tx_result}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Step 2: Add each candidate
        candidates = election.candidates.all()

        for idx, candidate in enumerate(candidates, start=1):
            blockchain_id = idx  # Use sequential IDs: 1, 2, 3, ...
            success, tx_result = service.add_candidate(
                str(election.id), blockchain_id, candidate.name, candidate.party
            )

            if success:
                # Save blockchain ID to Django model
                candidate.blockchain_id = blockchain_id
                candidate.blockchain_tx = tx_result
                candidate.save()

                logger.info(
                    f"Candidate synced | candidate_id={candidate.id} | blockchain_id={blockchain_id}"
                )
                results["candidates"].append(
                    {
                        "id": str(candidate.id),
                        "name": candidate.name,
                        "blockchain_id": blockchain_id,
                        "tx_hash": tx_result,
                    }
                )
            else:
                logger.warning(
                    f"Candidate sync failed | candidate_id={candidate.id} | error={tx_result}"
                )
                results["errors"].append(
                    {
                        "candidate_id": str(candidate.id),
                        "name": candidate.name,
                        "error": tx_result,
                    }
                )

        return Response(
            {
                "status": "success",
                "message": "Election synced to blockchain",
                "data": results,
            },
            status=status.HTTP_201_CREATED,
        )


class BlockchainElectionStatusView(APIView):
    """
    POST /api/v1/blockchain/elections/<election_id>/activate/

    Activate or deactivate an election on the blockchain.

    Request body:
    {
        "is_active": true   // or false
    }

    Response:
    {
        "status": "success",
        "message": "Election activated",
        "data": {"tx_hash": "0x..."}
    }
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        is_active = request.data.get("is_active", True)
        logger.info(
            f"Election status change requested | election_id={election_id} | is_active={is_active}"
        )
        try:
            service = get_blockchain_service()
        except (BlockchainConnectionError, ContractNotLoadedError) as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        success, result = service.set_election_status(str(election.id), is_active)

        if success:
            # Also update Django model
            election.is_active = is_active
            election.blockchain_tx = result
            election.blockchain_synced = True
            election.save()

            action = "activated" if is_active else "deactivated"
            logger.info(
                f"Election status updated | election_id={election.id} | tx={result}"
            )
            return Response(
                {
                    "status": "success",
                    "message": f"Election {action}",
                    "data": {"tx_hash": result},
                }
            )
        else:
            logger.error(
                f"Election status update failed | election_id={election.id} | error={result}"
            )
            return Response(
                {"status": "error", "message": result},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BlockchainResultsView(APIView):
    """
    GET /api/v1/blockchain/elections/<election_id>/results/

    Get election results directly from the blockchain.

    This provides tamper-proof verification of results.
    Anyone can view results (no auth required).

    Response:
    {
        "status": "success",
        "data": {
            "election": {...},
            "results": [
                {"id": 1, "name": "...", "party": "...", "vote_count": 150},
                ...
            ],
            "source": "blockchain"
        }
    }
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, election_id):
        election = get_object_or_404(Election, pk=election_id)
        logger.info(f"Election results requested. | election_id={election.id}")

        try:
            service = get_blockchain_service()
        except (BlockchainConnectionError, ContractNotLoadedError) as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Get election data from blockchain
        bc_election = service.get_election(str(election.id))

        if not bc_election:
            logger.error(
                f"Election not found in the blockchain | election_id={election.id}"
            )
            return Response(
                {
                    "status": "error",
                    "message": "Election not found on blockchain. Sync it first.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get all candidates that have blockchain IDs
        try:
            start = time.time()
            candidates = election.candidates.exclude(blockchain_id__isnull=True)
            candidate_ids = [c.blockchain_id for c in candidates]
            elapsed = time.time() - start
            logger.info(
                f"fetching candidates with candidate ids took: {elapsed:.2f}s | No of candidates= {len(candidate_ids)}"
            )
        except Exception as e:
            logger.error(f"Error fetching candidates.")
            return Response(
                {"status": "error", "message": "Failed to fetch candidates"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Get results from blockchain
        try:
            start = time.time()
            results = service.get_election_results(str(election.id), candidate_ids)
            elapsed = time.time() - start
            logger.info("Election results fetched sucessfully")
            logger.info(f"Fetching results from the blockchain took : {elapsed:.2f}s")
        except BlockchainConnectionError as e:
            logger.exception(
                f"Cannot fetch election results. Blockchain connection error."
            )
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during fetching election results: {e}"
            )
            raise

        # Calculate total votes and percentages
        total_votes = sum(r["vote_count"] for r in results)

        for r in results:
            r["percentage"] = round(
                (r["vote_count"] / total_votes * 100) if total_votes > 0 else 0, 2
            )

        return Response(
            {
                "status": "success",
                "message": "Results retrieved from blockchain",
                "data": {
                    "election": {
                        "id": bc_election["id"],
                        "title": bc_election["title"],
                        "is_active": bc_election["is_active"],
                        "total_candidates": bc_election["candidate_count"],
                    },
                    "summary": {"total_votes": total_votes},
                    "results": results,
                    "source": "blockchain",
                },
            }
        )


class VerifyVoteView(APIView):
    """
    GET /api/v1/blockchain/votes/verify/?election_id=...&address=0x...

    Verify that a vote was recorded on the blockchain.

    Query parameters:
        - election_id: UUID of the election
        - address: Ethereum address of the voter

    Response:
    {
        "status": "success",
        "data": {
            "has_voted": true,
            "vote_hash": "0x...",
            "verified": true
        }
    }
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        election_id = request.query_params.get("election_id")
        voter_address = request.query_params.get("address")
        logger.info("Blockchain vote record requested.")

        if not election_id or not voter_address:
            return Response(
                {
                    "status": "error",
                    "message": "Both election_id and address are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            service = get_blockchain_service()
        except (BlockchainConnectionError, ContractNotLoadedError) as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Check if address has voted
        has_voted = service.check_if_voted(election_id, voter_address)

        if not has_voted:
            return Response(
                {
                    "status": "success",
                    "message": "No vote found for this address",
                    "data": {
                        "election_id": election_id,
                        "voter_address": voter_address,
                        "has_voted": False,
                        "verified": False,
                    },
                }
            )

        # Get vote hash for verification
        vote_hash = service.get_vote_hash(election_id, voter_address)

        return Response(
            {
                "status": "success",
                "message": "Vote verified on blockchain",
                "data": {
                    "election_id": election_id,
                    "voter_address": voter_address,
                    "has_voted": True,
                    "vote_hash": vote_hash,
                    "verified": True,
                },
            }
        )
