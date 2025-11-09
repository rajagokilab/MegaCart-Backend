# order/views.py
import razorpay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

# Models
from .models import Order, OrderItem, OrderStatusHistory
from product_app.models import Product

# Permissions
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsVendor

# Serializers
from .serializers import OrderSerializer, VendorOrderSerializer

User = get_user_model()

# Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
import logging
logger = logging.getLogger(__name__)

# ✅ CREATE ORDER + RAZORPAY ORDER
class CreateRazorpayOrder(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        grand_total = float(request.data.get('grand_total'))
        items = request.data.get('items')
        shipping_address = request.data.get('shipping_address')

        if not items or grand_total <= 0:
            return Response({"error": "Cart is empty or invalid."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Create internal order
        try:
            with transaction.atomic():
                new_order = Order.objects.create(
                    user=user,
                    total_amount=grand_total,
                    status="Pending",
                    shipping_address=shipping_address,
                )

                for item_data in items:
                    product = Product.objects.get(id=item_data['id'])
                    OrderItem.objects.create(
                        order=new_order,
                        product=product,
                        quantity=item_data['quantity'],
                        price=product.price
                    )

        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Failed to create order: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ✅ Create Razorpay order
        try:
            razorpay_data = {
                "amount": int(grand_total * 100),
                "currency": "INR",
                "receipt": f"order_rcpt_{new_order.id}",
            }
            rp_order = client.order.create(data=razorpay_data)

        except Exception as e:
            new_order.delete()
            return Response({"error": f"Razorpay error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        new_order.razorpay_order_id = rp_order["id"]
        new_order.save()

        return Response({
            "razorpay_order_id": rp_order["id"],
            "amount": rp_order["amount"],
            "currency": rp_order["currency"],
        })


# ✅ VERIFY PAYMENT + SEND EMAIL TO VENDORS
class PaymentVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"Payment payload received: {request.data}")
        rzp_order_id = request.data.get("razorpay_order_id")
        rzp_payment_id = request.data.get("razorpay_payment_id")
        rzp_signature = request.data.get("razorpay_signature")

        # ✅ Find Pending order
        try:
            order = Order.objects.get(
                user=request.user,
                razorpay_order_id=rzp_order_id,
                status="Pending"
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already processed"}, status=404)

        # ✅ Verify Razorpay signature
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": rzp_order_id,
                "razorpay_payment_id": rzp_payment_id,
                "razorpay_signature": rzp_signature,
            })

            # ✅ Mark order as paid
            order.status = "Paid"
            order.razorpay_payment_id = rzp_payment_id
            order.razorpay_signature = rzp_signature
            order.save()

            OrderStatusHistory.objects.create(
                order=order,
                status="Paid",
                changed_by=request.user,
            )

            # ✅ SEND EMAIL TO VENDORS (SAFE MODE)
            vendors_map = {}
            for item in order.items.all():
                vendor_email = item.product.vendor.email
                vendors_map.setdefault(vendor_email, []).append(item)

            for email, items_list in vendors_map.items():

                # ✅ Prepare email content
                subject = f"New Order Received (Order #{order.id})"
                body = f"Dear Vendor,\n\nYou have new items to prepare:\n\n"

                for item in items_list:
                    body += f"- {item.product.name} (Qty: {item.quantity})\n"

                body += (
                    f"\nCustomer: {request.user.username}\n"
                    f"Order ID: {order.id}\n"
                    "Please check your vendor dashboard.\n\nMegaCart Team"
                )

                # ✅ IMPORTANT: This will NOT crash on Render
                try:
                    send_mail(
                        subject,
                        body,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=True,      # ✅ Email failure will NOT stop payment success
                    )
                except Exception as e:
                    logger.error(f"Email sending failed (ignored): {str(e)}")

            return Response({"message": "Payment verified successfully."})

        except razorpay.errors.SignatureVerificationError:
            order.status = "Failed"
            order.save()
            return Response({"error": "Payment verification failed"}, status=400)

        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}", exc_info=True)
            return Response({"error": "Server error during verification"}, status=500)

# ✅ CUSTOMER ORDER LIST
class OrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")


# ✅ VENDOR ORDER LIST
class VendorOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsVendor]
    serializer_class = VendorOrderSerializer

    def get_queryset(self):
        return (
            Order.objects.filter(items__product__vendor=self.request.user)
            .distinct()
            .order_by("-created_at")
        )


# ✅ VENDOR UPDATES STATUS (Shipped / Delivered) — Notify Customer
class OrderStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def patch(self, request, order_id):
        new_status = request.data.get("status")

        order = get_object_or_404(Order, id=order_id)
        old_status = order.status

        # ✅ Update order status
        order.status = new_status
        order.save()

        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            changed_by=request.user
        )

        # ✅ Only send email on Shipped or Delivered AND only if status changed
        if new_status in ["Shipped", "Delivered"] and old_status != new_status:

            # ✅ Prepare email content
            subject = f"Your Order #{order.id} is now {new_status}"
            message = (
                f"Dear {order.user.username},\n\n"
                f"Your order #{order.id} status has been updated to {new_status}.\n\n"
                f"Thank you for shopping with MegaCart!"
            )

            # ✅ Render-safe email sending
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [order.user.email],
                    fail_silently=True  # ✅ Never crash server
                )
            except Exception as e:
                logger.error(f"Email sending failed (ignored): {str(e)}")

        return Response({
            "message": "Status updated successfully",
            "status": new_status
        })
