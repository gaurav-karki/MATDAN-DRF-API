from itertools import count
from venv import create
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from rest_framework import generics, permissions, status
from yaml import serialize
from elections.models import Election
from .serializers import VoteListSerializer, VoteCreateSerializer, MyVoteSerializer
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
    
    #Ensure that only authenticated users can access that endpoint.
    permission_classes= [permissions.IsAuthenticated]

    # serializer to use for validating and deserializing input, and for serializing output.
    def get_serializer_class(self):
        """
        use diffrent serializer for list and create.
        """
        if self.request.method == 'POST':
            return VoteCreateSerializer
        return VoteListSerializer

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
        Return votes for the specific election.
        """
        election_id = self.kwargs.get('election_id')
        return Vote.objects.filter(election_id=election_id)

    def list(self, request, *args, **kwargs):
        """
        Custom list response with election metadata.
        """
        queryset = self.filter_queryset(self.get_queryset())
        election = self.get_serializer_context()['election']

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            paginated_data = serializer.data
        return Response({
            'status':'success',
            'message':'Votes retrived sucessfully',
            'data':{
                'election':{
                    'id':str(election.id),
                    'title':election.title,
                    'is_active':election.is_active,
                    'total_votes':queryset.count()
                },
                'votes':paginated_data
            }
        })

    def create(self, request, *args, **kwargs):
        """
        Custom create response with vote receipt.
        """
        serializer = self.get_serializer(data=request.data)
        # If the data is invalid, this will raise the Validation Error.
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            'status': 'success',
            'message': 'Your vote has been cast sucessfully.',
            'data':{
                'receipt':serializer.data
            }
        },status=status.HTTP_201_CREATED, headers=headers)
    
    # def perform_create(self, serializer):
    #     vote = serializer.save(voter=self.request.user)
    #     create(vote)
    
class MyVoteView(APIView):
    """
    API endpoint for users to view their own with verification hash
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, election_id):
        election = get_object_or_404(Election,pk=election_id)
        vote = Vote.objects.filter(voter=request.user, election=election).first()

        if not vote:
            return Response({
                'status': 'error',
                'message': 'You have not voted in this election yet.'
            },status=status.HTTP_404_NOT_FOUND)
        serializer = MyVoteSerializer(vote)
        return Response({
            'status': 'success',
            'message': 'Your vote retrived sucessfully.',
            'data': serializer.data
        })

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

        #Get total candidates associated with this election
        total_candidates = election.candidates.count()

        # query to group votes by candidate and count them
        vote_counts = Vote.objects.filter(election=election).values(
            'candidate__id', 
            'candidate__name',
            'candidate__party'
            ).annotate(
                vote_count=Count('id')
                ).order_by('-vote_count')
        
        total_votes = sum(item['vote_count'] for item in vote_counts)

        results = []
        for item in vote_counts:
            percentage = (item['vote_count'] / total_votes * 100) if total_votes > 0 else 0
            results.append({
                'candidate':{
                    'id': str(item['candidate__id']),
                    'name': item['candidate__name'],
                    'party': item['candidate__party']
                },
                'vote_count': item['vote_count'],
                'percentage': round(percentage, 2)
            })
        return Response({
            'status': 'success',
            'message': 'Election results retrived sucessfully',
            'data':{
                'election':{
                    'id': str(election.id),
                    'title': election.title,
                    'is_active': election.is_active
                },
                'summary':{
                    'total_votes': total_votes,
                    'total_candidates': total_candidates
                },
                'results': results
            }
        })

