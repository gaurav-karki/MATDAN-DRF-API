from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Election
from .serializers import ElectionCreationSerializer


class ElectionCreationSerializerTest(TestCase):
    # method that test the serializer with valid election data
    def test_valid_election_data(self):
        data = {
            "title": "Student Council Election",
            "start_time": timezone.now(),
            "end_time": timezone.now() + timedelta(days=1),
            "is_active": True,
        }

        serializer = ElectionCreationSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    # method to test .save() work or not and confirm the DB interaction
    def test_serializer_creates_election(self):
        data = {
            "title": "Class Representative Election",
            "start_time": timezone.now(),
            "end_time": timezone.now() + timedelta(days=2),
            "is_active": False,
        }

        serializer = ElectionCreationSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        election = serializer.save()

        self.assertEqual(Election.objects.count(), 1)
        self.assertEqual(election.title, data["title"])

    # method  to test if title is not provided or too less
    def test_invalid_title_too_short(self):
        data = {
            "title": "Hi",
            "start_time": timezone.now(),
            "end_time": timezone.now() + timedelta(days=1),
            "is_active": False,
        }

        serializer = ElectionCreationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    # method to test the dattime fields
    def test_end_time_before_start_time(self):
        data = {
            "title": "Invalid Election",
            "start_time": timezone.now(),
            "end_time": timezone.now() - timedelta(hours=1),
            "is_active": False,
        }

        serializer = ElectionCreationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    # method to test the business logic not fields
    def test_only_one_active_election_allowed(self):
        Election.objects.create(
            title="Existing Active Election",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1),
            is_active=True,
        )

        data = {
            "title": "Another Active Election",
            "start_time": timezone.now(),
            "end_time": timezone.now() + timedelta(days=2),
            "is_active": True,
        }

        serializer = ElectionCreationSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)
