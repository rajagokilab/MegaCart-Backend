# order/urls.py
from django.urls import path
from .views import CreateRazorpayOrder, PaymentVerificationView, OrderListView,OrderStatusUpdateView
# order/urls.py
from django.urls import path
from .views import (
    CreateRazorpayOrder, 
    PaymentVerificationView, 
    OrderListView,
    VendorOrderListView ,
     OrderStatusUpdateView # 👈 Import the new view
)

urlpatterns = [
    path('orders/create/', CreateRazorpayOrder.as_view(), name='razorpay-order-create'),
    path('orders/verify/', PaymentVerificationView.as_view(), name='razorpay-verify'),
    path('orders/my-orders/', OrderListView.as_view(), name='my-orders-list'),
    path('orders/vendor/', VendorOrderListView.as_view(), name='vendor-orders'),
    # 🔴 LIKELY CAUSE OF 404
path('orders/update_status/<int:order_id>/', OrderStatusUpdateView.as_view(), name='order-update-status'),
]