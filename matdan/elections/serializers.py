from rest_framework import serializers
from .models import Election, Candidate


class ElectionCreationSerializer(serializers.ModelSerializer):
    
    #meta class provides the metadata of the model and field to be included in the serializer
    class Meta:
        model = Election
        fields = ('id', 'title', 'start_time', 'end_time', 'is_active')

    def validate(self, data):
        """
        Add custom validation for business rules.
        """
        instance = self.instance
        start_time = data.get('start_time', instance.start_time if instance else None)
        end_time = data.get('end_time', instance.end_time if instance else None)

        # End time must be after start time.
        if start_time and  end_time and start_time >= end_time:
            raise serializers.ValidationError("The election's end time must be after its start time.")

        # If this election is being set to active, ensure no other election is already active.
        # We use .exclude(pk=self.instance.pk) to allow updating an already active election.
        if data.get('is_active') is True:
            active_elections = Election.objects.filter(is_active=True)
            if instance:
                active_elections = active_elections.exclude(pk=instance.pk)
            if active_elections.exists():
                raise serializers.ValidationError("Another election is already active. Only one election can be active at a time.")
        
        return data


class CandidateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'party', 'election', 'photo_url']
        read_only_fields = ['election']



    