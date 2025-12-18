from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, permissions
from .serializers import UserRegistrationSerializer

# Create your views here.
def accounts(request):
    return HttpResponse("welcome to account home page")

class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for creating new user instance.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes =[permissions.AllowAny]