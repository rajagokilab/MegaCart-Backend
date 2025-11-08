from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

# --- 1. Inline for OrderItem ---
# This allows the Admin to see all items when viewing a single Order object.
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    # Use raw_id_fields for ForeignKey lookups (more efficient for many products)
    raw_id_fields = ['product'] 
    extra = 0 # Don't show extra empty forms by default
    readonly_fields = ['price'] # Price should be fixed after order is placed

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Order model.
    """
    list_display = (
        'id', 
        'user', 
        'total_amount', 
        'status', 
        'created_at', 
        'razorpay_payment_id'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'razorpay_order_id', 'user__email')
    
    # Fields shown when editing/viewing a single order
    fieldsets = (
        (None, {
            'fields': ('user', 'total_amount', 'status')
        }),
        ('Shipping Details', {
            'fields': ('shipping_address',)
        }),
        ('Payment Records', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')
        }),
    )
    
    inlines = [OrderItemInline]
    
    # These fields are set during the transaction and should not be editable by admin manually
    readonly_fields = (
        'user', 
        'total_amount',
        'created_at',
        'razorpay_order_id', 
        'razorpay_payment_id', 
        'razorpay_signature', 
        'shipping_address'
    )

# --- 2. Cart Management ---

class CartItemInline(admin.TabularInline):
    model = CartItem
    raw_id_fields = ['product']
    extra = 0

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'guest_id', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'guest_id')
    inlines = [CartItemInline]
    readonly_fields = ('user', 'guest_id')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity')
    list_filter = ('cart__is_active',)
    search_fields = ('product__name',)