from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

# 💰 --- START: CORRECTED IMPORTS ---
# Import all the views you are using by their class name
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ReviewViewSet,
    CartAddItemView,
    CartDetailView,
    CartUpdateItemView,
    CartRemoveItemView,
    SaveAddressView,
    VendorDashboardView,
    # You were missing these three imports:
    VendorStorefrontView,
    VendorStorefrontSettingsView,
    VendorStorefrontReviewsView,
    AdminDashboardStatsView,
    AdminVendorsView,
    AdminApproveVendorView,
    AdminProductViewSet,
    AdminOrdersView
)
# 💰 --- END: CORRECTED IMPORTS ---


# ------------------ 1. Main Router ------------------
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'admin/all-products', AdminProductViewSet, basename='admin-products')

# ------------------ 2. Nested Router for Product Reviews ------------------
products_router = routers.NestedSimpleRouter(router, r'products', lookup='product')
products_router.register(
    r'reviews',
    ReviewViewSet,
    basename='product-reviews'
)

# ------------------ 3. URL Patterns ------------------
urlpatterns = [
    # --- Router Includes (Category, Product, Reviews) ---
    path('', include(router.urls)),
    path('', include(products_router.urls)),

    # --- Vendor & Dashboard Routes ---
    path('vendor/dashboard/', VendorDashboardView.as_view(), name='vendor-dashboard'),

    # --- User Account Management Routes ---
    path('users/save_address/', SaveAddressView.as_view(), name='save-address'),

    # --- Cart Operations ---
    path('cart/add_item/', CartAddItemView.as_view(), name='cart-add-item'),
    path('cart/detail/', CartDetailView.as_view(), name='cart-detail'),
    path('cart/update_item/', CartUpdateItemView.as_view(), name='cart-update-item'),
    path('cart/remove_item/<int:product_id>/', CartRemoveItemView.as_view(), name='cart-remove-item'),

    # --- Vendor Storefront Routes ---
    # Now these lines will work because the views are imported correctly
    path('vendor/<int:vendor_pk>/products/', 
         VendorStorefrontView.as_view(), 
         name='vendor-products'),
    
    path('vendor/<int:vendor_pk>/settings/', 
         VendorStorefrontSettingsView.as_view(), 
         name='vendor-settings'),
    
    path('vendor/<int:vendor_pk>/reviews/', 
         VendorStorefrontReviewsView.as_view(), 
         name='vendor-reviews'),
         path('admin/dashboard/', 
         AdminDashboardStatsView.as_view(), 
         name='admin-dashboard-stats'),
         
    path('admin/vendors/', 
         AdminVendorsView.as_view(), 
         name='admin-vendors-list'),
         
    path('admin/vendors/approve/<int:vendor_id>/', 
         AdminApproveVendorView.as_view(), 
         name='admin-approve-vendor'),
         
    path('orders/admin/all/', 
         AdminOrdersView.as_view(), 
         name='admin-all-orders'),
]