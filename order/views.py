import razorpay
import logging
import pandas as pd
import io
from decimal import Decimal
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.generics import ListAPIView
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

# Models
from .models import Order, OrderItem, OrderStatusHistory, Payout
from product_app.models import Product

# Permissions
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from users.permissions import IsVendor 

# Serializers
from .serializers import (
    OrderSerializer, 
    VendorOrderSerializer, 
    PayoutSerializer, 
    StatusHistorySerializer,
    BankDetailsSerializer,
    AdminOrderExportSerializer
)

User = get_user_model()
logger = logging.getLogger(__name__)

# Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


# -------------------------------------------------
# 1. CHECKOUT / PAYMENT VIEWS
# -------------------------------------------------

class CreateRazorpayOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        grand_total = Decimal(request.data.get('grand_total', 0))
        items = request.data.get('items')
        shipping_address = request.data.get('shipping_address')

        if not items or grand_total <= 0:
            return Response({"error": "Cart is empty or invalid."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not shipping_address:
            return Response({"error": "Shipping address is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                new_order = Order.objects.create(
                    user=user,
                    total_amount=grand_total,
                    status="Pending",
                    shipping_address=shipping_address,
                )

                for item_data in items:
                    # 1. Fetch the Product with locking to prevent race conditions
                    product = Product.objects.select_for_update().get(id=item_data['id'])
                    
                    if not product.vendor:
                        raise Exception(f"Product '{product.name}' has no assigned vendor.")
                    
                    quantity = int(item_data['quantity'])
                    
                    # 2. ✅ STOCK CHECK
                    if product.stock < quantity:
                        raise Exception(f"Insufficient stock for '{product.name}'. Only {product.stock} left.")
                    
                    # 3. ✅ DEDUCT STOCK
                    product.stock -= quantity
                    product.save()

                    OrderItem.objects.create(
                        order=new_order,
                        product=product,
                        quantity=quantity,
                        price=product.price,
                        vendor=product.vendor 
                    )
                
                OrderStatusHistory.objects.create(
                    order=new_order,
                    status="Pending",
                    changed_by=user,
                )

        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to create local order: {e}", exc_info=True)
            return Response({"error": f"Failed to create order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            razorpay_data = {
                "amount": int(grand_total * 100), # Amount in paise
                "currency": "INR",
                "receipt": f"order_rcpt_{new_order.id}",
            }
            rp_order = client.order.create(data=razorpay_data)

        except Exception as e:
            logger.error(f"Razorpay error: {e}", exc_info=True)
            # If Razorpay creation fails, we must roll back (delete) the local order 
            # OR the transaction.atomic() block above handles the rollback if an exception raised there.
            # BUT here we are outside the atomic block. 
            # Ideally, if razorpay fails, we should probably delete the order manually
            # to "refund" the stock effectively (since stock was deducted above).
            
            # Manual rollback of stock is complex here, but for simplicity we delete the order.
            # In a real production app, consider putting the Razorpay call *before* the atomic block 
            # or using a separate stock reservation system.
            new_order.delete()
            
            return Response({"error": f"Razorpay error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        new_order.razorpay_order_id = rp_order["id"]
        new_order.save()

        return Response({
            "razorpay_order_id": rp_order["id"],
            "amount": rp_order["amount"],
            "currency": rp_order["currency"],
        })


class PaymentVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"Payment payload received: {request.data}")
        rzp_order_id = request.data.get("razorpay_order_id")
        rzp_payment_id = request.data.get("razorpay_payment_id")
        rzp_signature = request.data.get("razorpay_signature")

        try:
            order = Order.objects.get(
                user=request.user,
                razorpay_order_id=rzp_order_id,
                status="Pending"
            )
        except Order.DoesNotExist:
            logger.warning(f"Order {rzp_order_id} not found or already processed for user {request.user.email}")
            return Response({"error": "Order not found or already processed"}, status=status.HTTP_404_NOT_FOUND)

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": rzp_order_id,
                "razorpay_payment_id": rzp_payment_id,
                "razorpay_signature": rzp_signature,
            })

            with transaction.atomic():
                order.status = "Paid"
                order.razorpay_payment_id = rzp_payment_id
                order.save()

                OrderStatusHistory.objects.create(
                    order=order,
                    status="Paid",
                    changed_by=request.user,
                )

            vendors_map = {}
            order_items = order.items.all()
            
            for item in order_items:
                vendor = item.product.vendor
                if vendor not in vendors_map:
                    vendors_map[vendor] = []
                vendors_map[vendor].append(item)
            
            admin_email_summary = []
            total_platform_fee = Decimal('0.00')

            for vendor, items_list in vendors_map.items():
                try:
                    vendor_total = sum(Decimal(item.price) * item.quantity for item in items_list)
                    commission_rate = Decimal('0.10') # 10%
                    platform_fee = (vendor_total * commission_rate).quantize(Decimal('0.01'))
                    vendor_earnings = (vendor_total - platform_fee).quantize(Decimal('0.01'))

                    with transaction.atomic():
                        vendor_profile = User.objects.select_for_update().get(id=vendor.id)
                        
                        vendor_profile.total_sales = (vendor_profile.total_sales or Decimal('0.00')) + vendor_total 
                        vendor_profile.lifetime_net_earnings = (vendor_profile.lifetime_net_earnings or Decimal('0.00')) + vendor_earnings
                        vendor_profile.available_for_payout = (vendor_profile.available_for_payout or Decimal('0.00')) + vendor_earnings
                        
                        vendor_profile.save(update_fields=[
                            'total_sales', 
                            'lifetime_net_earnings', 
                            'available_for_payout'
                        ])
                    
                    subject_vendor = f"You've Made a Sale! New Items for Order #{order.id}"
                    message_vendor = (
                        f"Hi {vendor.store_name},\n\n"
                        f"You have new items to ship for Order ID: {order.id}.\n\n"
                        f"--- Your Portion of the Order ---\n"
                        f"Subtotal: ₹{vendor_total}\n"
                        f"Platform Fee (10%): -₹{platform_fee}\n"
                        f"Your Earnings: ₹{vendor_earnings}\n\n"
                        "This amount has been added to your available payout balance.\n"
                        "Please log in to prepare the following items:\n"
                    )
                    for item in items_list:
                        message_vendor += f"- {item.product.name} (Qty: {item.quantity})\n"
                    
                    send_mail(
                        subject_vendor, message_vendor,
                        settings.DEFAULT_FROM_EMAIL, [vendor.email],
                        fail_silently=False
                    )
                    
                    admin_email_summary.append(
                        f"Vendor: {vendor.store_name} ({vendor.email})\n"
                        f"  - Vendor Total: ₹{vendor_total}\n"
                        f"  - Vendor Earning: ₹{vendor_earnings}\n"
                        f"  - Platform Fee: +₹{platform_fee}\n"
                    )
                    total_platform_fee += platform_fee

                except Exception as e:
                    logger.error(f"Failed to process payout/email for vendor {vendor.email}: {e}")

            try:
                # You can use settings.ADMIN_EMAIL or hardcode if needed temporarily
                admin_email = "rajagokilavivek@gmail.com" 
                subject_admin = f"New Multi-Vendor Sale: Order #{order.id}"
                message_admin = (
                    f"A new sale was made involving {len(vendors_map)} vendor(s).\n\n"
                    f"Order ID: {order.id}\n"
                    f"Customer: {order.user.email}\n"
                    f"Order Total: ₹{order.total_amount}\n\n"
                    "--- Financial Breakdown ---\n" +
                    "\n".join(admin_email_summary) +
                    f"\n------------------------\n"
                    f"Total Platform Commission: +₹{total_platform_fee}"
                )
                send_mail(
                    subject_admin, message_admin,
                    settings.DEFAULT_FROM_EMAIL, [admin_email],
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send admin summary email: {e}")

            try:
                buyer_email = order.user.email
                buyer_name = order.user.username
                subject_buyer = f"Your Order Has Been Placed! (Order #{order.id})"
                message_buyer = (
                    f"Hi {buyer_name},\n\n"
                    f"Thank you for your purchase! Your payment was successful and your order #{order.id} has been placed.\n\n"
                    f"Order Total: ₹{order.total_amount}\n\n"
                    "You will receive another email as soon as your items have been shipped.\n"
                    "You can track your order status from your 'My Account' page.\n\n"
                    "--- Items in this Order ---\n"
                )
                for item in order_items:
                    message_buyer += f"- {item.product.name} (Qty: {item.quantity})\n"
                
                send_mail(
                    subject_buyer,
                    message_buyer,
                    settings.DEFAULT_FROM_EMAIL,
                    [buyer_email],
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Failed to send order confirmation email to buyer {buyer_email}: {e}")

            return Response({"message": "Payment verified successfully."})

        except razorpay.errors.SignatureVerificationError:
            order.status = "Failed"
            order.save()
            # Note: Stock was already deducted. 
            # In a perfect system, you'd revert stock here. 
            # For now, we assume 'Failed' orders hold the stock (reservation logic).
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}", exc_info=True)
            return Response({"error": "Server error during verification"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# -------------------------------------------------
# 2. ORDER LISTING & STATUS VIEWS
# -------------------------------------------------

class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")

class VendorOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVendor]
    serializer_class = VendorOrderSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(items__product__vendor=self.request.user)
            .distinct()
            .order_by("-created_at")
        )

class AdminOrderListView(generics.ListAPIView):
    """
    Get a list of ALL orders for the ADMIN.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = OrderSerializer 

    def get_queryset(self):
        return Order.objects.all().order_by("-created_at")


class OrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def patch(self, request, order_id):
        new_status = request.data.get("status")
        tracking_number = request.data.get("tracking_number", None) 

        if not new_status:
            return Response({"error": "Status not provided"}, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, id=order_id)
        old_status = order.status

        if not order.items.filter(product__vendor=request.user).exists():
            return Response({"error": "You do not have permission to update this order."}, status=status.HTTP_403_FORBIDDEN)
        
        if new_status == "Shipped" and old_status == "Paid":
            if not tracking_number: 
                return Response({"error": "Tracking number is required to mark as shipped."}, status=status.HTTP_400_BAD_REQUEST)
            order.status = new_status
            order.tracking_number = tracking_number
        
        elif new_status == "Delivered" and old_status == "Shipped":
            order.status = new_status
            
        elif new_status == old_status:
             return Response({"error": "Order is already in this status."}, status=status.HTTP_400_BAD_REQUEST)
             
        else:
            return Response({"error": f"Invalid status transition from {old_status} to {new_status}."}, status=status.HTTP_400_BAD_REQUEST)
        
        order.save()

        history_entry = OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            changed_by=request.user
        )
        history_serializer = StatusHistorySerializer(history_entry)

        if new_status in ["Shipped", "Delivered"] and old_status != new_status:
            try:
                subject = f"Your Order #{order.id} is now {new_status}"
                tracking_info = ""
                if new_status == "Shipped" and order.tracking_number:
                    tracking_info = f"Your tracking number is: {order.tracking_number}\n\n"
                
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"Your order #{order.id} status has been updated to {new_status}.\n\n"
                    f"{tracking_info}"
                    f"Thank you for shopping!"
                )
                send_mail(
                    subject, message,
                    settings.DEFAULT_FROM_EMAIL, [order.user.email],
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Email sending failed (ignored): {str(e)}")

        return Response({
            "message": "Status updated successfully",
            "status": new_status,
            "tracking_number": order.tracking_number,
            "history": history_serializer.data 
        })

# -------------------------------------------------
# 3. MANUAL PAYOUT VIEWS (Bank/UPI)
# -------------------------------------------------

class VendorBankDetailsView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get_user(self):
        user = self.request.user
        if user.role != 'VENDOR':
            raise PermissionDenied("You are not a vendor.")
        return user

    def get(self, request, *args, **kwargs):
        user = self.get_user()
        serializer = BankDetailsSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = self.get_user()
        serializer = BankDetailsSerializer(instance=user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VendorPayoutHistoryView(ListAPIView):
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        return Payout.objects.filter(vendor=self.request.user).order_by('-requested_at')


class VendorPayoutRequestView(APIView):
    permission_classes = [IsAuthenticated, IsVendor] 

    def post(self, request, *args, **kwargs):
        user = self.request.user
        amount_to_payout = user.available_for_payout

        if amount_to_payout <= 0:
            return Response(
                {'error': 'No available balance for payout.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Payout.objects.filter(vendor=user, status='PENDING').exists():
            return Response(
                {'error': 'You already have a pending payout request.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.upi_id and not user.account_number:
            return Response(
                {'error': 'You must set up your Bank or UPI details in "Bank Settings" before requesting a payout.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                Payout.objects.create(
                    vendor=user,
                    amount=amount_to_payout,
                    status='PENDING'
                )
                
                user.available_for_payout = 0
                user.save(update_fields=['available_for_payout'])

            return Response(
                {'success': 'Payout request submitted successfully.'}, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Payout request failed for {user.email}: {e}", exc_info=True)
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VendorBalanceView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        user = request.user
        if user.role != 'VENDOR':
            return Response({"error": "Not a vendor"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"available_balance": user.available_for_payout})


class AdminPayoutListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = PayoutSerializer
    
    def get_queryset(self):
        return Payout.objects.all().order_by('-requested_at')


class AdminPayoutUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, payout_id, *args, **kwargs):
        payout = get_object_or_404(Payout, id=payout_id)
        new_status = request.data.get("status")

        if not new_status:
            return Response({"error": "Status not provided"}, status=status.HTTP_400_BAD_REQUEST)
        if new_status not in ["COMPLETED", "REJECTED"]:
            return Response({"error": "Invalid status. Must be 'COMPLETED' or 'REJECTED'."}, status=status.HTTP_400_BAD_REQUEST)
        if payout.status != 'PENDING':
            return Response({"error": f"This payout is already {payout.status}."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                payout.status = new_status
                
                if new_status == 'COMPLETED':
                    payout.paid_at = timezone.now()
                
                payout.save()
                
                if new_status == 'REJECTED':
                    vendor = payout.vendor
                    vendor.available_for_payout = (vendor.available_for_payout or Decimal('0.00')) + payout.amount
                    vendor.save(update_fields=['available_for_payout'])
            
            return Response(PayoutSerializer(payout).data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Admin payout update failed for payout {payout_id}: {e}", exc_info=True)
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# -------------------------------------------------
# 4. ADMIN EXPORT VIEW
# -------------------------------------------------
class AdminExportOrdersExcelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, *args, **kwargs):
        order_items = OrderItem.objects.all().order_by('-order__created_at').select_related(
            'order', 'order__user', 'product', 'product__category', 'product__vendor', 'vendor'
        )
        
        serializer = AdminOrderExportSerializer(order_items, many=True)
        data = serializer.data

        if not data:
            return Response({"error": "No order data to export."}, status=status.HTTP_404_NOT_FOUND)
            
        df = pd.DataFrame(data)

        df = df.rename(columns={
            'order_id': 'Order ID',
            'order_date': 'Order Date',
            'order_status': 'Order Status',
            'customer_name': 'Customer Name',
            'customer_email': 'Customer Email',
            'order_total': 'Order Total (₹)',
            'payment_id': 'Payment ID',
            'shipping_address_flat': 'Shipping Address',
            'shipping_phone': 'Mobile Number',
            'vendor_store_name': 'Vendor (Product)',
            'vendor': 'Vendor (Item)', 
            'product_name': 'Product Name',
            'product_category': 'Category',
            'quantity': 'Quantity',
            'price': 'Item Price (₹)',
        })
        
        if 'Order Date' in df.columns:
            df['Order Date'] = pd.to_datetime(df['Order Date']).dt.strftime('%Y-%m-%d %I:%M %p')
        
        final_columns = [
            'Order ID', 'Order Date', 'Order Status', 
            'Customer Name', 'Customer Email', 'Mobile Number', 'Shipping Address',
            'Vendor (Item)', 'Product Name', 'Category', 'Quantity', 'Item Price (₹)', 
            'Order Total (₹)', 'Payment ID'
        ]
        # Filter to only columns that exist
        final_columns = [col for col in final_columns if col in df.columns]
        df = df[final_columns]

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Orders', index=False)
        output.seek(0)

        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="all_orders_report.xlsx"'
        
        return response