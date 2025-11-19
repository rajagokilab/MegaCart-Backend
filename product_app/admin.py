from django.contrib import admin
from .models import Category, Product
from users.models import CustomUser
from django import forms 
from django.contrib.auth.models import AnonymousUser 

# -----------------------------
# 1️⃣ Category Admin (Guarded)
# -----------------------------
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import Category

# -----------------------------
# Category Admin
# -----------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image_tag')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)
    readonly_fields = ('image_tag',)

    # Form for adding/editing categories
    class CategoryAddForm(forms.ModelForm):
        class Meta:
            model = Category
            fields = ('name', 'slug', 'image')  # allow uploading image

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = self.CategoryAddForm
        return super().get_form(request, obj, **kwargs)

    # Show image preview in admin list
    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" style="object-fit:cover;" />',
                obj.image.url
            )
        return "-"
    image_tag.short_description = 'Preview'

    # Permissions (only ADMIN role can manage categories)
    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'



# -----------------------------
# 2️⃣ Product Admin (FINAL FIX)
# -----------------------------
from django.utils.html import format_html

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'vendor_name', 'price', 'status', 'is_published', 'stock', 'created_at', 'image_tag')
    list_filter = ('category', 'status', 'is_published')
    search_fields = ('name', 'vendor__store_name')
    list_editable = ('price', 'status', 'is_published', 'stock') 

    fieldsets = (
        (None, {'fields': ('name', 'category')}), 
        ('Vendor Details', {'fields': ('vendor',)}),
        ('Pricing and Inventory', {'fields': ('price', 'stock', 'status', 'is_published')}),
        ('Media', {'fields': ('image', 'image_tag')}),  # <-- Use real image field + method
    )
    
    readonly_fields = ('vendor', 'image_tag')  # <-- image_tag is read-only

    def vendor_name(self, obj):
        return obj.vendor.store_name if obj.vendor else '-'
    vendor_name.short_description = 'Vendor'

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" style="object-fit:cover;" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Preview'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "vendor":
            kwargs["queryset"] = CustomUser.objects.filter(role='VENDOR')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_authenticated and request.user.role == 'ADMIN':
            return qs
        return qs.none() 

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'
