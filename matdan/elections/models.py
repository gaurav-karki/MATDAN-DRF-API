from uuid import uuid4
from django.db import models
from django.core.validators import MinLengthValidator

class Election(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=255, validators=[MinLengthValidator(10)])
    contract_address = models.CharField(max_length=42, unique=True, null=True, blank=True)
    abi_interface = models.JSONField(help_text="smart contract ABI for web 3 Interaction", null=True, blank=True)
    blockchain_synced = models.BooleanField(
        default=False,
        help_text="Whether election is synced to blockchain"
    )
    blockchain_tx = models.CharField(
        max_length=66,
        null=True,
        blank=True,
        help_text="Transaction hash when election was created on blockchain"
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
class Candidate(models.Model):
    """
    Candidate model - represents a candidate in an election.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='candidates')
    name = models.CharField(max_length=255)
    party = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    photo_url = models.ImageField(upload_to='candidate_pictures/',blank=True, null=True)
    # Blockchain fields - CRITICAL for integration!
    blockchain_id = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Candidate ID on blockchain (integer, assigned during sync)"
    )
    blockchain_tx = models.CharField(
        max_length=66,
        null=True,
        blank=True,
        help_text="Transaction hash when candidate was added to blockchain"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('election', 'blockchain_id')  # Unique blockchain_id per election

    def __str__(self):
        return f"{self.name} - {self.party}"





