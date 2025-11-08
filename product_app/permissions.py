# product_app/permissions.py

from rest_framework.permissions import BasePermission

class IsVendor(BasePermission):
    """Allows access only to authenticated users with role='VENDOR'."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'VENDOR'

class IsAdminOrVendorOwner(BasePermission):
    """
    Allows full access to Admins, and read/write access to the Vendor who owns the object.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Admins (Superusers) can do anything
        if user and user.is_superuser:
            return True
            
        # Read permissions are allowed to everyone (handled by ProductViewSet)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True

        # Write permissions (POST, PUT, PATCH, DELETE) only if user is the vendor
        return obj.vendor == user