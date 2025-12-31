import logging

from django.shortcuts import get_object_or_404
from elections.models import Election
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Vote
from .serializers import VoteCreateSerializer, VoteListSerializer
from .services import (
    CandidateNotSyncedError,
    DuplicateVoteError,
    InActiveElectionError,
    VotingServiceError,
    get_voting_service,
)

# __name__ = 'voting.views' automatically
logger = logging.getLogger(__name__)


class VoteCreateView(generics.ListCreateAPIView):
    """
    API endpoint for voting operations.

    POST: allows user to cast vote in a specific election
    GET: view all votes for that election .
    """

    # Ensure that only authenticated users can access that endpoint.
    permission_classes = [permissions.IsAuthenticated]

    # serializer to use for validating and deserializing input, and for serializing output.
    def get_serializer_class(self):
        """
        use diffrent serializer for list and create.
        """
        if self.request.method == "POST":
            return VoteCreateSerializer
        return VoteListSerializer

    def get_serializer_context(self):
        """
        Pass the election object to the serializer context.
        """
        context = super().get_serializer_context()
        election_id = self.kwargs.get("election_id")
        context["election"] = get_object_or_404(Election, id=election_id)
        return context

    def get_queryset(self):
        """
        Return votes for the specific election.
        """
        election_id = self.kwargs.get("election_id")
        return Vote.objects.filter(election_id=election_id).select_related(
            "candidate", "voter", "election"
        )

    def list(self, request, *args, **kwargs):
        """
        Custom list response with election metadata.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(queryset, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        election_id = self.kwargs.get("election_id")
        election = get_object_or_404(Election, id=election_id)

        return Response(
            {
                "status": "success",
                "data": {
                    "election": {
                        "id": str(election.id),
                        "title": election.title,
                        "total_votes": queryset.count(),
                    },
                    "votes": serializer.data,
                },
            }
        )

    def create(self, request, *args, **kwargs):
        """
        Custom create response with vote receipt.
        cast a vote using service layer
        """
        # Validate with serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        election_id = self.kwargs.get("election_id")
        election = get_object_or_404(Election, id=election_id)
        candidate = serializer.validated_data["candidate"]

        # Use service layer for business logic
        voting_service = get_voting_service()

        try:
            success, result = voting_service.cast_vote(
                user=request.user, election=election, candidate=candidate
            )

            if success:
                return Response(
                    {
                        "status": "success",
                        "message": "Vote cast successfully and recorded on blockchain.",
                        "data": {
                            "vote_id": result["vote_id"],
                            "election": election.title,
                            "candidate": candidate.name,
                            "blockchain": result.get("blockchain", {}),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {
                        "status": "error",
                        "message": "Failed to cast vote",
                        "error": result.get("error"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except DuplicateVoteError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except InActiveElectionError as e:
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_403_FORBIDDEN
            )

        except CandidateNotSyncedError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except VotingServiceError as e:
            logger.error(f"Voting service error: {e}")
            return Response(
                {
                    "status": "error",
                    "message": "An error occurred while processing your vote",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MyVoteView(APIView):
    """
    API endpoint for users to view their own with verification hash
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, election_id):
        voting_service = get_voting_service()

        vote_data = voting_service.verify_vote(
            user=request.user, election_id=election_id
        )

        if vote_data:
            election = get_object_or_404(Election, id=election_id)

            return Response(
                {
                    "status": "success",
                    "data": {
                        "election": {"id": str(election.id), "title": election.title},
                        "vote": vote_data,
                    },
                }
            )
        else:
            return Response(
                {"status": "error", "message": "You have not voted in this election"},
                status=status.HTTP_404_NOT_FOUND,
            )


class ElectionResultsView(APIView):
    """
    API endpoint to view the result of a specific election with intelligent caching.
    Returns a list of candidates and their total votes counts for the given election.
    """

    permission_classes = [
        permissions.AllowAny
    ]  # Allows users (authenticated or not) to view the election result

    def get(self, request, election_id):
        """
        Handle GET requests to retrive and return aggregated elections results.
        """
        voting_service = get_voting_service()

        try:
            # service layer handles caching automatically
            results = voting_service.get_election_results(
                election_id=election_id, use_cache=True
            )
            return Response(
                {
                    "status": "success",
                    "message": "Results retrived successfully",
                    "data": results,
                }
            )
        except Election.DoesNotExist:
            return Response(
                {"status": "error", "message": "Election not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
