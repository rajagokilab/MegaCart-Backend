# support/views.py
from rest_framework import generics, permissions
from .models import SupportMessage
from .serializers import SupportMessageSerializer

# --- Public API for users to submit a support message ---
class SupportMessageCreateAPIView(generics.CreateAPIView):
    queryset = SupportMessage.objects.all()
    serializer_class = SupportMessageSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can submit

# --- Admin API to list all messages ---
class SupportMessageListCreateAPIView(generics.ListCreateAPIView):
    """
    Admin can list all messages and optionally create new messages (optional for admin panel).
    """
    queryset = SupportMessage.objects.all().order_by('-created_at')
    serializer_class = SupportMessageSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admins
