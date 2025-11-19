from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, OrderStatusHistory, Payout

# --- 1. Inline for OrderItem ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product'] 
    extra = 0
    readonly_fields = ['price', 'vendor'] # Added vendor as readonly

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
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
    
    fieldsets = (
        (None, {
            'fields': ('user', 'total_amount', 'status')
        }),
        ('Shipping Details', {
            'fields': ('shipping_address', 'tracking_number')
        }),
        ('Payment Records', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')
        }),
    )
    
    inlines = [OrderItemInline]
    
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

# --- 3. ADDED: Payout and History Admin ---

@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'timestamp', 'changed_by')
    list_filter = ('status', 'timestamp')
    search_fields = ('order__id',)

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'vendor', 'amount', 'status', 'requested_at', 'paid_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('vendor__email', 'vendor__store_name')
    list_editable = ('status',) # Allows quick updates from the list view
    readonly_fields = ('vendor', 'amount', 'requested_at', 'paid_at', 'transaction_id')