# support/urls.py
from django.urls import path
from .views import SupportMessageCreateAPIView, SupportMessageListCreateAPIView

urlpatterns = [
    # Endpoint for users to submit a support message
    path('create/', SupportMessageCreateAPIView.as_view(), name='support-create'),

    # Endpoint for admin to view all support messages
    path('admin/list/', SupportMessageListCreateAPIView.as_view(), name='admin-support-messages'),
]
