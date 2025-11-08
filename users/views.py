from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, CustomUserSerializer
from .models import CustomUser

class RegisterUserView(generics.CreateAPIView):
    """
    Handles registration of new users (Customer or Vendor)
    """
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Return minimal info; JWT token will be obtained on frontend via apiLogin
            data = CustomUserSerializer(user).data
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(generics.RetrieveAPIView):
    """
    Returns the currently authenticated user's info
    """
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

        
