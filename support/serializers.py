from rest_framework import serializers
from .models import SupportMessage

class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ['id', 'name', 'email', 'message', 'created_at', 'is_resolved']
