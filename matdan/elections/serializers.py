import logging
from urllib import request

from rest_framework import serializers

from .models import Candidate, Election

logger = logging.getLogger("elections")


class ElectionCreationSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Election instances.
    It handles the conversion of Election model instances to JSON and vice versa."""

    # The Meta class provides the metadata of the model and field to be included in the serializer
    class Meta:
        # specify the model the serializer is based on
        model = Election
        # Lists of the fields from the model to be included in the serialized output.
        fields = ("id", "title", "start_time", "end_time", "is_active")

    def update(self, instance, validated_data):
        logger.info(f"Election updated by admin:{instance.title}")
        return super().update(instance, validated_data)

    def validate(self, data):
        """
        Add custom validation for business rules that are not covered  by the model field validation.
        This method is called when `serializer.is_valid()` is executed
        """
        # self.instance is the object being updated, or None for a new object creation.
        instance = self.instance
        # get start_time or end_time from incoming data, or from the existing instance if not provided.
        start_time = data.get("start_time", instance.start_time if instance else None)
        end_time = data.get("end_time", instance.end_time if instance else None)
        title = data.get("title", instance.title if instance else None)

        logger.debug(
            f"Validating election: Start_time:{start_time}, End_time:{end_time}, instance = {instance}"
        )

        # Validation Rule 1: End time must be after start time.
        if start_time and end_time and start_time >= end_time:
            logger.warning(f"End time must be after start time.")
            raise serializers.ValidationError(
                "The election's end time must be after its start time."
            )

        # Validation Rule 2: If this election is being set to active, ensure no other election is already active.
        # If the current request is trying to set "is_active" to True
        if data.get("is_active") is True:
            # Find all other elections that are currently is_active=True
            logger.info("Searching for active elections")
            active_elections = Election.objects.filter(is_active=True)

            # If we are updating anexisting election, exclude it from the check
            # This allows us to update other fields of an already active election without errors.
            if instance:
                active_elections = active_elections.exclude(pk=instance.pk)
            # If any other active election exists, raise an error
            if active_elections.exists():
                logger.warning("Another election is already active")
                raise serializers.ValidationError(
                    "Another election is already active. Only one election can be active at a time."
                )
        # if all validation pass, return validated data.
        logger.info(
            f"Sucessfully created election: {title}, passes serializer validation criteria."
        )
        return data


class CandidateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Candidate instances.
    it handles the serialization and deserialization of the candidates data.
    """

    class Meta:
        model = Candidate
        # fields to be inclued in the serialized output
        fields = ["id", "name", "party", "election", "photo_url"]
        # `election ` is set to read-only because it should be determined by the URL
        read_only_fields = ["election"]

    def validate(self, data):
        """
        Custom validation for candidate data
        """

        instance = self.instance
        # Get the name from the incoming data or from the existing instance if not provided.
        name = data.get("name", instance.name if instance else None)
        election = data.get("election", instance.election if instance else None)

        logger.debug(
            f"Validating candidate: name = {name}, election = {election}, instance = {instance}"
        )

        # Validation Rule 1: Ensure the name is not too short
        if len(name) <= 1:
            logger.warning("Candidate name too short.")
            raise serializers.ValidationError("Name cannot be of 1 letter")

        # Ensure the candidate name is unique
        qs = Candidate.objects.filter(name=name)
        if election:
            qs = qs.filter(election=election)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            logger.warning(
                f"Candidate with name: '{name}' already exists in the election: '{election}'"
            )
            raise serializers.ValidationError("Candidate with the name already exists")
        logger.info(f"Candidate '{name}' passed validation for election '{election}'.")
        # return the validated data if all checks pass.
        return data
