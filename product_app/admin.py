from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import Category, Product
from users.models import CustomUser 

# ----------------------------------------
# 1. Helper Function (Image Preview)
# ----------------------------------------
def get_image_preview_tag(obj):
    if obj.image and hasattr(obj.image, 'url'):
        return format_html(
            '<img src="{}" width="50" height="50" style="object-fit:cover; border-radius: 4px;" />',
            obj.image.url
        )
    return "-"
get_image_preview_tag.short_description = 'Preview'

# ----------------------------------------
# 2. Category Form (MUST BE DEFINED FIRST)
# ----------------------------------------
class CategoryAddForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'slug', 'image', 'is_active') 

# ----------------------------------------
# 3. Category Admin
# ----------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAddForm  # ✅ Class is now defined above

    # List View Settings
    list_display = ('name', 'slug', 'is_active', get_image_preview_tag)
    list_editable = ('is_active',) # ⚡ Quick Toggle in list view
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name', 'is_active')
    search_fields = ('name',)
    readonly_fields = (get_image_preview_tag,)

    # --- CUSTOM BULK ACTIONS ---
    actions = ['make_active', 'make_inactive']

    @admin.action(description="✅ Mark selected as Active")
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} categories marked as Active.")

    @admin.action(description="❌ Mark selected as Inactive")
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} categories marked as Inactive.")

    # --- PERMISSIONS (Strictly Admin Only) ---
    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'


# ----------------------------------------
# 4. Product Admin
# ----------------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Display key info columns
    list_display = (
        'name', 
        'category', 
        'vendor_name', 
        'price', 
        'status',         # Show current status (Pending/Approved)
        'is_published',   # Show published state
        'stock', 
        get_image_preview_tag
    )
    
    # Filters sidebar
    list_filter = ('category', 'status', 'is_published')
    search_fields = ('name', 'vendor__store_name')
    
    # Allow editing these directly in the list view (Fast Edit)
    list_editable = ('price', 'status', 'is_published', 'stock') 

    # Layout for the "Add/Edit Product" page
    fieldsets = (
        (None, {'fields': ('name', 'category')}), 
        ('Vendor Details', {'fields': ('vendor',)}),
        ('Pricing and Inventory', {'fields': ('price', 'stock', 'status', 'is_published')}),
        ('Media', {'fields': ('image', get_image_preview_tag)}), 

    )
    
    readonly_fields = (get_image_preview_tag,) 

    # --- CUSTOM ACTIONS ---
    actions = ['mark_approved', 'mark_pending', 'mark_rejected', 'publish_products', 'unpublish_products']

    @admin.action(description="✅ Approve selected products")
    def mark_approved(self, request, queryset):
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f"{updated} products have been APPROVED.")

    @admin.action(description="⏳ Set selected products to Pending")
    def mark_pending(self, request, queryset):
        updated = queryset.update(status='PENDING')
        self.message_user(request, f"{updated} products marked as PENDING.")

    @admin.action(description="❌ Reject selected products")
    def mark_rejected(self, request, queryset):
        updated = queryset.update(status='REJECTED')
        self.message_user(request, f"{updated} products have been REJECTED.")

    @admin.action(description="👁️ Publish selected products")
    def publish_products(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} products are now PUBLIC.")

    @admin.action(description="🔒 Unpublish (Hide) selected products")
    def unpublish_products(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} products are now HIDDEN.")

    # --- HELPER METHODS ---
    def vendor_name(self, obj):
        return obj.vendor.store_name if obj.vendor else '-'
    vendor_name.short_description = 'Vendor'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only show VENDOR users in the dropdown
        if db_field.name == "vendor":
            kwargs["queryset"] = CustomUser.objects.filter(role='VENDOR')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Only show data if user is ADMIN
        if request.user.is_authenticated and request.user.role == 'ADMIN':
            return qs
        return self.model.objects.none()

    # --- PERMISSIONS ---
    def has_add_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_change_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_delete_permission(self, request, obj=None):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

    def has_module_permission(self, request):
        return request.user.is_authenticated and request.user.role == 'ADMIN'