from django.urls import path
# ⭐️ FIX: Add get_all_customers to the import list
from users.views import (
    SaveAddressView, 
    ApproveVendorView,
    AdminAllVendorsView,
    AdminExportVendorsExcelView,
    AdminfrontDashboardView,
    get_all_customers,  # <--- Added this
)

urlpatterns = [
    path('save_address/', SaveAddressView.as_view(), name='save-address'),
    path('admin/vendors/approve/<int:pk>/', ApproveVendorView.as_view(), name='admin-approve-vendor'),
    
    path('admin/vendors/all/', AdminAllVendorsView.as_view(), name='admin-all-vendors-list'),
    path('admin/vendors/export/excel/', AdminExportVendorsExcelView.as_view(), name='admin-export-excel'),
    path('dashboard/', AdminfrontDashboardView.as_view(), name='admin-dashboard'),
    
    # ⭐️ FIX: Use the function directly (removed 'views.')
    path('admin/customers/all/', get_all_customers, name='admin-all-customers'),
]