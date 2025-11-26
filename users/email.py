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
        # 1. Get default data
        context = super().get_context_data()

        # 2. Link to the logic you just wrote in settings.py
        context['domain'] = settings.FRONTEND_DOMAIN
        context['protocol'] = settings.PROTOCOL
        context['site_name'] = 'VetriCart'
        
        return context