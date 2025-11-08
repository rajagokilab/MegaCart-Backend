# users/urls.py
from django.urls import path
from product_app.views import SaveAddressView # Your address saving view

urlpatterns = [
    # 1. Custom Address Saving Endpoint (Used by CheckoutPage.jsx)
    # Full URL: /api/users/save_address/
    path('save_address/', SaveAddressView.as_view(), name='save-address'),
    
    # 2. Vendor Storefront Customization Endpoint (V-3)
    # Full URL: /api/users/storefront_settings/<vendor_id>/
    # Note: We use <int:vendor_id> here to retrieve the settings for a specific vendor ID.
    
]