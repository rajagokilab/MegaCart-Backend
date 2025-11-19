# order/urls.py
from django.urls import path
from .views import (
    CreateRazorpayOrder, 
    PaymentVerificationView, 
    OrderListView,
    VendorOrderListView ,
    OrderStatusUpdateView,
    VendorPayoutHistoryView,
    VendorPayoutRequestView,
    AdminPayoutListView,
    VendorBalanceView,
    AdminPayoutUpdateView,
    VendorBankDetailsView,
    AdminExportOrdersExcelView,
    AdminOrderListView # ⭐️ 1. IMPORT ADMIN ORDER LIST
)

urlpatterns = [
    path('orders/create/', CreateRazorpayOrder.as_view(), name='razorpay-order-create'),
    path('orders/verify/', PaymentVerificationView.as_view(), name='razorpay-verify'),
    path('orders/my-orders/', OrderListView.as_view(), name='my-orders-list'),
    
    # Vendor
    path('orders/vendor/', VendorOrderListView.as_view(), name='vendor-orders'),
    path('orders/update_status/<int:order_id>/', OrderStatusUpdateView.as_view(), name='order-update-status'),
    path('vendor/payouts/', VendorPayoutHistoryView.as_view(), name='vendor-payout-history'),
    path('vendor/request-payout/', VendorPayoutRequestView.as_view(), name='vendor-payout-request'),
    path('vendor/balance/', VendorBalanceView.as_view(), name='vendor-balance'),
    
    # ⭐️ 2. UNCOMMENTED THIS PATH
    path('vendor/bank-details/', VendorBankDetailsView.as_view(), name='vendor-bank-details'),

    # Admin
    path('orders/admin/all/', AdminOrderListView.as_view(), name='admin-order-list'), # ⭐️ 3. ADDED THIS
    path('admin/payouts/', AdminPayoutListView.as_view(), name='admin-payout-list'),
    path('admin/payouts/update/<int:payout_id>/', AdminPayoutUpdateView.as_view(), name='admin-payout-update'),
    path('admin/orders/export/excel/', AdminExportOrdersExcelView.as_view(), name='admin-export-orders-excel'),
]