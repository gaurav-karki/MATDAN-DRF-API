#serializer module provides functionalities for serializing & deserializing complex data into JSON
from rest_framework import serializers
from .models import User
import logging

logger = logging.getLogger('accounts')

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    serializer for creating user.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type':'password'}) # 'style={'input_type': 'password'}' helps DRF's browsable API render this as a password input field.

    # Meta class provides the metadata of the model and field to be included in the serializer
    class Meta:
        model = User
        # Tuple of the field from the user model(i.e. accounts/model.py) that will be included in the serialized data
        fields = ('username', 'password', 'email', 'wallet_address', 'national_id_hash')

    #method to create a new user instance when valid data is submitted to the serializer
    def create(self, validated_data):
        """
        This method is called to create a new user instance when valid data is submitted.
        """
        user = User.objects.create_user(
            username = validated_data['username'],
            email = validated_data.get('email'),
            password = validated_data['password'],
            wallet_address = validated_data.get('wallet_address'),
            national_id_hash = validated_data.get('national_id_hash')
        )
        # return the newly created user instance.
        logger.info(f"New user registered: {user.username}")
        return user
    
        