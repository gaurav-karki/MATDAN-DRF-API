from multiprocessing import context
from urllib import request
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework import generics, permissions
from .serializers import UserRegistrationSerializer
from django.utils import timezone
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

# Create your views here.
def accounts(request):
    return HttpResponse("welcome to account home page")


class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request':request})

        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        #manually update the last login field
        user.last_login = timezone.now()
        user.save(update_fields=['last_login']) # save the last login time to the database

        return Response({
            'token':token.key,
            'user_id':user.pk,
            'email':user.email
        })


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for creating new user instance.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes =[permissions.AllowAny]

