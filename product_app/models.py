from django.db import models
from django.conf import settings
from decimal import Decimal # Required for price calculation
from cloudinary.models import CloudinaryField

# -----------------------------
# 1. Category Model
# -----------------------------
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    image = CloudinaryField('image', blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this category")

    def __str__(self):
        return self.name

# -----------------------------
# 2. Product Model
# -----------------------------
class Product(models.Model):
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'VENDOR'} ,
        related_name='products'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.PositiveIntegerField(default=0, help_text="Discount in % (0-100)")
    
    stock = models.PositiveIntegerField(default=0)
    image = CloudinaryField('image', blank=True, null=True)
    
    # Old ImageField kept for fallback if needed, but using CloudinaryField primarily
    # image = models.ImageField(upload_to='product_images/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Added updated_at for tracking
    
    # APPROVAL WORKFLOW
    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    status = models.CharField(
        max_length=10, 
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING', 
        help_text='Approval status set by Admin.'
    )
    
    is_published = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.name} ({self.vendor.store_name})"

    @property
    def discounted_price(self):
        """
        Calculates the price after the discount percentage is applied.
        """
        if self.discount_percentage > 0:
            discount_amount = (self.price * Decimal(self.discount_percentage)) / Decimal(100)
            return round(self.price - discount_amount, 2)
        return self.price

# -----------------------------
# 3. Review Model
# -----------------------------
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')

    RATING_CHOICES = [(1,'1'), (2,'2'), (3,'3'), (4,'4'), (5,'5')]
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.rating})"