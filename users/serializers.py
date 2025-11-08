from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import authenticate

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password', 'role', 'store_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'CUSTOMER'),
            store_name=validated_data.get('store_name', None),
            is_approved=validated_data.get('role') != 'VENDOR'  # auto-approve non-vendors
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if user.role == 'VENDOR' and not user.is_approved:
            raise serializers.ValidationError("Vendor account not approved yet")
        return {'user': user}
from rest_framework import serializers
from .models import CustomUser

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'role', 'store_name', 'is_active', 'is_staff')
        # users/serializers.py
from rest_framework import serializers
from .models import CustomUser

class StorefrontUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('store_name', 'store_description', 'store_logo', 'store_banner')
