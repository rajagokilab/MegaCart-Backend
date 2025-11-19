import pandas as pd
import io
import threading # ⭐️ Added missing import
from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Sum
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework import generics, views, permissions, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny

# Import your models
from .models import CustomUser
from order.models import Order 

# Import your serializers
from .serializers import (
    RegisterSerializer, 
    CustomUserSerializer, 
    AdminVendorSerializer,
    AdminVendorListSerializer
)
# ⭐️ (Note: You need to implement the email sending functions)
# from .utils import send_approval_email_async, send_rejection_email_async

User = get_user_model()


class RegisterUserView(generics.CreateAPIView):
    """
    Handles registration of new users (Customer or Vendor)
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            data = CustomUserSerializer(user).data
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(generics.RetrieveAPIView):
    """
    Returns the currently authenticated user's info
    """
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ApproveVendorView(views.APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        try:
            vendor = User.objects.get(pk=pk, role='VENDOR')
        except User.DoesNotExist:
            return Response({"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # "APPROVE" or "REJECT"

        if action == 'APPROVE':
            vendor.is_approved = True
            vendor.save(update_fields=['is_approved'])
            
            # --- 🚀 TRIGGER ASYNCHRONOUS EMAIL ---
            # (Make sure you have an email function to call here)
            # email_thread = threading.Thread(
            #     target=send_approval_email_async,
            #     args=(vendor.email, vendor.store_name)
            # )
            # email_thread.start()
            
            return Response(AdminVendorSerializer(vendor).data, status=status.HTTP_200_OK)
        
        elif action == 'REJECT':
            vendor.is_approved = False
            vendor.save(update_fields=['is_approved'])
            
            # (Optional: send a rejection email here)
            # send_rejection_email_async(vendor.email, vendor.store_name)
            
            return Response(AdminVendorSerializer(vendor).data, status=status.HTTP_200_OK)
        
        return Response({"detail": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

    
class SaveAddressView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data

        if not isinstance(data, dict):
            return Response(
                {"error": "Invalid data format. Must be a JSON object."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user.shipping_address = data
            user.save(update_fields=['shipping_address'])

            return Response(
                {"message": "Address saved successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            print(f"Error saving address for user {user.id}: {e}")
            return Response(
                {"error": "Internal server error while saving address."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminAllVendorsView(generics.ListAPIView):
    """
    Lists ALL vendors (pending and approved) with their stats.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminVendorListSerializer
    
    def get_queryset(self):
        return User.objects.filter(role='VENDOR').order_by('-date_joined')


class AdminExportVendorsExcelView(views.APIView):
    """
    Generates and returns an Excel file of all vendors and their details.
    """
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
            'total_sales': 'Total Gross Sales (₹)', # ⭐️ Renamed
            'available_for_payout': 'Available for Payout (₹)', 
            'total_orders': 'Total Orders',
            'total_products': 'Total Products',
            'active_products': 'Active Products', 
            'account_holder_name': 'Bank Account Holder',
            'account_number': 'Bank Account Number',
            'ifsc_code': 'Bank IFSC Code',
            'upi_id': 'UPI ID'
        })
        
        df['Date Joined'] = pd.to_datetime(df['Date Joined']).dt.strftime('%Y-%m-%d')
        
        column_order = [
            'Vendor ID', 'Store Name', 'Email', 'Approved Status', 'Date Joined',
            'Total Gross Sales (₹)', 'Available for Payout (₹)',
            'Total Orders', 'Total Products', 'Active Products',
            'Bank Account Holder', 'Bank Account Number', 'Bank IFSC Code', 'UPI ID'
        ]
        
        final_columns = [col for col in column_order if col in df.columns]
        df = df[final_columns]

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
    

class AdminfrontDashboardView(APIView):
    """
    Provides aggregated data for the main Admin Dashboard.
    Calculates total sales, total commission, new orders, and pending vendors.
    """
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
    
    from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from datetime import timedelta
from order.models import Order # Import your Order model

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # 1. Determine Date Range
        range_param = request.GET.get('range', '1M') # Default to 1 Month
        today = timezone.now().date()
        
        if range_param == '1W':
            start_date = today - timedelta(days=7)
        elif range_param == '1Y':
            start_date = today - timedelta(days=365)
        else: # 1M
            start_date = today - timedelta(days=30)

        # 2. Query & Aggregate Data
        # Only get PAID orders to ensure revenue is real
        orders_data = (
            Order.objects.filter(
                created_at__date__gte=start_date, 
                payment_status='PAID' 
            )
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total_sales=Sum('total_amount'),
                total_commission=Sum('admin_commission') # Ensure this field exists in your model
            )
            .order_by('date')
        )

        # 3. Format Data & Fill Missing Dates (Crucial for smooth charts)
        chart_data = []
        current_date = start_date
        
        # Convert QuerySet to a dictionary for O(1) lookup
        data_dict = {item['date']: item for item in orders_data}

        while current_date <= today:
            # If we have data for this day, use it. Otherwise, use 0.
            day_stats = data_dict.get(current_date, {
                'total_sales': 0, 
                'total_commission': 0
            })
            
            chart_data.append({
                # Format date as "Oct 21" for the chart label
                'date': current_date.strftime("%b %d"), 
                'total_sales': float(day_stats['total_sales'] or 0),
                'total_commission': float(day_stats['total_commission'] or 0)
            })
            
            current_date += timedelta(days=1)

        # 4. Return Response
        return Response({
            'stat_cards': {
                # ... your other stats ...
                'total_sales': sum(d['total_sales'] for d in chart_data),
                'total_commission': sum(d['total_commission'] for d in chart_data),
            },
            'charts': {
                'sales_over_time': chart_data, # <--- This is what the React chart reads
                # ... other charts ...
            }
        })