from django.urls import path
# ⭐️ FIX: Import all the views you are using
from users.views import (
    SaveAddressView, 
    ApproveVendorView,
    AdminAllVendorsView,
    AdminExportVendorsExcelView,
    AdminfrontDashboardView,
)

urlpatterns = [
    path('save_address/', SaveAddressView.as_view(), name='save-address'),
    path('admin/vendors/approve/<int:pk>/', ApproveVendorView.as_view(), name='admin-approve-vendor'),
    
    # ⭐️ FIX: Remove the "views." prefix
    path('admin/vendors/all/', AdminAllVendorsView.as_view(), name='admin-all-vendors-list'),
    path('admin/vendors/export/excel/', AdminExportVendorsExcelView.as_view(), name='admin-export-excel'),
    path('dashboard/', AdminfrontDashboardView.as_view(), name='admin-dashboard'), # NEW
]