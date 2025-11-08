# users/permissions.py

from rest_framework.permissions import BasePermission

class IsVendor(BasePermission):
    """
    Custom permission to only allow access to users with role='VENDOR'.
    """
    def has_permission(self, request, view):
        # Checks if user is authenticated AND has the VENDOR role.
        return request.user.is_authenticated and request.user.role == 'VENDOR'

# 🛑 ADD THIS MISSING CLASS 🛑
class IsAdminOrVendorOwner(BasePermission):
    """
    Allows full access to Admins, and CRUD access to the Vendor who owns the object.
    Used for VendorProductViewSet (Product Management).
    """
    # 1. Checks general permission (Is the user an Admin or Vendor?)
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        # Allow if Admin/Superuser or a Vendor
        return user.is_superuser or user.role == 'ADMIN' or user.role == 'VENDOR'

    # 2. Checks object-level permission (Is the Vendor modifying their own product?)
    def has_object_permission(self, request, view, obj):
        user = request.user
            
        # Admins (Superusers) can do anything
        if user.is_superuser or user.role == 'ADMIN':
            return True
            
        # Read operations (GET) are generally allowed by has_permission, 
        # but for safety, we allow it here if the user is authenticated.
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True 
            
        # Write operations (PUT, PATCH, DELETE) require the user to be the owner
        if user.role == 'VENDOR':
            # obj is the product instance; obj.vendor is the user who owns it.
            return obj.vendor == user
            
        return False