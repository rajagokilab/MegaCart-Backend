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
    AdminDashboardStatsView,
    AdminProductViewSet,
    AdminOrdersView,
    VendorAnalyticsView,
    VendorfrontDashboardView,
    
    # ✅ IMPORT THE NEW VIEWSET HERE
    VendorProductViewSet, 
)

# ------------------ 1. Main Router ------------------
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')

# Public Product List (For Customers)
router.register(r'products', ProductViewSet, basename='product')

# ------------------ 2. Vendor Management Router (NEW) ------------------
# ✅ REGISTER THE VENDOR VIEWSET
# Vendors will POST to /api/vendor/my-products/ to create items (triggers email)
router.register(r'vendor/my-products', VendorProductViewSet, basename='vendor-my-products')

# ------------------ 3. Admin Router ------------------
# Admin Product Management (For Admin)
router.register(r'admin/all-products', AdminProductViewSet, basename='admin-products')

# ------------------ 4. Nested Router for Product Reviews ------------------
products_router = routers.NestedSimpleRouter(router, r'products', lookup='product_pk')
products_router.register(
    r'reviews',
    ReviewViewSet,
    basename='product-reviews'
)

# ------------------ 5. URL Patterns ------------------
urlpatterns = [
    # --- Router Includes ---
    path('', include(router.urls)),
    path('', include(products_router.urls)),

    # --- Vendor & Dashboard Routes ---
    path('vendor/dashboard/', VendorfrontDashboardView.as_view(), name='vendor-dashboard'),
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
    path('admin/dashboard/', AdminDashboardStatsView.as_view(), name='admin-dashboard-stats'),
]