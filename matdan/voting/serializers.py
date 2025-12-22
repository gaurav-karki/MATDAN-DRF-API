from rest_framework import serializers
from .models import Vote

class VoteSerializer(serializers.ModelSerializer):
    """
    Serializer for the Vote model.

    Handles the creation of a new vote. It validates the incoming data to ensure
    that the vote is being cast in an active election, for a valid candidate,
    and that the user has not already voted.
    """

    class Meta:
        model = Vote
        #list of the fields from the Vote (i.e voting/models.py) that will be included in the serializer
        fields = ('id', 'election', 'candidate')

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
        if Vote.objects.filter(voter_id=user, election=election).exists():
            raise serializers.ValidationError("You have already voted")
        # If all validations pass, return validated data
        return data