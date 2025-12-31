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

logger = logging.getLogger("elections")


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

    def create(self, request, *args, **kwargs):
        logger.debug(f"Incoming data: {request.data}")
        return super().create(request, *args, **kwargs)


class ElectionUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Election.objects.all()
    serializer_class = ElectionCreationSerializer

    def update(self, request, *args, **kwargs):
        logger.debug(f"Incoming data: {request.data}")
        return super().update(request, *args, **kwargs)


class CandidateListByElectionView(generics.ListCreateAPIView):
    serializer_class = (
        CandidateSerializer  # serializer that handles the candidate creation
    )
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        election_id = self.kwargs["election_id"]
        logger.info("Elections data retrived sucessfully.")
        return Candidate.objects.filter(election_id=election_id)

    def perform_create(self, serializer):
        """
        Associate the candidate with the election from the URL.
        """
        # Print the contents of self.kwargs to verify the key and value exist
        logger.debug(f"self.kwargs content:{self.kwargs}")
        # print the specific election_id being accessed
        try:
            election = get_object_or_404(Election, pk=self.kwargs["election_id"])
            logger.info(f"election_id from the url: '{election}'")
            serializer.save(election=election)
        except KeyError as e:
            logger.error("Missing url parameter")
            return Response(
                {"error": f"Missing URL parameter: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["election_id"] = self.kwargs.get("election_id")
        return context
