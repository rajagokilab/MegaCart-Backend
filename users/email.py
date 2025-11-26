# from djoser import email

# class CustomPasswordResetEmail(email.PasswordResetEmail):
#     def get_context_data(self):
#         # 1. Grab the default data (user, uid, token)
#         context = super().get_context_data()

#         # 2. OVERRIDE: Force the domain to your React Frontend Port
#         # If you deploy to production later, change this to your real domain (e.g., vetricart.com)
#         context['domain'] = 'localhost:5173'
#         context['site_name'] = 'VetriCart'
        
#         return context

from djoser import email
from django.conf import settings

class CustomPasswordResetEmail(email.PasswordResetEmail):
    def get_context_data(self):
        context = super().get_context_data()

        # This reads the variable you just set in the dashboard
        # If it's missing, it defaults to localhost (which is why you had the error)
        context['domain'] = getattr(settings, 'FRONTEND_DOMAIN', 'localhost:5173')
        context['site_name'] = 'VetriCart'
        
        # Ensure the link is HTTPS in production
        if not settings.DEBUG:
            context['protocol'] = 'https'

        return context