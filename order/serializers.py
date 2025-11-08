# order/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem
from product_app.models import Product 

# --- Serializer for Customer's "My Orders" Page ---

class ProductLiteSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['name', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:  # change 'image' to whatever your Product model field is
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializes an order item, showing the product details.
    """
    # Use the serializer above to nest product details
    product = ProductLiteSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price'] 

class OrderSerializer(serializers.ModelSerializer):
    """
    Serializes a customer's order, including all its items.
    """
    # 'items' is the related_name from your OrderItem model
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'razorpay_order_id', 'items']


# --- Serializers for Vendor's "Orders" Dashboard ---

class VendorOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product_name', 'product_image', 'quantity', 'price')

    def get_product_image(self, obj):
        request = self.context.get("request")
        if obj.product and getattr(obj.product, 'image_url', None):
            if request:
                return request.build_absolute_uri(obj.product.image_url)
            return obj.product.image_url
        return None




class VendorOrderSerializer(serializers.ModelSerializer):
    """
    Shows an order, but filters its 'items' to only include
    products belonging to the currently logged-in vendor.
    """
    items = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='user.username', read_only=True) 

    class Meta:
        model = Order
        fields = ('id', 'status', 'created_at', 'customer_name', 'items')

    def get_items(self, obj):
        # 'obj' is the Order instance.
        # We get the 'request' from the context passed by the view.
        user = self.context['request'].user
        
        # This is the magic: filter items for this order
        # based on the new 'product__vendor' (CustomUser) link
        vendor_items = obj.items.filter(product__vendor=user)
        
        # Now serialize just those items
        # We pass 'context' again so the image URL can be built
        return VendorOrderItemSerializer(vendor_items, many=True, context=self.context).data
    

    from rest_framework import serializers
from .models import Order, OrderItem, Cart, CartItem
from product_app.models import Product 
# Import the serializer for Product details
from product_app.serializers import ProductSerializer 

# ----------------------------------------------------
# 1. CART SERIALIZERS
# ----------------------------------------------------
class CartItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source='product', read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
    source='product',
    queryset=Product.objects.all(),
    write_only=True
)

    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'product_details', 'quantity', 'total_price']
        read_only_fields = ['id', 'product_details', 'total_price']

    def get_total_price(self, obj):
        if obj.product:
            return float(obj.quantity * obj.product.price)
        return 0.0

class CartSerializer(serializers.ModelSerializer):
    """
    Serializes the main cart, including all its items and totals.
    """
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    guest_cart_id = serializers.CharField(source='guest_id', read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'guest_cart_id', 'items', 'total_items', 'grand_total']
        read_only_fields = ['id', 'user', 'guest_cart_id']

    def get_grand_total(self, obj):
        # Safely calculate total, even if a product was deleted
        return round(float(sum(
            (item.quantity or 0) * (item.product.price or 0) 
            for item in obj.items.all() if item.product
        )), 2)

    def get_total_items(self, obj):
        return sum(item.quantity or 0 for item in obj.items.all())
    

    # order/serializers.py

from .models import Order, OrderItem, OrderStatusHistory # 👈 Ensure this is imported

# --- NEW HISTORY SERIALIZER ---
class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'timestamp', 'changed_by_name']
# --- End NEW HISTORY SERIALIZER ---


# --- Update OrderSerializer (Used for Customer MyOrdersPage) ---
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    # 👇 ADD THE HISTORY FIELD 👇
    history = StatusHistorySerializer(many=True, read_only=True) 
    
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'razorpay_order_id', 'items', 'history']
    