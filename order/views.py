# order/views.py
import razorpay
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.core.mail import send_mail
from django.db import transaction
from django.contrib.auth import get_user_model

# Import models from this app
from .models import Order, OrderItem
# Import models from other apps
from product_app.models import Product 
from users.permissions import IsVendor # Import your custom permission

# Import serializers from this app
from .serializers import OrderSerializer, VendorOrderSerializer

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
User = get_user_model()



class CreateRazorpayOrder(APIView):
    """
    Creates a pending internal order (with items) and a corresponding Razorpay order.
    Called by the frontend when "Proceed to Payment" is clicked.
    """
    permission_classes = [IsAuthenticated] 

    def post(self, request):
        user = request.user
        
        # Get data from frontend (CheckoutPage.jsx)
        grand_total = float(request.data.get('grand_total'))
        items = request.data.get('items') # e.g., [{'id': 1, 'quantity': 2}, ...]
        shipping_address = request.data.get('shipping_address')

        if not items or grand_total <= 0:
            return Response({"error": "Cart is empty or total is zero."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Create Internal Order (Status: Pending)
        try:
            with transaction.atomic():
                new_order = Order.objects.create(
                    user=user,
                    total_amount=grand_total,
                    status='Pending',
                    shipping_address=shipping_address # Save the address
                )
                
                # Create OrderItem objects
                for item_data in items:
                    product = Product.objects.get(id=item_data.get('id'))
                    OrderItem.objects.create(
                        order=new_order,
                        product=product,
                        quantity=item_data.get('quantity'),
                        price=product.price # Lock the price at time of purchase
                    )
                
        except Product.DoesNotExist:
            return Response({"error": "A product in the cart was not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"Failed to create internal order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Create Razorpay Order
        amount_in_paisa = int(grand_total * 100)
        razorpay_order_data = {
            "amount": amount_in_paisa,  
            "currency": "INR",
            "receipt": f"order_rcpt_{new_order.id}",
        }

        try:
            razorpay_order = client.order.create(data=razorpay_order_data)
        except Exception as e:
            new_order.delete() # Rollback
            return Response({"error": f"Razorpay error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Save Razorpay ID to your order
        new_order.razorpay_order_id = razorpay_order['id']
        new_order.save()

        # 4. Return Razorpay Order ID to frontend
        return Response({
            "razorpay_order_id": razorpay_order['id'],
            "amount": razorpay_order['amount'],
            "currency": razorpay_order['currency'],
        }, status=status.HTTP_200_OK)


class PaymentVerificationView(APIView):
    """
    Verifies the payment signature from Razorpay.
    If successful, marks order as 'Paid' and sends vendor emails.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        # 1. Find your internal order
        try:
            order = Order.objects.get(
                user=request.user,
                razorpay_order_id=razorpay_order_id,
                status='Pending'
            )
        except Order.DoesNotExist:
            return Response({"error": "Order not found or already processed"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Verify the signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
            
            # 3. Update Order Status to 'Paid'
            order.status = 'Paid'
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.save()
            OrderStatusHistory.objects.create(
                order=order,
                status='Paid',
                changed_by=request.user # The customer who paid
            )
            
            # --- 4. 📧 VENDOR EMAIL NOTIFICATION ---
            try:
                vendors_to_notify = {}
                
                # Get all items from the order
                order_items = order.items.all().prefetch_related('product__vendor')
                
                for item in order_items:
                    # 'item.product.vendor' IS the CustomUser
                    vendor_email = item.product.vendor.email
                    
                    if vendor_email not in vendors_to_notify:
                        vendors_to_notify[vendor_email] = []
                    
                    vendors_to_notify[vendor_email].append(item)

                # Send one email per vendor
                for email, items_list in vendors_to_notify.items():
                    subject = f"[MegaCart] New Order Received! (Order ID: {order.id})"
                    message_body = f"You have received a new order.\n\n" \
                                   f"Order ID: {order.id}\n" \
                                   f"Customer: {request.user.username}\n\n" \
                                   f"Items to prepare:\n"
                    
                    for item in items_list:
                        message_body += f"- {item.product.name} (Qty: {item.quantity}) at ₹{item.price}\n"
                    
                    message_body += "\nPlease log in to your vendor dashboard to manage this order."
                    
                    send_mail(
                        subject,
                        message_body,
                        settings.DEFAULT_FROM_EMAIL, # 'from' email (from settings.py)
                        [email],                     # 'to' email (the vendor)
                        fail_silently=False,
                    )
            except Exception as e:
                # Don't fail the whole order, just log the email error
                print(f"CRITICAL ERROR: Failed to send vendor email for Order {order.id}: {str(e)}")
            
            # TODO: Clear the user's cart
            # (You can get the cart with Cart.objects.get(user=request.user, is_active=True))
            
            return Response({"message": "Payment successful, order marked as Paid."}, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            order.status = 'Failed'
            order.save()
            return Response({"error": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            order.status = 'Failed'
            order.save()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderListView(generics.ListAPIView):
    """
    Gets a list of all orders for the currently authenticated customer.
    (For the "My Orders" page)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')


class VendorOrderListView(generics.ListAPIView):
    """
    API view for a logged-in vendor to see all orders
    that contain their products. (For the "Orders" tab in MyPage)
    """
    permission_classes = [IsAuthenticated, IsVendor] # Use your vendor permission
    serializer_class = VendorOrderSerializer

    def get_queryset(self):
        user = self.request.user
        
        # This is the correct, simplified query
        queryset = Order.objects.filter(
            items__product__vendor=user
        ).distinct().order_by('-created_at')
        
        return queryset

    def get_serializer_context(self):
        # Pass 'request' to the serializer for 'get_items' method
        return {'request': self.request}
    
    # order/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404 # Needed for update view

# --- 1. Import new model and necessary permissions ---
from .models import Order, OrderItem, OrderStatusHistory 
from .serializers import OrderSerializer, VendorOrderSerializer # Will be updated to include history
from product_app.models import Product 
from users.permissions import IsVendor # Assuming you have this custom permission
# ... (Other imports: razorpay, settings, User) ...


# --- A. OrderStatusUpdateView (NEW API) ---
# order/views.py

# ... (Existing imports: send_mail, Order, OrderStatusHistory, etc.) ...

class OrderStatusUpdateView(APIView):
    # ... (patch method start) ...

    def patch(self, request, order_id):
        new_status = request.data.get('status')
        user = request.user
        
        # ... (Validation and Permission Checks are fine) ...
        
        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        # Store the old status before updating
        old_status = order.status 

        # 1. Check permissions (already handled)
        # ... 

        # 2. Update the Order status and create History Record
        order.status = new_status
        order.save(update_fields=['status'])

        OrderStatusHistory.objects.create(
            order=order,
            status=new_status,
            changed_by=user
        )
        
        # --- 🎯 NEW LOGIC: NOTIFY CUSTOMER ON SHIPPED/DELIVERED ---
        
        if new_status in ['Shipped', 'Delivered'] and new_status != old_status:
            try:
                subject_map = {
                    'Shipped': f"📦 Order #{order.id} is on its way!",
                    'Delivered': f"🎉 Order #{order.id} has been delivered!",
                }
                
                message = (
                    f"Dear {order.user.username},\n\n"
                    f"The status of your order #{order.id} has been updated to **{new_status}**.\n\n"
                    f"Items are being shipped by your vendor. You can check the tracking history on your dashboard.\n\n"
                    f"Thank you for shopping with MegaCart!"
                )
                
                send_mail(
                    subject_map[new_status],
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [order.user.email], # Send email to the customer
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't fail the API response
                print(f"Error sending customer status email for Order {order.id}: {e}")
        # --- END NEW LOGIC ---

        return Response(
            {"message": f"Order {order_id} status updated to {new_status}.", "status": new_status}, 
            status=status.HTTP_200_OK
        )
    
    