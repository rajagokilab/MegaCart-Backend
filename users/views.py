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

        
# In your admin/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from users.models import CustomUser  # ⬅️ Import your CustomUser model
from .serializers import AdminVendorSerializer # ⬅️ Import your serializer

# Make sure to import the helper function from Step 1
# (It might already be in this file)


class ApproveVendorView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        try:
            # Get the vendor you want to approve/reject
            vendor = CustomUser.objects.get(pk=pk, role='VENDOR')
        except CustomUser.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # "APPROVE" or "REJECT" from React

        if action == 'APPROVE':
            vendor.is_approved = True
            vendor.save(update_fields=['is_approved'])
            
            # --- 🚀 TRIGGER ASYNCHRONOUS EMAIL ---
            # This is the new code you must add
            email_thread = threading.Thread(
                target=send_approval_email_async,
                args=(vendor.email, vendor.store_name)
            )
            email_thread.start() # This returns immediately
            # --- Email is now being sent in the background ---
            
            return Response(AdminVendorSerializer(vendor).data, status=status.HTTP_200_OK)
        
        elif action == 'REJECT':
            vendor.is_approved = False
            vendor.save(update_fields=['is_approved'])
            
            # (Optional: send a rejection email here)
            # send_rejection_email_async(vendor.email, vendor.store_name)
            
            return Response(AdminVendorSerializer(vendor).data, status=status.HTTP_200_OK)
        
        return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)