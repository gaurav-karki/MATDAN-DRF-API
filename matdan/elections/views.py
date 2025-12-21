from django.http import HttpResponse
from .models import Election
from rest_framework import generics, permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .serializers import ElectionCreationSerializer
from .permissions import IsAdminOrReadOnly

def elections_home(request):
    return HttpResponse("Welcome to election home page.")


class ElectionCreationView(ModelViewSet):
    """
    API endpoint to create new elections
    """
    queryset = Election.objects.all()
    serializer_class = ElectionCreationSerializer
    permission_classes = [IsAdminOrReadOnly]