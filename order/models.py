from django.db import models
from django.conf import settings
# Import your Product model
from product_app.models import Product 

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

    def __str__(self):
        return f"Order {self.id} by {self.user.email if self.user else 'Deleted User'} ({self.status})"

# -----------------------------
# 4️⃣ OrderItem Model
# -----------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, # Keeps order history if product is deleted
        null=True,
        related_name='order_items' # This fixes the 'clash' error
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of purchase

    def __str__(self):
        return f"{self.quantity} of {self.product.name if self.product else 'Deleted Product'}"

# order/models.py
from django.db import models
from django.conf import settings
from product_app.models import Product 

# --- (Your existing Cart, CartItem, and Order models remain here) ---

# -----------------------------
# 5️⃣ OrderStatusHistory Model (NEW)
# -----------------------------
class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        'Order', 
        on_delete=models.CASCADE, 
        related_name='history' # Critical for order.history.all() lookup
    )
    # The user who changed the status (Admin or Vendor)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    # The status that the order changed TO
    status = models.CharField(max_length=10, choices=Order.STATUS_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Order Status Histories"
        ordering = ['timestamp']

    def __str__(self):
        return f"Order {self.order.id} status changed to {self.status}"