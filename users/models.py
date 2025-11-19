from django.contrib.auth.models import AbstractUser
from django.db import models
from decimal import Decimal

class CustomUser(AbstractUser):
    USER_ROLES = [
        ('CUSTOMER', 'Customer'),
        ('VENDOR', 'Vendor'),
        ('ADMIN', 'Admin'),
    ]
    role = models.CharField(max_length=10, choices=USER_ROLES, default='CUSTOMER')
    store_name = models.CharField(max_length=100, blank=True, null=True)
    is_approved = models.BooleanField(default=False) 
    email = models.EmailField(unique=True)
    shipping_address = models.JSONField(null=True, blank=True)
    
    # 💰 Additional fields
    store_description = models.TextField(blank=True, null=True)
    store_logo = models.ImageField(upload_to='vendor_logos/', blank=True, null=True)
    store_banner = models.ImageField(upload_to='vendor_banners/', blank=True, null=True)


    total_sales = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Total gross sales for this vendor (before commission)"
    )
    
    # ⭐️ NEW FIELD TO TRACK TOTAL EARNED (The Blue Card)
    lifetime_net_earnings = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00')
    )
    
    # ✅ CURRENT BALANCE (The Green Card)
    available_for_payout = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    
    # Manual/Automated Payment Details
    razorpay_account_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    account_holder_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    upi_id = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'role']
    
    def __str__(self):
        return f"{self.email} ({self.role})"