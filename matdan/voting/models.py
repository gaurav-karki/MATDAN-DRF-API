from uuid import uuid4
from django.db import models
from django.conf import settings

class Vote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='votes')
    election = models.ForeignKey('elections.Election', on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey('elections.Candidate', on_delete=models.CASCADE)
    vote_hash = models.CharField(max_length=255)
    blockchain_tx = models.CharField(max_length=255, null=True, blank=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """
        Metadata ptions for the Vote model
        """
        #This constraint ensures that a user can vote only once per election.
        unique_together = ('voter', 'election')

    def __str__(self):
        """
        Returns a string representation of the Vote instance, useful for the Django Admin."""
        return f"Vote by {self.voter} for {self.candidate}"




