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
from .permissions import IsAnonymousUser

# Create your views here.
def accounts(request):
    return HttpResponse("welcome to account home page")


class CustomAuthToken(ObtainAuthToken):
    """
    Custom authentication token view that extends DRF's default `ObtainAuthToken` class.
    This view provides a token upon sucessful login and also update `last_login` timestamp.
    """
    def post(self, request, *args, **kwargs):
        #Instantiate the serializer with the request data.
        serializer = self.serializer_class(data=request.data, context={'request':request})

        #validate the credentails. if invalid , it will raise Validation Error.
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Retrive an existing token or create a new one for the user.
        token, created = Token.objects.get_or_create(user=user)

        #manually update the last login field
        user.last_login = timezone.now()
        user.save(update_fields=['last_login']) # save the last login time to the database

        # Return a customresponse including the token and basic user info.
        return Response({
            'token':token.key,
            'user_id':user.pk,
            'email':user.email
        })


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for creating new user instance.
    """
    # Use the UserRegistrationSerializer to validate and create a user instance.
    serializer_class = UserRegistrationSerializer
    #Allow any user (authenticated or not) to acces this endpoint for registration
    permission_classes =[IsAnonymousUser]

