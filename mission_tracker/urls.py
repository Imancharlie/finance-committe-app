"""
Multi-tenant URL configuration for Bossin Finance App.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from tracker.views import offline_view

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # PWA support (temporarily disabled due to Django 5.2 compatibility)
    # path('', include('pwa.urls')),
    
    # Tracker app (includes tenant-specific routes)
    path('', include('tracker.urls')),
    
    # Offline support
    path('offline/', offline_view, name='offline'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)