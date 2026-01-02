import pandas as pd
import io
import threading
from decimal import Decimal
from datetime import timedelta

# Django Imports
from django.http import HttpResponse
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

# DRF Imports
from rest_framework import generics, views, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser

# Local Imports
from .models import CustomUser
from order.models import Order 
from .serializers import (
    RegisterSerializer, 
    CustomUserSerializer, 
    AdminVendorSerializer,
    AdminVendorListSerializer,
    VendorKYCSerializer
)

User = get_user_model()

# ---------------------------------------------------------
# 📧 HELPER: Send Email Asynchronously (Prevents Lag)
# ---------------------------------------------------------
def send_email_thread(subject, message, recipient_list):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=True
        )
        print(f"✅ Email sent to {recipient_list}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")


# ---------------------------------------------------------
# 👤 AUTHENTICATION & USER MANAGEMENT
# ---------------------------------------------------------

class RegisterUserView(generics.CreateAPIView):
    """
    Handles registration of new users (Customer or Vendor).
    - If Vendor registers -> Notifies Admin via Email.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # --- 📧 NOTIFY ADMIN IF VENDOR REGISTERS ---
            if user.role == 'VENDOR':
                subject = f"New Vendor Application: {user.store_name}"
                message = (
                    f"A new vendor has registered on Vetricart.\n\n"
                    f"Store Name: {user.store_name}\n"
                    f"Email: {user.email}\n"
                    f"Business ID: {user.business_reg_id}\n\n"
                    f"Please login to the Admin Panel to review their KYC documents."
                )
                
                # Send to Admin (Async)
                threading.Thread(
                    target=send_email_thread, 
                    args=(subject, message, ['rajagokilavivek@gmail.com']) # 👈 Admin Email
                ).start()
            # -------------------------------------------

            data = CustomUserSerializer(user).data
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(generics.RetrieveAPIView):
    """
    Returns the currently authenticated user's info.
    """
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class SaveAddressView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        if not isinstance(data, dict):
            return Response({"error": "Invalid data format."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user.shipping_address = data
            user.save(update_fields=['shipping_address'])
            return Response({"message": "Address saved successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_all_customers(request):
    """
    Returns a list of all users who are strictly CUSTOMERS.
    """
    customers = User.objects.filter(role='CUSTOMER')
    serializer = CustomUserSerializer(customers, many=True)
    return Response(serializer.data)


# ---------------------------------------------------------
# 🏢 VENDOR MANAGEMENT (ADMIN SIDE)
# ---------------------------------------------------------

# backend/users/views.py

class ApproveVendorView(views.APIView):
    """
    Updates Vendor Status.
    - APPROVE: is_approved=True, vendor_status='APPROVED'
    - PENDING: is_approved=False, vendor_status='PENDING'
    - REJECT: is_approved=False, vendor_status='REJECTED' (Does NOT delete user)
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        try:
            vendor = User.objects.get(pk=pk, role='VENDOR')
        except User.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # "APPROVE", "REJECT", "PENDING"
        subject = ""
        message = ""
        email_needed = False

        # 1. HANDLE APPROVE
        if action == 'APPROVE':
            vendor.is_approved = True
            vendor.vendor_status = 'APPROVED' # ✅ Updates status
            vendor.save()
            
            subject = "🎉 Account Approved: Welcome to Vetricart!"
            message = (
                f"Hello {vendor.store_name},\n\n"
                f"Congratulations! Your vendor account has been APPROVED.\n"
                f"You can now log in to your dashboard.\n\n"
                f"Best Regards,\nVetriCart Team"
            )
            email_needed = True

        # 2. HANDLE REJECT (NO DELETE)
        elif action == 'REJECT':
            # ❌ REMOVED: vendor.delete() <-- This was causing your error
            
            vendor.is_approved = False
            vendor.vendor_status = 'REJECTED' # ✅ Updates status to Rejected instead
            vendor.save()
            
            subject = "⚠️ Account Status: Application Rejected"
            message = (
                f"Hello {vendor.store_name},\n\n"
                f"We regret to inform you that your vendor application has been rejected.\n"
                f"This may be due to incomplete KYC documents.\n\n"
                f"Best Regards,\nVetriCart Team"
            )
            email_needed = True

        # 3. HANDLE PENDING
        elif action == 'PENDING':
            vendor.is_approved = False
            vendor.vendor_status = 'PENDING' # ✅ Updates status
            vendor.save()

            subject = "⏳ Account Status: Under Review"
            message = (
                f"Hello {vendor.store_name},\n\n"
                f"Your account status has been set to 'Pending Review'.\n\n"
                f"Best Regards,\nVetriCart Team"
            )
            email_needed = True
        
        else:
            return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

        # 🚀 Send Email
        if email_needed and vendor.email:
            threading.Thread(
                target=send_email_thread, 
                args=(subject, message, [vendor.email])
            ).start()

        return Response(AdminVendorSerializer(vendor).data, status=status.HTTP_200_OK)
    
    
class AdminAllVendorsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminVendorListSerializer
    
    def get_queryset(self):
        return User.objects.filter(role='VENDOR').order_by('-date_joined')


class AdminExportVendorsExcelView(views.APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        vendors = User.objects.filter(role='VENDOR')
        serializer = AdminVendorListSerializer(vendors, many=True)
        data = serializer.data

        df = pd.DataFrame(data)
        df = df.rename(columns={
            'id': 'Vendor ID',
            'store_name': 'Store Name',
            'email': 'Email',
            'is_approved': 'Approved Status',
            'date_joined': 'Date Joined',
            'total_sales': 'Total Gross Sales (₹)',
            'available_for_payout': 'Available for Payout (₹)', 
            'total_orders': 'Total Orders',
            'total_products': 'Total Products',
            'active_products': 'Active Products', 
            'account_holder_name': 'Bank Account Holder',
            'account_number': 'Bank Account Number',
            'ifsc_code': 'Bank IFSC Code',
            'upi_id': 'UPI ID'
        })
        
        if 'Date Joined' in df.columns:
            df['Date Joined'] = pd.to_datetime(df['Date Joined']).dt.strftime('%Y-%m-%d')
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Vendors', index=False)
        output.seek(0)

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="vendor_report.xlsx"'
        return response


# ---------------------------------------------------------
# 📊 DASHBOARD & ANALYTICS
# ---------------------------------------------------------

class AdminfrontDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        vendor_stats = User.objects.filter(role='VENDOR').aggregate(
            total_sales_sum=Sum('total_sales')
        )
        total_sales = vendor_stats.get('total_sales_sum') or Decimal('0.00')
        
        COMMISSION_RATE = Decimal('0.10') 
        total_commission = total_sales * COMMISSION_RATE
        
        new_orders = Order.objects.filter(status='Paid').count()
        pending_vendors = User.objects.filter(role='VENDOR', is_approved=False).count()

        data = {
            "total_sales": total_sales,
            "total_commission": total_commission,
            "new_orders": new_orders,
            "pending_vendors": pending_vendors,
        }
        return Response(data, status=status.HTTP_200_OK)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        range_param = request.GET.get('range', '1M') 
        today = timezone.now().date()
        
        if range_param == '1W':
            start_date = today - timedelta(days=7)
        elif range_param == '1Y':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)

        orders_data = (
            Order.objects.filter(
                created_at__date__gte=start_date, 
                payment_status='PAID' 
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total_sales=Sum('total_amount'),
                total_commission=Sum('total_amount') * Decimal('0.10') 
            )
            .order_by('date')
        )

        chart_data = []
        current_date = start_date
        data_dict = {item['date']: item for item in orders_data}

        while current_date <= today:
            day_stats = data_dict.get(current_date, {
                'total_sales': 0, 
                'total_commission': 0
            })
            chart_data.append({
                'date': current_date.strftime("%b %d"), 
                'total_sales': float(day_stats['total_sales'] or 0),
                'total_commission': float(day_stats['total_commission'] or 0)
            })
            current_date += timedelta(days=1)

        return Response({
            'stat_cards': {
                'total_sales': sum(d['total_sales'] for d in chart_data),
                'total_commission': sum(d['total_commission'] for d in chart_data),
            },
            'charts': {
                'sales_over_time': chart_data,
            }
        })


# ---------------------------------------------------------
# 📝 VENDOR ACTIONS (KYC UPLOAD)
# ---------------------------------------------------------

class VendorKYCUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        if user.role != 'VENDOR':
            return Response({"error": "Only vendors can upload KYC documents."}, status=status.HTTP_403_FORBIDDEN)

        serializer = VendorKYCSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "KYC Document uploaded successfully. Admin will review it."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)