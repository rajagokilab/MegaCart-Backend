# product_app/views.py

import logging
import io
import pandas as pd
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, F, Q, Avg, DecimalField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, views, status, serializers, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    IsAuthenticated, 
    IsAuthenticatedOrReadOnly, 
    AllowAny, 
    IsAdminUser
)
# This is the import you were missing at the top
from rest_framework.views import APIView 

# --- 1. IMPORT MODELS ---
from .models import Product, Category, Review
from order.models import Cart, CartItem, Order, OrderItem
from users.models import CustomUser

# --- 2. IMPORT SERIALIZERS ---
from .serializers import (
    ProductSerializer, 
    CategorySerializer, 
    ReviewSerializer, 
    AdminVendorSerializer, 
    AdminOrderSerializer
)
from order.serializers import CartSerializer

# --- 3. IMPORT PERMISSIONS ---
from users.permissions import IsVendor, IsAdminOrVendorOwner

User = get_user_model()
logger = logging.getLogger(__name__)

# ------------------
# CART HELPER
# ------------------
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
        logger.error(f"Error in get_current_cart: {e}", exc_info=True)
        raise serializers.ValidationError({"detail": "Internal server error."}, code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ------------------
# 1. CATEGORY VIEWSET
# ------------------
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
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
            return [permission() for permission in self.permission_classes_by_action[self.action]]
        except KeyError:
            return [permission() for permission in self.permission_classes]

# ------------------
# 2. PRODUCT VIEWSET
# ------------------
from rest_framework.parsers import MultiPartParser, FormParser # <--- 1. ADD THIS IMPORT
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['vendor', 'category']
    search_fields = ['name', 'category__name', 'vendor__store_name']

    def get_queryset(self):
        user = self.request.user
        
        # Admin sees all products in any state
        if user.is_authenticated and user.role == 'ADMIN':
            return Product.objects.all().select_related('category', 'vendor')
        
        # Vendor sees all of THEIR products in any state
        if user.is_authenticated and user.role == 'VENDOR':
            return Product.objects.filter(vendor=user).select_related('category', 'vendor')
            
        # Public (customer or guest) sees only APPROVED & PUBLISHED products
        return Product.objects.filter(status='APPROVED', is_published=True).select_related('category', 'vendor')

    @action(detail=False, url_path=r'by-category/(?P<category_slug>[-\w]+)')
    def by_category(self, request, category_slug=None):
        products = self.get_queryset().filter(category__slug=category_slug)
        return Response(self.get_serializer(products, many=True).data)

    @action(detail=True, methods=['get'])
    def suggestions(self, request, pk=None):
        product = self.get_object()
        suggestions = self.get_queryset().filter(category=product.category).exclude(pk=pk)[:4]
        serializer = self.get_serializer(suggestions, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.role == 'VENDOR' or user.is_superuser):
            raise serializers.ValidationError({"detail": "Only vendors can create products."})
        # New products start as PENDING and NOT PUBLISHED
        serializer.save(vendor=user, status='PENDING', is_published=False)
        
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def approve(self, request, pk=None):
        product = self.get_object()
        new_status = request.data.get('status')
        if new_status in ['APPROVED', 'REJECTED']:
            product.status = new_status
            product.save(update_fields=['status'])
            return Response(ProductSerializer(product).data)
        return Response({"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

# ------------------
# 3. REVIEW VIEWSET
# ------------------
class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        product_id = self.kwargs.get('product_pk__pk')
        if not product_id:
            return Review.objects.none() # Don't list all reviews
        return Review.objects.filter(product_id=product_id)

    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_pk__pk')
        product = get_object_or_404(Product, id=product_id)
        
        if Review.objects.filter(product=product, user=self.request.user).exists():
            raise serializers.ValidationError({"detail": "You already reviewed this product."})
        serializer.save(user=self.request.user, product=product)

# ------------------
# 4. CART VIEWS
# ------------------
class CartAddItemView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        cart = get_current_cart(request)
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))

        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if quantity < 1:
            return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(Product, pk=product_id, status='APPROVED', is_published=True)

        item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': quantity})
        if not created:
            item.quantity += quantity
            item.save()
        return Response(CartSerializer(cart, context={'request': request}).data, status=status.HTTP_200_OK)


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

# ------------------
# 5. VENDOR STOREFRONT VIEWS (Public)
# ------------------
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


class VendorStorefrontSettingsView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    def get(self, request, vendor_pk):
        vendor = User.objects.filter(id=vendor_pk, role='VENDOR', is_approved=True).first()
        if not vendor:
            return Response({"detail": "Vendor not found"}, status=404)

        total_sales_count = Order.objects.filter(
            items__product__vendor=vendor, 
            status__in=['Paid', 'Shipped', 'Delivered']
        ).distinct().count()

        data = {
            "store_name": vendor.store_name,
            "store_logo": vendor.store_logo.url if vendor.store_logo else None,
            "store_banner": vendor.store_banner.url if vendor.store_banner else None,
            "store_description": vendor.store_description,
            "total_sales": total_sales_count
        }
        return Response(data)


class VendorStorefrontReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        vendor_id = self.kwargs['vendor_pk']
        return Review.objects.filter(
            product__vendor__id=vendor_id
        ).select_related('user', 'product').order_by('-created_at')


# ------------------
# 6. ADMIN-ONLY VIEWS
# ------------------
class AdminDashboardStatsView(views.APIView):
    """
    This is the main Admin Dashboard view. 
    It has been moved from the 'users' app to here for better organization.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        
        # 1. STAT CARD QUERIES
        # We read the pre-calculated gross sales from all vendors
        vendor_stats = CustomUser.objects.filter(role='VENDOR').aggregate(
            total_sales_sum=Coalesce(Sum('total_sales'), Decimal('0.0'))
        )
        
        total_sales = vendor_stats.get('total_sales_sum')
        total_commission = total_sales * Decimal('0.10') # 10%
        
        new_orders_count = Order.objects.filter(status='Paid').count()
        pending_vendors_count = CustomUser.objects.filter(role='VENDOR', is_approved=False).count()
        total_customers_count = CustomUser.objects.filter(role='CUSTOMER').count()
        total_approved_vendors_count = CustomUser.objects.filter(role='VENDOR', is_approved=True).count()

        stat_cards = {
            "total_sales": total_sales,
            "total_commission": round(total_commission, 2),
            "new_orders": new_orders_count,
            "pending_vendors": pending_vendors_count,
            "total_customers": total_customers_count,
            "total_approved_vendors": total_approved_vendors_count
        }

        # 2. CHART QUERIES
        sales_by_category = OrderItem.objects.filter(order__status__in=['Paid', 'Shipped', 'Delivered']) \
            .values('product__category__name') \
            .annotate(
                name=F('product__category__name'),
                total_sales=Coalesce(Sum(F('quantity') * F('price'), output_field=DecimalField()), Decimal('0.0'))
            ) \
            .filter(total_sales__gt=0) \
            .order_by('-total_sales') \
            .values('name', 'total_sales')

        sales_by_vendor = OrderItem.objects.filter(order__status__in=['Paid', 'Shipped', 'Delivered']) \
            .values('product__vendor__store_name') \
            .annotate(
                store_name=F('product__vendor__store_name'),
                total_earnings=Coalesce(Sum(F('quantity') * F('price'), output_field=DecimalField()), Decimal('0.0'))
            ) \
            .filter(total_earnings__gt=0) \
            .order_by('-total_earnings')[:5] \
            .values('store_name', 'total_earnings')

        fast_moving_products = OrderItem.objects.filter(order__status__in=['Paid', 'Shipped', 'Delivered']) \
            .values('product__name') \
            .annotate(
                name=F('product__name'),
                total_sold=Sum('quantity')
            ) \
            .filter(total_sold__gt=0) \
            .order_by('-total_sold')[:5] \
            .values('name', 'total_sold')
        
        # ... (add other chart queries here if needed) ...

        charts = {
            "sales_by_category": list(sales_by_category),
            "sales_by_vendor": list(sales_by_vendor),
            "fast_moving_products": list(fast_moving_products),
            "top_reviewed_vendors": [] # Placeholder
        }

        data = {
            "stat_cards": stat_cards,
            "charts": charts
        }
        
        return Response(data, status=status.HTTP_200_OK)


from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, permissions
from .models import Product
from .serializers import ProductSerializer
# Import your IsAdminUser permission if it's custom, or use standard:
from rest_framework.permissions import IsAdminUser, IsAuthenticated

# ---------------------------------------------------------
# 1. ADMIN VIEWSET (Updates Status -> Notifies Vendor)
# ---------------------------------------------------------
class AdminProductStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        # ✅ FIX: Add 'is_published' so the frontend can toggle it
        fields = ['status', 'is_published'] 

class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ProductSerializer
    queryset = Product.objects.all().select_related('vendor', 'category')

    def get_serializer_class(self):
        # Use the specific serializer for updates
        if self.action in ['update', 'partial_update']:
            return AdminProductStatusSerializer
        return super().get_serializer_class()

    def perform_update(self, serializer):
        # 1. Capture the previous status before saving
        instance = serializer.instance
        old_status = instance.status

        # 2. Save the new data (Updates 'status' AND 'is_published')
        updated_product = serializer.save()
        new_status = updated_product.status

        # 3. Check if STATUS changed (e.g., Pending -> Approved)
        # We do this check so we don't send an email if we just toggled "is_published"
        if old_status != new_status:
            self.send_status_email(updated_product, new_status)

    def send_status_email(self, product, new_status):
        # ... (Your existing email logic remains exactly the same) ...
        print(f"Attempting to send email for {product.name}...") 
        try:
            if not product.vendor or not product.vendor.email:
                print("❌ No vendor email found. Skipping.")
                return

            vendor_email = product.vendor.email
            subject = f"Product Status Update: {product.name}"
            message = f"The status of your product '{product.name}' has changed to: {new_status}."
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [vendor_email],
                fail_silently=False 
            )
            print(f"✅ Email sent to {vendor_email}")
        except Exception as e:
            print(f"❌ EMAIL FAILED (But status updated): {e}")

# ---------------------------------------------------------
# 2. VENDOR VIEWSET (Adds Product -> Notifies Admin)
# ---------------------------------------------------------
# Since you didn't have this, add it to the same file
class VendorProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated] # Only logged in vendors
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Vendors only see their own products
        return Product.objects.filter(vendor=self.request.user)

    def perform_create(self, serializer):
        # 1. Save product, assign logged-in user as vendor, set status to Pending
        product = serializer.save(vendor=self.request.user, status='PENDING')
        
        # 2. Send Email to Admin
        self.send_admin_notification(product)

    def send_admin_notification(self, product):
        """Helper function to send email to admin"""
        try:
            # You can set a specific admin email in settings.py or hardcode here
            admin_email = getattr(settings, 'ADMIN_SUPPORT_EMAIL', settings.EMAIL_HOST_USER)
            
            subject = f"🚀 New Vendor Product: {product.name}"
            message = (
                f"A new product has been added by {self.request.user.username}.\n\n"
                f"Product: {product.name}\n"
                f"Price: {product.price}\n\n"
                f"Please review it in the Admin Dashboard."
            )

            print(f"📧 Sending email to Admin: {admin_email}") # Console log
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=True
            )
        except Exception as e:
            print(f"❌ Error sending email to admin: {e}")
    

class AdminOrdersView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminOrderSerializer # You need to create this serializer
    queryset = Order.objects.all().prefetch_related('items', 'items__product').order_by('-created_at')

# ------------------
# 7. VENDOR-ONLY ANALYTICS VIEW
# ------------------
class VendorAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]
    
    def get(self, request, format=None):
        vendor_user = request.user
        today = timezone.now().date()
        one_month_ago = today - timedelta(days=30)
        one_year_ago = today - timedelta(days=365)

        # Sales by Category
        category_sales = (
            OrderItem.objects.filter(vendor=vendor_user, order__status__in=['Paid', 'Shipped', 'Delivered'])
            .values('product__category__name').annotate(
                total_revenue=Sum(F('price') * F('quantity'), output_field=DecimalField())
            )
            .order_by('-total_revenue')
            .exclude(product__category__name__isnull=True)
        )
        
        # Product Performance
        product_performance = (
            OrderItem.objects.filter(vendor=vendor_user, order__status__in=['Paid', 'Shipped', 'Delivered'])
            .values('product__id', 'product__name')
            .annotate(
                units_sold=Sum('quantity'),
                revenue=Sum(F('price') * F('quantity'), output_field=DecimalField())
            )
            .order_by('-units_sold')
            [:5]
        )
        
        # Daily sales for the past 30 days
        daily_sales = (
            OrderItem.objects.filter(
                product__vendor=vendor_user,
                order__status__in=['Paid', 'Shipped', 'Delivered'],
                order__created_at__gte=one_month_ago
            )
            .annotate(date=TruncDate('order__created_at'))
            .values('date')
            .annotate(total_sales=Sum(F('price') * F('quantity'), output_field=DecimalField()))
            .order_by('date')
        )
        
        # Monthly sales for the past 12 months
        monthly_sales = (
            OrderItem.objects.filter(
                product__vendor=vendor_user,
                order__status__in=['Paid', 'Shipped', 'Delivered'],
                order__created_at__gte=one_year_ago
            )
            .annotate(month=TruncMonth('order__created_at'))
            .values('month')
            .annotate(total_sales=Sum(F('price') * F('quantity'), output_field=DecimalField()))
            .order_by('month')
        )
        
        return Response({
            "category_sales": list(category_sales),
            "product_performance": list(product_performance),
            "sales_daily": list(daily_sales),
            "sales_monthly": list(monthly_sales),
        }, status=status.HTTP_200_OK)


# ------------------
# 8. VENDOR-ONLY DASHBOARD VIEW
# ------------------
class VendorfrontDashboardView(APIView):
    """
    Provides aggregated data for the main Vendor Dashboard (MyPage.jsx).
    Reads pre-calculated financial data from the user model.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request, *args, **kwargs):
        vendor = request.user 
        
        total_orders = Order.objects.filter(
            items__product__vendor=vendor
        ).distinct().count()
        
        active_products = Product.objects.filter(
            vendor=vendor, 
            status='APPROVED',
            is_published=True
        ).count()

        data = {
            "lifetime_net_earnings": vendor.lifetime_net_earnings or Decimal('0.00'),
            "available_for_payout": vendor.available_for_payout or Decimal('0.00'),
            "total_orders": total_orders,
            "active_products": active_products,
        }
        return Response(data, status=status.HTTP_200_OK)

# ------------------
# 9. ADMIN DATA EXPORT VIEW
# ------------------
class AdminFullDataExportView(views.APIView):
    """
    A dedicated view for exporting all website data as an Excel file.
    This is a heavy operation and should be admin-only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            # 1. Get Customers Data
            customers = CustomUser.objects.filter(role='CUSTOMER').values(
                'id', 'username', 'email', 'first_name', 'last_name', 'date_joined'
            )
            df_customers = pd.DataFrame(list(customers))
            if not df_customers.empty:
                df_customers['date_joined'] = df_customers['date_joined'].dt.tz_convert(None) # Naive datetime

            # 2. Get Vendors Data
            vendors = CustomUser.objects.filter(role='VENDOR').values(
                'id', 'username', 'email', 'store_name', 'is_approved', 'date_joined'
            )
            df_vendors = pd.DataFrame(list(vendors))
            if not df_vendors.empty:
                df_vendors['date_joined'] = df_vendors['date_joined'].dt.tz_convert(None) # Naive datetime

            # 3. Get Products Data
            products = Product.objects.all().annotate(
                category_name=F('category__name'),
                vendor_name=F('vendor__store_name')
            ).values(
                'id', 'name', 'category_name', 'vendor_name', 'price', 'stock'
            )
            df_products = pd.DataFrame(list(products))

            # 4. Get All Order Items
            order_items = OrderItem.objects.all().select_related(
                'order', 'order__user', 'product', 'product__vendor'
            ).annotate(
                customer_username=F('order__user__username'),
                customer_email=F('order__user__email'),
                order_date=F('order__created_at'),
                order_status=F('order__status'),
                product_name=F('product__name'),
                vendor_name=F('product__vendor__store_name'), 
            ).values(
                'order__id', 'order_date', 'order_status',
                'customer_username', 'customer_email',
                'product_name', 'vendor_name', 'quantity', 'price'
            ).order_by('-order_date')
            
            df_order_details = pd.DataFrame(list(order_items))
            if not df_order_details.empty:
                df_order_details['order_date'] = df_order_details['order_date'].dt.tz_convert(None) # Naive datetime

            # Rename columns
            df_order_details = df_order_details.rename(columns={
                'order__id': 'Order ID', 'order_date': 'Order Date', 'order_status': 'Order Status',
                'customer_username': 'Customer', 'customer_email': 'Customer Email',
                'product_name': 'Product', 'vendor_name': 'Vendor Name', 
                'quantity': 'Quantity', 'price': 'Price per Unit'
            })

            # 5. Create Excel file in memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_order_details.to_excel(writer, sheet_name='All Order Details', index=False)
                df_customers.to_excel(writer, sheet_name='Customers', index=False)
                df_vendors.to_excel(writer, sheet_name='Vendors', index=False)
                df_products.to_excel(writer, sheet_name='Products', index=False)
            
            output.seek(0) # Rewind the buffer

            # 6. Create the HttpResponse
            response = HttpResponse(
                output,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="full_website_export.xlsx"'
            
            return response

        except Exception as e:
            logger.error(f"Error generating export: {e}", exc_info=True)
            return Response({"error": f"Failed to generate export: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

