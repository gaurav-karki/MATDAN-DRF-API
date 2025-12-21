from uuid import uuid4
from django.db import models
from django.core.validators import MinLengthValidator

class Election(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=255, validators=[MinLengthValidator(10)])
    contract_address = models.CharField(max_length=42, unique=True, null=True, blank=True)
    abi_interface = models.JSONField(help_text="smart contract ABI for web 3 Interaction", null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title




