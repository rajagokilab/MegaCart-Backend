from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # Product app endpoints
    path('api/', include('product_app.urls')),
    path('api/', include('order.urls')),

    # User management / authentication
    # path('api/', include('users.urls')),            # your custom user endpoints
    path('api/auth/', include('djoser.urls')),      # login/logout/user
    path('api/auth/', include('djoser.urls.jwt')),
      path('api/support/', include('support.urls')),
      path('api/users/', include('users.urls')),

  # JWT login/logout
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)