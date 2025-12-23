from rest_framework import serializers

from elections.models import Candidate
from .models import Vote

class CandidateDetailSerializer(serializers.ModelSerializer):
    """
    Nested Serializer for candidated deatils
    """
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'party']
class VoteListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing votes (GET request)
    """
    candidate = CandidateDetailSerializer(read_only=True)
    class Meta:
        model = Vote
        fields = ['id', 'candidate','voted_at']


class VoteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for the Vote model.

    Handles the creation of a new vote. It validates the incoming data to ensure
    that the vote is being cast in an active election, for a valid candidate,
    and that the user has not already voted.
    """
    candidate_id = serializers.PrimaryKeyRelatedField(queryset=Candidate.objects.none(), source='candidate', write_only=True)
    candidate = CandidateDetailSerializer(read_only=True)

    class Meta:
        model = Vote
        #list of the fields from the Vote (i.e voting/models.py) that will be included in the serializer
        fields = ['id', 'candidate_id','candidate', 'vote_hash','voted_at']
        read_only_fields = ['id', 'candidate','vote_hash','voted_at']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # get election from context (passed from the view)
        election = self.context.get('election')

        if election:
            # Filter candidates to only show those in this election
            self.fields['candidate'].queryset = Candidate.objects.filter(election=election)

    def validate(self, data):
        """
        Perform custom validation on the data for a new vote.
        """
        user = self.context['request'].user
        election = self.context['election']
        candidate = data['candidate']

        #check if the election is currently active
        if not election.is_active:
            raise serializers.ValidationError("Election is not active.")
        
        #check if the selected candidate belongs to this specific election.
        if candidate.election != election:
            raise serializers.ValidationError("Candidate doesnot belong to this election")
        
        #check if the user has already cast a vote in this election
        if Vote.objects.filter(voter=user, election=election).exists():
            raise serializers.ValidationError("You have already voted")
        
        # If all validations pass, return validated data
        return data
    
    def create(self, validated_data):
        """
        Create a new vote with the election from context and current user as voter.
        """
        import hashlib
        import time

        #Get election from context and add it to validated_data
        election = self.context.get('election')
        user = self.context['request'].user

        #generate vote hash
        vote_data = f"{user.id}-{election.id}-{validated_data['candidate'].id}-{time.time()}"
        vote_hash = hashlib.sha256(vote_data.encode()).hexdigest()

        validated_data['election'] = election
        validated_data['voter'] = user
        validated_data['vote_hash'] = vote_hash

        return super().create(validated_data)
    

class MyVoteSerializer(serializers.ModelSerializer):
    """
    Serializer for user's own vote with verification hash.
    """
    candidate = CandidateDetailSerializer(read_only=True)
    election_title = serializers.CharField(source='election.title', read_only=True)

    class Meta:
        model = Vote
        fields = ['id', 'election', 'election_title', 'candidate', 'vote_hash', 'voted_at']