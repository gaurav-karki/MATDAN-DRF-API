from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    wallet_address = models.CharField(max_length=255, unique=True, null=True, blank=True)
    national_id_hash = models.CharField(max_length=255,unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username



