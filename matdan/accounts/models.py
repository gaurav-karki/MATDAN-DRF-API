import logging

from django.contrib.auth.models import AbstractUser
from django.db import models

logger = logging.getLogger("accounts")


class User(AbstractUser):
    wallet_address = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    national_id_hash = models.CharField(
        max_length=255, unique=True, null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if self.pk and User.objects.filter(pk=self.pk).exists():
            logger.info(f"Login updated for user -> {self.username}")
        else:
            logger.info(f"Saving user: {self.username}")
        super().save(*args, **kwargs)
