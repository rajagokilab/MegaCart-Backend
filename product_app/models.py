from django.db import models
from django.conf import settings

# -----------------------------
# 1️⃣ Category Model
# -----------------------------
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


# -----------------------------
# 2️⃣ Product Model
# -----------------------------
class Product(models.Model):
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'VENDOR'} ,
        related_name='products'
    )
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="product_images/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 🛑 ADDED FIELDS FOR VENDOR APPROVAL WORKFLOW
    APPROVAL_STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    status = models.CharField(
        max_length=10, 
        choices=APPROVAL_STATUS_CHOICES,
        default='PENDING', # New products start as PENDING
        help_text='Approval status set by Admin.'
    )
    
    # is_published controls vendor visibility; status controls marketplace visibility.
    is_published = models.BooleanField(default=False) 

    def __str__(self):
        # We assume the vendor object has a store_name field for display
        return f"{self.name} ({self.vendor.store_name})"


# -----------------------------
# 3️⃣ Review Model
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


