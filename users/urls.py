from django.urls import path
from users.views import (
    RegisterUserView,            # 👈 1. Added this import
    SaveAddressView, 
    ApproveVendorView,
    AdminAllVendorsView,
    AdminExportVendorsExcelView,
    AdminfrontDashboardView,
    get_all_customers,
    VendorKYCUploadView
)

urlpatterns = [
    # 👇 2. Added this path. This fixes the 404 error.
    path('register/', RegisterUserView.as_view(), name='custom-register'),

    path('save_address/', SaveAddressView.as_view(), name='save-address'),
    path('admin/vendors/approve/<int:pk>/', ApproveVendorView.as_view(), name='admin-approve-vendor'),
    
    path('admin/vendors/all/', AdminAllVendorsView.as_view(), name='admin-all-vendors-list'),
    path('admin/vendors/export/excel/', AdminExportVendorsExcelView.as_view(), name='admin-export-excel'),
    path('dashboard/', AdminfrontDashboardView.as_view(), name='admin-dashboard'),
    
    path('admin/customers/all/', get_all_customers, name='admin-all-customers'),
    path('vendor/kyc/upload/', VendorKYCUploadView.as_view(), name='vendor-kyc-upload'),
]