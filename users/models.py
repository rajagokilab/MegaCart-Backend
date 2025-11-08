# In users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_ROLES = [
        ('CUSTOMER', 'Customer'),
        ('VENDOR', 'Vendor'),
        ('ADMIN', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=USER_ROLES, default='CUSTOMER')
    store_name = models.CharField(max_length=100, blank=True, null=True)
    is_approved = models.BooleanField(default=False)  # Vendors must be approved
    email = models.EmailField(unique=True)
    shipping_address = models.JSONField(null=True, blank=True)
    
    # 💰 --- ADD THESE 3 FIELDS ---
    store_description = models.TextField(blank=True, null=True)
    store_logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True)
    store_banner = models.ImageField(upload_to='vendor_banners/', blank=True, null=True)
    # -----------------------------

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'role']
    
    def __str__(self):
        return f"{self.email} ({self.role})"