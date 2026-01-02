from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    def kyc_document_link(self, obj):
        if obj.kyc_document:
            return format_html('<a href="{}" target="_blank">View Doc</a>', obj.kyc_document.url)
        return "-"
    kyc_document_link.short_description = "KYC Proof"
    list_display = ('email', 'store_name', 'business_reg_id', 'kyc_document_link', 'is_approved')   
    list_filter = ('role', 'is_approved', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username', 'store_name')
    list_editable = ('is_approved',)
    ordering = ('role', 'email')
    readonly_fields = ('last_login', 'date_joined')

    

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password', 'role', 'store_name')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('KYC Details', {'fields': ('business_reg_id', 'kyc_document', 'is_approved')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 'store_name', 'is_staff', 'is_active')}
        ),
    )

    # 🛑 FIX: Ensure request.user is authenticated before accessing the custom 'role' attribute.
    
    def has_add_permission(self, request):
        # Only allow authenticated users with the specific ADMIN role
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_change_permission(self, request, obj=None):
        # Only allow authenticated users with the specific ADMIN role
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_delete_permission(self, request, obj=None):
        # Only allow authenticated users with the specific ADMIN role
        return request.user.is_authenticated and request.user.role == 'ADMIN'
    
    