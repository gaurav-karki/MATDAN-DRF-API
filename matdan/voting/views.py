from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from elections.models import Election
from .serializers import VoteSerializer
from rest_framework.response import Response
from django.db.models import Count
from rest_framework.views import APIView

from .models import Vote

def voting_home(request):
    return HttpResponse("Welcome to voting page")

class VoteCreateView(generics.ListCreateAPIView):
    """
    API endpoint that allows user to cast vote in a specific election (POST)
    & view all votes for that election (GET).
    """
    # serializer to use for validating and deserializing input, and for serializing output.
    serializer_class = VoteSerializer
    #Ensure that only authenticated users can access that endpoint.
    permission_classes= [permissions.IsAuthenticated]

    def get_serializer_context(self):
        """
        Pass the election object to the serializer context.
        """
        context = super().get_serializer_context()
        election_id = self.kwargs.get('election_id')
        context['election'] = get_object_or_404(Election, id=election_id)
        return context

    def get_queryset(self):
        """
        This method is called to get the list of objects for 
        """
        election_id = self.kwargs.get('election_id')
        return Vote.objects.filter(election_id=election_id)

    def perform_create(self, serializer):
        """
        Hook called by CreateModelMixin before saving a new object instance.
        
        This implementation injects the `voter` (the authenticated user) and the
        `election` (retrieved from the URL) into the instance before it is saved.
        """
        election_id = self.kwargs.get('election_id')
        election = get_object_or_404(Election, id=election_id)
        # serializer `validate` method will handle the business logic
        # such as checking if the user has already voted.
        serializer.save(voter=self.request.user, election=election)

    def create(self, request, *args, **kwargs):
        """
        overrrides the default create method to provide a custom sucess message
        """
        serializer = self.get_serializer(data=request.data)
        # If the data is invalid, this will raise the Validation Error.
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'detail':'Vote cast sucessfully,'},status=status.HTTP_201_CREATED, headers=headers)
    

class ElectionResultsView(APIView):
    """
    API endpoint to view the result of a specific election.
    Returns a list of candidates and their total votes counts for the given election.
    """
    permission_classes = [permissions.AllowAny] # Allows users (authenticated or not) to view the election result

    def get(self, request, election_id, format=None):
        """
        Handle GET requests to retrive and return aggregated elections results.
        """
        #Ensure the election exists before trying to get result
        election = get_object_or_404(Election, pk=election_id)

        # query to group votes by candidate and count them
        vote_counts = Vote.objects.filter(election=election).values(
            'candidate__id', 'candidate__name'
            ).annotate(
                vote_counts=Count('id')
                ).order_by('-vote_counts')
        return Response(vote_counts, status=status.HTTP_200_OK)

