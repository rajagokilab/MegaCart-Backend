# order/models.py
from django.db import models
from django.conf import settings
from product_app.models import Product 
from decimal import Decimal # Make sure this is imported

# -----------------------------
# 1️⃣ Cart Model
# -----------------------------
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_id = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Guest Cart {self.guest_id}"

# -----------------------------
# 2️⃣ CartItem Model
# -----------------------------
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# -----------------------------
# 3️⃣ Order Model
# -----------------------------
class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, # Keeps order if user is deleted
        null=True,
        related_name='orders'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Fields for Razorpay
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Shipping address (copied from user at time of order)
    shipping_address = models.JSONField(null=True, blank=True)

    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.email if self.user else 'Deleted User'} ({self.status})"

# -----------------------------
# 4️⃣ OrderItem Model (FIXED)
# -----------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # ⭐️ ⬇️ THIS WAS INDENTED WRONGLY. IT MUST BE INSIDE THE CLASS. ⬇️ ⭐️
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        limit_choices_to={'role': 'VENDOR'}
    )
    
    # ⭐️ ⬇️ THIS WAS ALSO INDENTED WRONGLY. ⬇️ ⭐️
    def __str__(self):
        return f"{self.quantity} of {self.product.name if self.product else 'Deleted Product'}"
        
# -----------------------------
# 5️⃣ OrderStatusHistory Model
# -----------------------------
class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='history' # Critical for order.history.all() lookup
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    status = models.CharField(max_length=10, choices=Order.STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Order Status Histories"
        ordering = ['timestamp']

    def __str__(self):
        return f"Order {self.order.id} status changed to {self.status}"
    
# -----------------------------
# 6️⃣ Payout Model
# -----------------------------
class Payout(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('FAILED', 'Failed'),
    ]

    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'VENDOR'}
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True) # Set this when you complete the payment
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Payout for {self.vendor.username} - ₹{self.amount} ({self.status})"