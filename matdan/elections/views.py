import logging

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from requests import Response
from rest_framework import generics, status
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet

from .models import Candidate, Election
from .permissions import IsAdminOrReadOnly
from .serializers import CandidateSerializer, ElectionCreationSerializer

logger = logging.getLogger(__name__)


class ElectionCreationView(ModelViewSet):
    """
    API endpoint to create new elections
    """

    queryset = Election.objects.all()
    serializer_class = (
        ElectionCreationSerializer  # serializer that handles the election creation
    )
    permission_classes = [IsAdminOrReadOnly]

    # add OrderingFilter to filter_backends
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["is_active"]  # This enables filtering by the 'is_active' field
    # elections will be ordered based on the start_time
    ordering_fields = ["start_time", "created_at"]


class ElectionUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Election.objects.all()
    serializer_class = ElectionCreationSerializer


class CandidateListByElectionView(generics.ListCreateAPIView):
    serializer_class = (
        CandidateSerializer  # serializer that handles the candidate creation
    )
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        election_id = self.kwargs["election_id"]
        logger.info(f"Fetching candidates for elections: {election_id}")
        return Candidate.objects.filter(election_id=election_id)

    def get_serializer_context(self):
        """
        Pass the actual election OBJECT to the serializer context.
        This is crucial for validation to work correctly.
        """
        context = super().get_serializer_context()
        election_id = self.kwargs.get("election_id")

        # Get the election object and passs it in context
        election = get_object_or_404(Election, pk=election_id)
        context["election"] = election

        logger.debug(f"Serializer context includes elections: {election.title}")
        return context

    def perform_create(self, serializer):
        """
        Associate the candidate with the election from the URL.
        """
        election_id = self.kwargs["election_id"]
        election = get_object_or_404(Election, pk=election_id)

        logger.info(f"Creating candidate for election: {election.title}")
        serializer.save(election=election)
