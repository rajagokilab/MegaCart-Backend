# users/permissions.py

from rest_framework.permissions import BasePermission

class IsVendor(BasePermission):
    """
    Custom permission to only allow access to users with role='VENDOR'.
    """
    def has_permission(self, request, view):
        # Checks if user is authenticated AND has the VENDOR role.
        return request.user.is_authenticated and request.user.role == 'VENDOR'

from rest_framework.permissions import BasePermission

class IsAdminOrVendorOwner(BasePermission):
    """
    Allows full access to Admins, and CRUD access to the Vendor who owns the object.
    Used for VendorProductViewSet (Product Management).
    """

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or user.role == 'ADMIN' or user.role == 'VENDOR'

    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admins (Superusers) can do anything
        if user.is_superuser or user.role == 'ADMIN':
            return True
        
        # Read-only requests allowed
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        
        # Write operations only allowed if Vendor owns the object
        if user.role == 'VENDOR':
            return obj.vendor == user
        
        return False
