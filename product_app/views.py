

# product_app/views.py

# product_app/views.py
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from .models import Product, Review
from .serializers import ProductSerializer, ReviewSerializer
User = get_user_model()
from rest_framework import viewsets
from .serializers import ProductSerializer
from django_filters.rest_framework import DjangoFilterBackend

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework import viewsets, views, status, serializers, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny, IsAdminUser
from django.db.models import Sum, Count, F

# --- 1. FIXED MODEL IMPORTS ---
from .models import Product, Category, Review  # From THIS app
from order.models import Order, OrderItem, Cart, CartItem  # From the 'order' app

# --- 2. FIXED SERIALIZER IMPORTS ---
from .serializers import ProductSerializer, CategorySerializer, ReviewSerializer # From THIS app
from order.serializers import CartSerializer, VendorOrderSerializer # From the 'order' app

from users.permissions import IsVendor, IsAdminOrVendorOwner 
User = get_user_model()

# product_app/views.py

from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework import viewsets, views, status, serializers, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, F
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, Category, Review
from .serializers import ProductSerializer, CategorySerializer, ReviewSerializer
from order.models import Cart, CartItem, Order, OrderItem
from order.serializers import CartSerializer
from users.permissions import IsVendor

User = get_user_model()


# ------------------ CART HELPER ------------------
def get_current_cart(request):
    """
    Returns the active cart for user or guest. Auto-creates guest cart if needed.
    """
    user = request.user if request.user.is_authenticated else None
    guest_id = request.headers.get("X-Guest-Cart-Id")

    try:
        if user:
            user_cart, _ = Cart.objects.get_or_create(user=user, is_active=True)
            if guest_id:
                # Merge guest cart into user cart
                guest_cart = Cart.objects.filter(guest_id=guest_id, is_active=True, user__isnull=True).first()
                if guest_cart:
                    for item in guest_cart.items.all():
                        existing, created = CartItem.objects.get_or_create(
                            cart=user_cart, product=item.product, defaults={"quantity": item.quantity}
                        )
                        if not created:
                            existing.quantity += item.quantity
                            existing.save()
                    guest_cart.is_active = False
                    guest_cart.save()
            return user_cart

        # Guest user
        if not guest_id:
            import uuid
            guest_id = str(uuid.uuid4())
            cart = Cart.objects.create(guest_id=guest_id, is_active=True)
            return cart

        cart, _ = Cart.objects.get_or_create(
            guest_id=guest_id, is_active=True, user__isnull=True
        )
        return cart

    except Exception as e:
        print("Error in get_current_cart:", e)
        raise serializers.ValidationError({"detail": "Internal server error."}, code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------ CATEGORY VIEW ------------------
# class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer
#     permission_classes = [AllowAny]


# In product_app/views.py
class CategoryViewSet(viewsets.ModelViewSet): # ✅ UPDATED
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # Allow anyone to read, but only admin to create/update/delete
    permission_classes_by_action = {
        'list': [AllowAny],
        'retrieve': [AllowAny],
        'create': [IsAdminUser],
        'update': [IsAdminUser],
        'partial_update': [IsAdminUser],
        'destroy': [IsAdminUser],
    }

    def get_permissions(self):
        try:
            # return permission_classes_by_action for specific action
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            # action is not set, return default permission_classes
            return [permission() for permission in self.permission_classes]

# ------------------ PRODUCT VIEW ------------------
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(status='APPROVED', is_published=True).select_related('category', 'vendor')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['vendor']
    search_fields = ['name', 'category__name', 'vendor__store_name']

    def get_queryset(self):
        queryset = Product.objects.all().select_related('category', 'vendor')
        vendor_id = self.request.query_params.get('vendor')
        if vendor_id and vendor_id.isdigit():
            queryset = queryset.filter(vendor_id=int(vendor_id))
        else:
            queryset = queryset.filter(status='APPROVED', is_published=True)

        user = self.request.user
        if user.is_authenticated:
            if user.is_superuser or getattr(user, 'role', None) == 'ADMIN':
                return queryset
            elif getattr(user, 'role', None) == 'VENDOR':
                return queryset.filter(vendor=user)
        return queryset

    @action(detail=False, url_path=r'by-category/(?P<category_slug>[-\w]+)')
    def by_category(self, request, category_slug=None):
        products = self.get_queryset().filter(category__slug=category_slug)
        return Response(self.get_serializer(products, many=True).data)

    @action(detail=True, methods=['get'])
    def suggestions(self, request, pk=None):
        product = self.get_object()
        suggestions = Product.objects.filter(
            category=product.category, status='APPROVED', is_published=True
        ).exclude(pk=pk)[:4]
        serializer = self.get_serializer(suggestions, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) != 'VENDOR' and not user.is_superuser:
            raise serializers.ValidationError({"detail": "Only vendors can create products."})
        serializer.save(vendor=user, status='PENDING')

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def approve(self, request, pk=None):
        if not request.user.is_superuser:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        product = self.get_object()
        new_status = request.data.get('status')
        if new_status in ['APPROVED', 'REJECTED']:
            product.status = new_status
            product.save(update_fields=['status'])
            return Response(ProductSerializer(product).data)
        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)


# ------------------ REVIEW VIEW ------------------
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        pid = self.kwargs.get('product_pk')
        return Review.objects.filter(product_id=pid) if pid else Review.objects.all()

    def perform_create(self, serializer):
        pid = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=pid)
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError({"detail": "You already reviewed this product."})
        serializer.save(user=self.request.user, product=product)


# ------------------ CART VIEWS ------------------
class CartAddItemView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            cart = get_current_cart(request)
            product_id = request.data.get("product_id")
            if not product_id:
                return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            quantity = int(request.data.get("quantity", 1))
            product = get_object_or_404(Product, pk=product_id, status='APPROVED', is_published=True)

            if quantity < 1:
                return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

            item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
            if not created:
                item.quantity += quantity
                item.save()

            return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CartDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_current_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartUpdateItemView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        cart = get_current_cart(request)
        item_id = request.data.get("item_id")
        quantity = int(request.data.get("quantity", 1))
        item = get_object_or_404(CartItem, cart=cart, id=item_id)
        if quantity <= 0:
            item.delete()
        else:
            item.quantity = quantity
            item.save()
        return Response(CartSerializer(cart, context={'request': request}).data)


class CartRemoveItemView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, product_id):
        cart = get_current_cart(request)
        product = get_object_or_404(Product, pk=product_id)
        cart_item = get_object_or_404(CartItem, cart=cart, product=product)
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# ------------------ ADDRESS VIEW ------------------
class SaveAddressView(views.APIView):
    # ... (permission_classes are fine) ...

    def post(self, request):
        user = request.user
        data = request.data # This is the address object {name: ..., street: ...}

        try:
            # --- FIX: Save the entire object to the JSONField ---
            user.shipping_address = data 
            # Note: The 'shipping_address' field MUST be defined on your CustomUser model.
            user.save(update_fields=['shipping_address'])
            
            return Response({"message": "Address saved successfully."}, status=status.HTTP_200_OK)
        
        except Exception as e:
            # If the user model doesn't have shipping_address, it will land here
            print(f"Error saving address: {e}")
            return Response({"error": f"Internal Error: Check user model fields."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ------------------ VENDOR DASHBOARD & ORDERS ------------------
class VendorDashboardView(views.APIView):
    permission_classes = [IsAuthenticated, IsVendor]
    def get(self, request):
        vendor = request.user
        order_items = OrderItem.objects.filter(product__vendor=vendor, order__status='Paid')
        
        sales_summary = order_items.aggregate(
            total_earnings=Sum(F('quantity') * F('price')),
            total_orders=Count('order', distinct=True) 
        )
        active_products = Product.objects.filter(vendor=vendor, status='APPROVED', is_published=True).count()
        unique_customers = Order.objects.filter(
            items__product__vendor=vendor, status='Paid'
        ).aggregate(count=Count('user', distinct=True))['count'] or 0

        response_data = {
            "total_earnings": sales_summary['total_earnings'] or 0,
            "total_orders": sales_summary['total_orders'] or 0,
            "active_products": active_products,
            "unique_customers": unique_customers,
        }
        return Response(response_data, status=status.HTTP_200_OK)

# product_app/views.py

# ... (other imports)
from .serializers import ProductSerializer, ReviewSerializer
from .models import Product, Review
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
User = get_user_model()
from django.db.models import Count
# ... (other views)


# --- View 1: Fetches the vendor's products ---
class VendorStorefrontView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_pk']
        return Product.objects.filter(
            vendor__id=vendor_id,
            status='APPROVED',
            is_published=True
        ).select_related('category', 'vendor').order_by('-created_at')


# --- View 2: Fetches the vendor's settings (banner, logo) ---
class VendorStorefrontSettingsView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]

    def get(self, request, vendor_pk):
        vendor = User.objects.filter(id=vendor_pk, role='VENDOR', is_approved=True).first()
        if not vendor:
            return Response({"detail": "Vendor not found"}, status=404)

        # 💰 2. THIS IS THE CORRECT QUERY FOR "TOTAL SALES"
        # We count distinct 'Paid' orders that contain a product from this vendor
        total_sales_count = Order.objects.filter(
            items__product__vendor=vendor, 
            status='Paid'
        ).distinct().count()

        data = {
            "store_name": vendor.store_name,
            "store_logo": vendor.store_logo.url if vendor.store_logo else None,
            "store_banner": vendor.store_banner.url if vendor.store_banner else None,
            "store_description": vendor.store_description,
            
            # 💰 3. USE THE CORRECT COUNT
            "total_sales": total_sales_count
            
            # ❌ OLD BUGGY LINE (for reference):
            # "total_sales": vendor.reviews.aggregate(total=Count('id'))['total'] if hasattr(vendor, 'reviews') else 0
        }
        return Response(data)


# --- View 3: Fetches the vendor's reviews ---
class VendorStorefrontReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        vendor_id = self.kwargs['vendor_pk']
        return Review.objects.filter(product__vendor__id=vendor_id).select_related('user', 'product').order_by('-created_at')


# In product_app/views.py
# (Add these new classes at the end of the file)

from rest_framework.permissions import IsAdminUser
from rest_framework import viewsets, views, status, generics
from django.db.models import Sum, Count, F, Value
from django.db.models.functions import Coalesce


# Make sure to import all the models and serializers you need
from users.models import CustomUser
from order.models import Order, OrderItem
from .models import Product
from .serializers import (
    ProductSerializer, 
    AdminVendorSerializer, 
    AdminOrderSerializer
)


# --- 1. View for Admin Dashboard Stats (A-1) ---
# In product_app/views.py

# --- 1. MAKE SURE YOU IMPORT THESE AT THE TOP ---
from .models import Product, Category, Review
from order.models import Order, OrderItem, Cart, CartItem # 💰 IMPORT OrderItem
from users.models import CustomUser
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import viewsets, views, status, generics
from rest_framework.permissions import IsAdminUser
from decimal import Decimal
# ... (all your other imports)

# In product_app/views.py

class AdminDashboardStatsView(views.APIView):
    # ... (permission_classes)

    def get(self, request):

        total_sales = OrderItem.objects.filter(order__status='Paid').aggregate(
            total=Coalesce(
                Sum(F('quantity') * F('price'), output_field=DecimalField()), 
                0, 
                output_field=DecimalField()
            )
        )['total']

        # 💰 2. THIS IS THE FIX:
        total_commission = total_sales * Decimal('0.10') # <-- Use Decimal('0.10') instead of 0.10

        new_orders_count = Order.objects.filter(status='Paid').count()

        pending_vendors_count = CustomUser.objects.filter(
            role='VENDOR', 
            is_approved=False
        ).count()

        stats = {
            "total_sales": total_sales,
            "total_commission": round(total_commission, 2), # round() is still good practice
            "new_orders": new_orders_count,
            "pending_vendors": pending_vendors_count
        }
        return Response(stats, status=status.HTTP_200_OK)
# --- 2. View for Listing Pending Vendors (A-2) ---
class AdminVendorsView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminVendorSerializer
    queryset = CustomUser.objects.filter(role='VENDOR', is_approved=False)


# --- 3. View for Approving/Rejecting Vendors (A-2) ---
class AdminApproveVendorView(views.APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, vendor_id):
        try:
            vendor = CustomUser.objects.get(id=vendor_id, role='VENDOR')
        except CustomUser.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)
            
        action = request.data.get('action') # "APPROVE" or "REJECT"
        
        if action == "APPROVE":
            vendor.is_approved = True
            vendor.save()
            return Response({"status": "Vendor approved"}, status=status.HTTP_200_OK)
        
        elif action == "REJECT":
            vendor.delete() # Or set is_active=False
            return Response({"status": "Vendor rejected and deleted"}, status=status.HTTP_200_OK)
            
        return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)


# --- 4. ViewSet for Managing All Products (A-4) ---
class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ProductSerializer
    queryset = Product.objects.all().select_related('vendor', 'category')
    

# --- 5. View for Listing All Orders (A-5) ---
class AdminOrdersView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminOrderSerializer
    queryset = Order.objects.all().prefetch_related('items', 'items__product').order_by('-created_at')