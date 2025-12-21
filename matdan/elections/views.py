from django.http import HttpResponse
from rest_framework import generics
from .models import Election, Candidate
from rest_framework.viewsets import ModelViewSet
from .serializers import ElectionCreationSerializer, CandidateSerializer
from .permissions import IsAdminOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser

def elections_home(request):
    return HttpResponse("Welcome to election home page.")


class ElectionCreationView(ModelViewSet):
    """
    API endpoint to create new elections
    """
    queryset = Election.objects.all()
    serializer_class = ElectionCreationSerializer
    permission_classes = [IsAdminOrReadOnly]

    #add OrderingFilter to filter_backends
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_active'] # This enables filtering by the 'is_active' field

    ordering_fields = ['start_time', 'created_at']


class CandidateListByElectionView(generics.ListCreateAPIView):
    serializer_class = CandidateSerializer
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        election_id = self.kwargs['election_id']
        return Candidate.objects.filter(election_id=election_id)
    
    def perform_create(self, serializer):
        """
        Associate the candidate with the election from the URL.
        """
        election = get_object_or_404(Election, pk=self.kwargs['election_id'])
        serializer.save(election=election)