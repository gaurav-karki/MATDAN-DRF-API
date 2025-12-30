import logging

from django.utils import timezone
from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from .permissions import IsAnonymousUser
from .serializers import UserRegistrationSerializer

logger = logging.getLogger("accounts")


class CustomAuthToken(ObtainAuthToken):
    """
    Custom authentication token view that extends DRF's default `ObtainAuthToken` class.
    This view provides a token upon sucessful login and also update `last_login` timestamp.
    """

    def post(self, request, *args, **kwargs):
        logger.info("Authentication attempt for user: %s", request.data.get("username"))

        # Instantiate the serializer with the request data.
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )

        try:
            # validate the credentails. if invalid , it will raise Validation Error.
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data["user"]

            # Retrive an existing token or create a new one for the user.
            token, created = Token.objects.get_or_create(user=user)

            # manually update the last login field
            user.last_login = timezone.now()
            user.save(
                update_fields=["last_login"]
            )  # save the last login time to the database

            logger.info("User authenticated sucessfully: %s", user.username)
            # Logger to log 'True' if a new token was created or 'False' if an existing token was returned.
            if created:
                logger.info("New token created for user: %s", user.username)
            else:
                logger.info("Existing token returned for user: %s", user.username)

            # Return a customresponse including the token and basic user info.
            return Response(
                {"token": token.key, "user_id": user.pk, "email": user.email}
            )
        except Exception as e:
            logger.error(
                "Authentication failed for user: %s. Error: %s",
                request.data.get("username"),
                str(e),
            )


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for creating new user instance.
    """

    # Use the UserRegistrationSerializer to validate and create a user instance.
    serializer_class = UserRegistrationSerializer
    # Allow any user (authenticated or not) to acces this endpoint for registration
    permission_classes = [IsAnonymousUser]

    def create(self, request, *args, **kwargs):
        logger.info("User registration attempt: %s", request.data.get("username"))
        try:
            response = super().create(request, *args, **kwargs)
            logger.info(
                "User registered sucessfully -> %s", request.data.get("username")
            )
            return response
        except Exception as e:
            logger.error(
                "User registration failed for %s. Error: %s",
                request.data.get("username"),
                str(e),
            )
            raise
