# product_app/urls.py
from django.urls import path, include
from rest_framework_nested.routers import DefaultRouter
from rest_framework_nested import routers

# --- 1. IMPORT ALL THE VIEWS YOU NEED ---
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ReviewViewSet,
    CartAddItemView,
    CartDetailView,
    CartUpdateItemView,
    CartRemoveItemView,
    VendorStorefrontView,
    VendorStorefrontSettingsView,
    VendorStorefrontReviewsView,
    AdminDashboardStatsView,   # The Admin dashboard
    AdminProductViewSet,       # Admin product management
    AdminOrdersView,           # Admin order list
    VendorAnalyticsView,       # Vendor charts page
    VendorfrontDashboardView,  # ⭐️ The Vendor dashboard
)
# (Note: Admin vendor management views are in the 'users' app)


# ------------------ 1. Main Router ------------------
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')

# ------------------ 2. Admin Router ------------------
# This router is for admin-only product management
router.register(r'admin/all-products', AdminProductViewSet, basename='admin-products')

# ------------------ 3. Nested Router for Product Reviews ------------------
products_router = routers.NestedSimpleRouter(router, r'products', lookup='product_pk')
products_router.register(
    r'reviews',
    ReviewViewSet,
    basename='product-reviews'
)

# ------------------ 4. URL Patterns ------------------
urlpatterns = [
    # --- Router Includes (Category, Product, Reviews, Admin-Products) ---
    path('', include(router.urls)),
    path('', include(products_router.urls)),
    

    # --- Vendor & Dashboard Routes ---
    
    # ⭐️ THIS IS THE CORRECT VENDOR DASHBOARD URL (for MyPage.jsx)
    path('vendor/dashboard/', VendorfrontDashboardView.as_view(), name='vendor-dashboard'),
    
    # This is for the "Analysis" button
    path('vendor/analytics/', VendorAnalyticsView.as_view(), name='vendor-analytics'),


    # --- Cart Operations ---
    path('cart/add_item/', CartAddItemView.as_view(), name='cart-add-item'),
    path('cart/detail/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/update_item/', CartUpdateItemView.as_view(), name='cart-update-item'),
    path('cart/remove_item/<int:product_id>/', CartRemoveItemView.as_view(), name='cart-remove-item'),


    # --- Vendor Storefront Routes (Public) ---
    path('vendor/<int:vendor_pk>/products/', VendorStorefrontView.as_view(), name='vendor-products'),
    path('vendor/<int:vendor_pk>/settings/', VendorStorefrontSettingsView.as_view(), name='vendor-settings'),
    path('vendor/<int:vendor_pk>/reviews/', VendorStorefrontReviewsView.as_view(), name='vendor-reviews'),

    
    # --- Admin Dashboard Routes ---
    
    # ⭐️ THIS IS THE CORRECT ADMIN DASHBOARD URL (for MyPage.jsx)
    path('admin/dashboard/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
    
    # This URL is in your 'order' app, not here
    # path('orders/admin/all/', AdminOrdersView.as_view(), name='admin-all-orders'), 
    
    # These URLs should be in your 'users' app
    # path('admin/vendors/', AdminVendorsView.as_view(), name='admin-vendors-list'),
    # path('admin/vendors/approve/<int:vendor_id>/', AdminApproveVendorView.as_view(), name='admin-approve-vendor'),
]