from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import authenticate
from order.models import Payout, Order
from product_app.models import Product
from django.db.models import Sum, Count

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # ✅ Correctly configured to SAVE data
        fields = ('email', 'username', 'password', 'role', 'store_name', 'business_reg_id', 'kyc_document')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'CUSTOMER'),
            store_name=validated_data.get('store_name', None),
            # ✅ Correctly saving to database
            business_reg_id=validated_data.get('business_reg_id', None),
            kyc_document=validated_data.get('kyc_document', None),
            is_approved=validated_data.get('role') != 'VENDOR'
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

# 🔴 UPDATE THIS SERIALIZER 🔴
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # ✅ Added 'business_reg_id' and 'kyc_document' so they appear in the response
        fields = ('id', 'username', 'email', 'role', 'store_name', 'business_reg_id', 'kyc_document', 'is_active', 'is_staff', 'date_joined','vendor_status','business_reg_id','business_reg_id', 
            'shipping_address')

class StorefrontUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('store_name', 'store_description', 'store_logo', 'store_banner')

class AdminVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'store_name', 'is_approved']

class AdminVendorListSerializer(serializers.ModelSerializer):
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_orders = serializers.SerializerMethodField()
    total_products = serializers.SerializerMethodField()
    active_products = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'store_name', 'email', 'is_approved', 'date_joined','vendor_status',
            'total_sales',
            'total_orders', 
            'total_products',
            'active_products', 
            'available_for_payout',
            'account_holder_name', 'account_number', 'ifsc_code', 'upi_id',
        ]

    def get_total_orders(self, obj):
        return Order.objects.filter(items__product__vendor=obj).distinct().count()

    def get_total_products(self, obj):
        return Product.objects.filter(vendor=obj).count()

    def get_active_products(self, obj):
        return Product.objects.filter(vendor=obj, status='APPROVED').count()
    
class VendorKYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('kyc_document',)