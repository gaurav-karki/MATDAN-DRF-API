import logging
import uuid
from typing import Any, Dict, Optional, Tuple
from urllib import request

from blockchain.services import get_blockchain_service
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from elections.models import Candidate, Election

from .models import Vote

logger = logging.getLogger(__name__)


class VotingServiceError(Exception):
    """Base Exception for voting service"""

    pass


class DuplicateVoteError(VotingServiceError):
    """Raised when user tries to vote twice"""

    pass


class InActiveElectionError(VotingServiceError):
    """Raised when user try to vote in in_active eletion"""

    pass


class CandidateNotSyncedError(VotingServiceError):
    """Raised when candidate is not synced to blockchain"""

    pass


class VotingService:
    """
    Centralized service for all voting operations.
    Handles validation, blockchain integration, and database transactions.
    """

    def __init__(self):
        self.blockchain_service = get_blockchain_service()

    @transaction.atomic  # Database transaction -all or noting
    def cast_vote(
        self, user, election: Election, candidate: Candidate
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cast a vote with full validation and blockchain recording.

        Args:
            user: The authenticated user casting the vote
            election: The election to vote in
            candidate: The candidate to vote for

        Returns:
            Tuple of (success, result_data)

        Raises:
            DuplicateVoteError: If user already voted
            InactiveElectionError: If election is not active
            CandidateNotSyncedError: If candidate not on blockchain
        """
        # Using request IDs for Tracing logs
        request_id = str(uuid.uuid4())[:8]  # short ID
        request.request_id = request_id

        # Validation of vote
        self._validate_vote(user, election, candidate)

        # Record 'Vote' on the blockchain first
        blockchain_result = self._record_on_blockchain(election, candidate)

        if not blockchain_result["success"]:
            logger.error(
                f"[{request_id}] Blockchain vote failed: {blockchain_result.get('error')}"
            )
            return False, {
                "error": "Blockchain recording failed",
                "details": blockchain_result.get("error"),
            }

        # Save to database (inside transaction)
        vote = Vote.objects.create(
            voter=user,
            election=election,
            candidate=candidate,
            blockchain_tx=blockchain_result["tx_hash"],
            blockchain_hash=blockchain_result["vote_hash"],
        )

        # Clear the cached results
        self._invalidate_cache(election.id)

        # Send notification
        self._send_vote_confirmation(user, vote)

        # log the vote successfully message
        logger.info(
            f"[{request_id}] Vote successfully cast.",
            extra={"Vote_id": vote.id, "Voter": user},
        )
        # return the response to the user
        return True, {"vote_id": str(vote.id), "blockchain": blockchain_result}

    def _validate_vote(self, user, election: Election, candidate: Candidate) -> None:
        """Validate all voting requirements"""
        # Check duplicate vote
        if Vote.objects.filter(voter=user, election=election).exists():
            raise DuplicateVoteError("You have already voted in this election")

        # check election is active
        if not election.is_active:
            raise InActiveElectionError("This election is not accepting votes")

        # Check election time window
        now = timezone.now()
        if now < election.start_time:
            raise InActiveElectionError("Election has not started yet")
        if now > election.end_time:
            raise InActiveElectionError("Election has ended")

        # Check blockchain sync
        if not candidate.blockchain_id:
            raise CandidateNotSyncedError("Candidate not synced to blockchain.")

    def _record_on_blockchain(
        self, election: Election, candidate: Candidate
    ) -> Dict[str, Any]:
        """Record vote on blockchain"""
        if not self.blockchain_service.is_connected():
            logger.warning("Blockchain not connected")
            return {"success": False, "error": "Blockchain unavailable"}

        success, result = self.blockchain_service.cast_vote(
            election_id=str(election.id),
            candidate_blockchain_id=candidate.blockchain_id,
        )

        return {"success": success, **result}

    def _invalidate_cache(self, election_id) -> None:
        """Clear cached election results"""
        cache_key = f"election_results:{election_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for election {election_id}")

    def _send_vote_confirmation(self, user, vote: Vote) -> None:
        """Send vote confirmation (placeholder for email/notification)"""

        # Implement with celery for async processing
        logger.info(f"Vote confirmation for user {user.id}: {vote.id}")

    def get_election_results(
        self, election_id, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get election results with intelligent caching

        Args:
            election_id: UUID of the election
            use_cache: whether to use cached results (default: True)

        Returns:
            Dictionary containing election results
        """
        cache_key = f"election_results:{election_id}"
        # Try cache first
        if use_cache:
            cached_results = cache.get(cache_key)
            if cached_results:
                logger.debug(f"Returning cached results for {election_id}")
                return cached_results

        # calculate results from database
        election = Election.objects.get(pk=election_id)

        # use efficient aggregation
        from django.db.models import Count, F

        results = (
            Vote.objects.filter(election=election)
            .values(
                "candidate__id",
                "candidate__name",
                "candidate__party",
                "candidate__blockchain_id",
            )
            .annotate(vote_count=Count("id"))
            .order_by("-vote_count")
        )

        total_votes = sum(r["vote_count"] for r in results)

        formatted_results = {
            "election": {
                "id": str(election.id),
                "title": election.title,
                "is_active": election.is_active,
            },
            "total_votes": total_votes,
            "candidates": [
                {
                    "candidate": {
                        "id": str(r["candidate__id"]),
                        "name": r["candidate__name"],
                        "party": r["candidate__party"],
                        "blockchain_id": r["candidate__blockchain_id"],
                    },
                    "vote_count": r["vote_count"],
                    "percentage": round(
                        (r["vote_count"] / total_votes * 100) if total_votes > 0 else 0,
                        2,
                    ),
                }
                for r in results
            ],
        }

        # Cache for 5 minutes (adjust based on needs)
        cache.set(cache_key, formatted_results, timeout=300)

        return formatted_results

    def verify_vote(self, user, election_id) -> Optional[Dict[str, Any]]:
        """
        Verify a user's vote on the blockchain.

        Returns:
            Vote details with blockchain verification, or None if not found
        """
        try:
            vote = Vote.objects.get(voter=user, election_id=election_id)

            # Verify on blockchain
            blockchain_verified = False
            if vote.blockchain_hash:
                # Check blockchain
                bc_vote_hash = self.blockchain_service.get_vote_hash(
                    str(election_id),
                    user.wallet_address if hasattr(user, "wallet_address") else None,
                )
                blockchain_verified = bc_vote_hash == vote.blockchain_hash

            return {
                "vote_id": str(vote.id),
                "candidate": {
                    "name": vote.candidate.name,
                    "party": vote.candidate.party,
                },
                "blockchain_tx": vote.blockchain_tx,
                "blockchain_hash": vote.blockchain_hash,
                "blockchain_verified": blockchain_verified,
                "voted_at": vote.created_at.isoformat(),
            }

        except Vote.DoesNotExist:
            return None


# Singleton instance
_voting_service: Optional[VotingService] = None


def get_voting_service() -> VotingService:
    """Get or create the voting service singleton"""
    global _voting_service
    if _voting_service is None:
        _voting_service = VotingService()
    return _voting_service
