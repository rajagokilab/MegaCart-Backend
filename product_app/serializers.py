from rest_framework import serializers
from django.db import models
from django.db.models import Sum, F

# Adjust imports based on your actual project structure if needed
from .models import Category, Product, Review
from order.models import Cart, CartItem, Order, OrderItem
from users.models import CustomUser

# ----------------------------------------------------
# 1. REVIEW SERIALIZER
# ----------------------------------------------------
class ReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'user', 'user_username', 'product', 
            'product_name', 'rating', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'product', 'created_at']


# ----------------------------------------------------
# 2. PRODUCT SERIALIZER (FIXED)
# ----------------------------------------------------
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True)

    image_url = serializers.SerializerMethodField()
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    cloudinary_url = serializers.CharField(read_only=True)
    
    # Calculated Fields
    discounted_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    # 🚨 FIX: Explicitly define sales_count so it doesn't crash if missing from model
    sales_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name', 
            'vendor', 'vendor_name', 
            'price', 
            'discount_percentage',
            'discounted_price',     
            'stock', 
            'sales_count', # ✅ Now this maps to the method below
            'image', 'image_url', 'is_published', 'cloudinary_url',
            'reviews', 'average_rating', 'review_count', 'status', 'created_at'
        ]
        read_only_fields = ['vendor', 'vendor_name', 'status', 'created_at', 'updated_at', 'discounted_price']

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url 
        return None

    def get_average_rating(self, obj):
        # Safe aggregation
        avg = obj.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else 0

    def get_review_count(self, obj):
        return obj.reviews.count()

    # 🚨 FIX: This method handles the missing field safely
    def get_sales_count(self, obj):
        # If the view annotated 'sales_count', use it. Otherwise return 0.
        return getattr(obj, 'sales_count', 0)


# ----------------------------------------------------
# 3. CATEGORY SERIALIZER
# ----------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField(method_name='get_category_image_url')

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'products', 'image', 'image_url'] 

    def get_category_image_url(self, obj):
        if obj.image:
            return obj.image.url 
        return None


# ----------------------------------------------------
# 4. ADMIN SERIALIZERS
# ----------------------------------------------------
class AdminVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'store_name', 'is_approved']

class AdminOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_category_name = serializers.CharField(source='product.category.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 
            'product_name', 
            'quantity', 
            'price', 
            'product_category_name'
        ]

class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 
            'user_email', 
            'total_amount',
            'status', 
            'items', 
            'created_at'
        ]
        
    def get_total_amount(self, obj):
        total = obj.items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total']
        return total or 0