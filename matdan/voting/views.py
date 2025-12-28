from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Count

from requests import get
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from elections.models import Election, Candidate
from .models import Vote
from .serializers import VoteListSerializer, VoteCreateSerializer, MyVoteSerializer

from blockchain.services import get_blockchain_service

import logging
logger=logging.getLogger(__name__)



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
        serializer=self.get_serializer(queryset, many=True)

        election_id = self.kwargs.get('election_id')
        election = get_object_or_404(Election, id=election_id)

        return Response({
            'status':'success',
            'data':{
                'election':{
                    'id':str(election.id),
                    'title':election.title,
                    'total_votes':queryset.count()
                },
                'total_votes':queryset.count(),
                'votes':serializer.data
            }
        })

    def create(self, request, *args, **kwargs):
        """
        Custom create response with vote receipt.
        cast a vote -saves to DB and blockchain
        """
        serializer = self.get_serializer(data=request.data)
        # If the data is invalid, this will raise the Validation Error.
        serializer.is_valid(raise_exception=True)

        # Get election and candidate
        election_id = self.kwargs.get('election_id')
        election = get_object_or_404(Election, id=election_id)
        candidate = serializer.validated_data['candidate']

        # Check if user already voted (in Django DB)
        if Vote.objects.filter(voter=request.user, election=election).exists():
            return Response({
                'status': 'error',
                'message': 'You have already voted in this election'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if election is active
        if not election.is_active:
            return Response({
                'status': 'error',
                'message': 'This election is not active'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if candidate has blockchain_id
        if not candidate.blockchain_id:
            return Response({
                'status': 'error',
                'message': 'Candidate not synced to blockchain. Contact admin.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # ============ STEP 2: RECORD ON BLOCKCHAIN ============
        blockchain_service = get_blockchain_service()
        if blockchain_service.is_connected() and blockchain_service.contract:
            logger.info(f"Recording vote on blockchain...")
            
            success, result = blockchain_service.cast_vote(
                election_id=str(election.id),
                candidate_blockchain_id=candidate.blockchain_id
            )
            
            if success:
                # ============ STEP 1: SAVE TO POSTGRESQL ============
                vote = Vote.objects.create(
                    voter=request.user,
                    election=election,
                    candidate=candidate,
                    blockchain_tx=result.get('tx_hash'),
                    blockchain_hash=result.get('vote_hash')
                )
                logger.info(f"Vote recoreded to blockchain and saved to DB: {vote.id}")
                
                return Response({
                    'status': 'success',
                    'message': 'Vote cast successfully and recorded on blockchain!',
                    'data': {
                        'vote_id': str(vote.id),
                        'election': election.title,
                        'candidate': candidate.name,
                        'blockchain': {
                            'tx_hash': result.get('tx_hash'),
                            'vote_hash': result.get('vote_hash'),
                            'block_number': result.get('block_number')
                        }
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                logger.error(f"Blockchain recording failed: {result.get('error')}")
                
                return Response({
                    'status': 'error',
                    'message': 'Blockchain recording failed. vote not saved',
                    'blockchain_error': result.get('error')
                    
                }, status=status.HTTP_201_CREATED)
        else:
            # Blockchain not available
            logger.warning("Blockchain not connected, vote saved to DB only")
            
            return Response({
                'status': 'success',
                'message': 'Vote cast successfully (blockchain offline)',
                'data': {
                    'vote_id': str(vote.id),
                    'election': election.title,
                    'candidate': candidate.name,
                    'blockchain': None
                }
            }, status=status.HTTP_201_CREATED)
    
class MyVoteView(APIView):
    """
    API endpoint for users to view their own with verification hash
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, election_id):
        election = get_object_or_404(Election,id=election_id)

        try:
            vote = Vote.objects.get(voter=request.user, election=election)

            return Response({
                'status': 'success',
                'data': {
                    'election': {
                        'id': str(election.id),
                        'title': election.title
                    },
                    'vote': {
                        'id': str(vote.id),
                        'candidate': {
                            'id': str(vote.candidate.id),
                            'name': vote.candidate.name,
                            'party': vote.candidate.party
                        },
                        'voted_at': vote.created_at.isoformat(),
                        'blockchain': {
                            'tx_hash': vote.blockchain_tx,
                            'vote_hash': vote.blockchain_hash
                        }
                    }
                }
            })
        except Vote.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'You have not voted in this election'
            }, status=status.HTTP_404_NOT_FOUND)

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
            'candidate__party',
            'candidate__blockchain_id'
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
                    'party': item['candidate__party'],
                    'blockchain_id': item['candidate__blockchain_id']
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
                'results': results,
                'source':'postgresql'
            }
        })

