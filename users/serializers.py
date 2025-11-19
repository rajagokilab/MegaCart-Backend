from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import authenticate
from order.models import Payout, Order
from product_app.models import Product
from django.db.models import Sum, Count

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'password', 'role', 'store_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'CUSTOMER'),
            store_name=validated_data.get('store_name', None),
            is_approved=validated_data.get('role') != 'VENDOR'  # auto-approve non-vendors
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if user.role == 'VENDOR' and not user.is_approved:
            raise serializers.ValidationError("Vendor account not approved yet")
        return {'user': user}

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'role', 'store_name', 'is_active', 'is_staff')

class StorefrontUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('store_name', 'store_description', 'store_logo', 'store_banner')

class AdminVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'store_name', 'is_approved']


# ---
# --- THIS SERIALIZER IS NOW FIXED ---
# ---
class AdminVendorListSerializer(serializers.ModelSerializer):
    """
    Serializer for the "All Vendors" list in the admin panel.
    Reads pre-calculated stats from the model.
    """
    # ⭐️ FIX: Changed from SerializerMethodField to read directly from the model
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    total_orders = serializers.SerializerMethodField()
    total_products = serializers.SerializerMethodField()
    active_products = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'store_name', 'email', 'is_approved', 'date_joined',
            
            # Stats
            'total_sales', # ⭐️ This will now correctly read the 'total_sales' field
            'total_orders', 
            'total_products',
            'active_products', 
            'available_for_payout', # This was already correct

            # Manual Payment Details
            'account_holder_name', 'account_number', 'ifsc_code', 'upi_id',
        ]

    # ⭐️ FIX: Removed the buggy 'get_total_sales' method.
    # It will now use the 'total_sales' field from the model by default.

    def get_total_orders(self, obj):
        # Count distinct orders containing this vendor's products
        return Order.objects.filter(items__product__vendor=obj).distinct().count()

    def get_total_products(self, obj):
        # Count of ALL products (Pending, Approved, etc.)
        return Product.objects.filter(vendor=obj).count()

    def get_active_products(self, obj):
        # Count of only APPROVED products
        return Product.objects.filter(vendor=obj, status='APPROVED').count()