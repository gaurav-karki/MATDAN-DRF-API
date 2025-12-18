#serializer module provides functionalities for serializing & deserializing complex data into JSON
from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type':'password'})

    # Meta class provides the metadata of the model and field to be included in the serializer
    class Meta:
        model = User
        #list of the field from the user model(i.e. accounts/model.py) that will be included in the serialized data
        fields = ('username', 'password', 'email', 'wallet_address')

    #method to create a new user instance when valid data is submitted to the serializer
    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data['username'],
            email = validated_data.get('email'),
            password = validated_data['password'],
            wallet_address = validated_data.get('wallet_address')
        )
        return user
    
        