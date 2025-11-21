# order/serializers.py
from rest_framework import serializers
import re
from .models import Order, OrderItem, Cart, CartItem, OrderStatusHistory, Payout
from product_app.models import Product 
from product_app.serializers import ProductSerializer # Import full ProductSerializer
from users.models import CustomUser

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
    items = CartItemSerializer(many=True, read_only=True)
    grand_total = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    guest_cart_id = serializers.CharField(source='guest_id', read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'guest_cart_id', 'items', 'total_items', 'grand_total']
        read_only_fields = ['id', 'user', 'guest_cart_id']

    def get_grand_total(self, obj):
        return round(float(sum(
            (item.quantity or 0) * (item.product.price or 0) 
            for item in obj.items.all() if item.product
        )), 2)

    def get_total_items(self, obj):
        return sum(item.quantity or 0 for item in obj.items.all())

# ----------------------------------------------------
# 2. ORDER & CUSTOMER SERIALIZERS
# ----------------------------------------------------
class ProductLiteSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()


    class Meta:
        model = Product
        fields = ['name', 'image_url']

    # def get_image_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.image:
    #         return request.build_absolute_uri(obj.image.url) if request else obj.image.url
    #     return None

    def get_image_url(self, obj):
        if obj.cloudinary_url:
            return obj.cloudinary_url  # ALWAYS use Cloudinary

        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)

        return None


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductLiteSerializer(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price'] 

class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source='changed_by.username', read_only=True)
    
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'timestamp', 'changed_by_name']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True) 
    history = StatusHistorySerializer(many=True, read_only=True)
    # ⭐️ ADDED: To show vendor/product names in Admin Order Dashboard
    vendor_name = serializers.SerializerMethodField()
    product_names = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 
            'razorpay_order_id', 
            'created_at', 
            'status', 
            'total_amount', 
            'items', 
            'history',
            'shipping_address',
            'vendor_name',   # ⭐️ ADDED
            'product_names',
              'tracking_number'  # ⭐️ ADDED
        ]
        
    def get_vendor_name(self, obj):
        # ⭐️ ADDED: Get unique vendor names from the order items
        vendors = {item.vendor.store_name for item in obj.items.all() if item.vendor}
        return ", ".join(vendors) if vendors else "N/A"

    def get_product_names(self, obj):
        # ⭐️ ADDED: Get product names
        products = [item.product.name for item in obj.items.all() if item.product]
        return ", ".join(products) if products else "N/A"

# ----------------------------------------------------
# 3. VENDOR SERIALIZERS
# ----------------------------------------------------
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
    items = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='user.username', read_only=True) 
    history = StatusHistorySerializer(many=True, read_only=True) 
    # ⭐️ ADDED: To show tracking number in vendor order list
    tracking_number = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'created_at', 'customer_name', 'items', 'history', 'tracking_number') # ⭐️ ADDED 'tracking_number'

    def get_items(self, obj):
        user = self.context['request'].user
        vendor_items = obj.items.filter(product__vendor=user)
        return VendorOrderItemSerializer(vendor_items, many=True, context=self.context).data

# ----------------------------------------------------
# 4. PAYOUT & BANK SERIALIZERS
# ----------------------------------------------------
class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser  # We are updating the CustomUser model
        fields = [
            'account_holder_name',
            'account_number',
            'ifsc_code',
            'upi_id'
        ]
        extra_kwargs = {
            'account_holder_name': {'required': False, 'allow_blank': True},
            'account_number': {'required': False, 'allow_blank': True},
            'ifsc_code': {'required': False, 'allow_blank': True},
            'upi_id': {'required': False, 'allow_blank': True},
        }

class PayoutSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    vendor_payment_details = serializers.SerializerMethodField()

    class Meta:
        model = Payout
        fields = [
            'id', 
            'amount', 
            'status', 
            'requested_at', 
            'vendor_name', 
            'vendor_email',
            'transaction_id',
            'vendor_payment_details'
        ]
        read_only_fields = [
            'id', 'amount', 'status', 'requested_at', 
            'vendor_name', 'vendor_email', 'transaction_id', 'vendor_payment_details'
        ]

    def get_vendor_payment_details(self, obj):
        vendor = obj.vendor
        return {
            'account_holder_name': vendor.account_holder_name,
            'account_number': vendor.account_number,
            'ifsc_code': vendor.ifsc_code,
            'upi_id': vendor.upi_id
        }

# ----------------------------------------------------
# 5. ADMIN EXPORT SERIALIZER
# ----------------------------------------------------
class AdminOrderExportSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_date = serializers.DateTimeField(source='order.created_at', read_only=True)
    order_total = serializers.DecimalField(source='order.total_amount', max_digits=10, decimal_places=2, read_only=True)
    payment_id = serializers.CharField(source='order.razorpay_payment_id', read_only=True, default='')
    customer_name = serializers.CharField(source='order.user.username', read_only=True)
    customer_email = serializers.CharField(source='order.user.email', read_only=True)
    shipping_address_flat = serializers.SerializerMethodField()
    shipping_phone = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category = serializers.CharField(source='product.category.name', read_only=True, default='N/A')
    vendor_store_name = serializers.CharField(source='product.vendor.store_name', read_only=True)
    # ⭐️ ADDED: vendor (for item-level vendor)
    vendor = serializers.CharField(source='vendor.store_name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'order_id', 'order_status', 'order_date', 'customer_name', 'customer_email', 
            'order_total', 'payment_id', 
            'shipping_address_flat', 'shipping_phone',
            'vendor_store_name', 'product_name', 'product_category', 'quantity', 'price',
            'vendor' # ⭐️ ADDED
        ]

    def get_shipping_address_flat(self, obj):
        address = obj.order.shipping_address
        if isinstance(address, dict):
            return f"{address.get('name', '')}, {address.get('street', '')}, {address.get('city', '')}"
        return str(address or 'N/A') 

    def get_shipping_phone(self, obj):
        address = obj.order.shipping_address
        if isinstance(address, dict):
            return address.get('phone', 'N/A')
        return 'N/A'