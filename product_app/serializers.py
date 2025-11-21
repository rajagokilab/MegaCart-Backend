from rest_framework import serializers
from django.db import models
from django.db.models import Sum, F # <-- 1. IMPORT Sum & F

# --- 2. IMPORT ALL MODELS ---
from .models import Category, Product, Review
from order.models import Cart, CartItem, Order, OrderItem # <-- IMPORT Order & OrderItem
from users.models import CustomUser # <-- IMPORT CustomUser

# ----------------------------------------------------
# 1. REVIEW SERIALIZER (Correct)
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
# 2. PRODUCT SERIALIZER (Correct)
# ----------------------------------------------------
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.store_name', read_only=True)

    image_url = serializers.SerializerMethodField()
    # image_url = serializers.CharField(read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name', 
            'vendor', 'vendor_name', 
            'price', 'stock', 'image', 'image_url', 'is_published',
            'reviews', 'average_rating', 'status','created_at'
        ]
        read_only_fields = ['vendor', 'vendor_name', 'status']

    # def get_image_url(self, obj):
    #     request = self.context.get("request", None)
    #     if obj.image:
    #         if request:
    #             return request.build_absolute_uri(obj.image.url)
    #         return obj.image.url
    #     return None

    def get_image_url(self, obj):
        if obj.cloudinary_url:
            return obj.cloudinary_url
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url)
        return None


    def get_average_rating(self, obj):
        avg = obj.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return round(avg, 1) if avg is not None else None


# ----------------------------------------------------
# 3. CATEGORY SERIALIZER (Correct)
# ----------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()
    # image_url = serializers.CharField(read_only=True)
    
    

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'products', 'image', 'image_url']  # ✅ include image_url

    # def get_image_url(self, obj):
    #     request = self.context.get('request')
    #     if obj.image and hasattr(obj.image, 'url'):
    #         return request.build_absolute_uri(obj.image.url)
    #     return None


    def get_image_url(self, obj):
            if obj.image:
                return obj.image.url  # CloudinaryField provides full URL
            return None




# ----------------------------------------------------
# 4. 💰 --- ADMIN SERIALIZERS (These were missing) ---
# ----------------------------------------------------

# --- Serializer for the Admin "Vendor Applications" list ---
class AdminVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'store_name', 'is_approved']

# --- Serializer for nested Order Items (for the "All Orders" list) ---
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
            'product_category_name' # 💰 --- AND ADD IT HERE ---
        ]
# --- Serializer for the "All Orders" list (Corrected) ---
class AdminOrderSerializer(serializers.ModelSerializer):
    items = AdminOrderItemSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 
            'user_email', 
            'total_amount', # Use the method field
            'status', 
            'items', 
            'created_at'
        ]
        
    def get_total_amount(self, obj):
        # Calculate the total from its items
        total = obj.items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total']
        return total or 0