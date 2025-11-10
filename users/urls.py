from django.urls import path
from users.views import SaveAddressView, ApproveVendorView  

urlpatterns = [
    path('save_address/', SaveAddressView.as_view(), name='save-address'),
    path('admin/vendors/approve/<int:pk>/', ApproveVendorView.as_view(), name='admin-approve-vendor'),
]
