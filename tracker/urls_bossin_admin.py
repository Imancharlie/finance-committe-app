"""
URL configuration for Bossin Admin Portal.
Accessible only to superusers at /bossin-admin/
"""
from django.urls import path
from . import views_bossin_admin

app_name = 'bossin_admin'

urlpatterns = [
    # Dashboard
    path('', views_bossin_admin.bossin_dashboard, name='dashboard'),
    
    # Organizations
    path('organizations/', views_bossin_admin.bossin_organizations, name='organizations'),
    path('organizations/<int:org_id>/', views_bossin_admin.bossin_organization_detail, name='organization_detail'),
    path('organizations/<int:org_id>/suspend/', views_bossin_admin.bossin_organization_suspend, name='organization_suspend'),
    
    # Subscriptions (Payment Requests)
    path('subscriptions/', views_bossin_admin.bossin_subscriptions, name='subscriptions'),
    path('subscriptions/<int:request_id>/approve/', views_bossin_admin.bossin_subscription_approve, name='subscription_approve'),
    path('subscriptions/<int:request_id>/decline/', views_bossin_admin.bossin_subscription_decline, name='subscription_decline'),
    
    # Themes & Categories
    path('themes/', views_bossin_admin.bossin_themes, name='themes'),
    path('themes/update/', views_bossin_admin.bossin_themes_update, name='themes_update'),
    
    # Backups
    path('backups/', views_bossin_admin.bossin_backups, name='backups'),
    path('backups/create/', views_bossin_admin.bossin_backup_create, name='backup_create'),
    path('backups/download/', views_bossin_admin.bossin_backup_download, name='backup_download'),
    path('backups/restore/', views_bossin_admin.bossin_backup_restore, name='backup_restore'),
    
    # Users
    path('users/', views_bossin_admin.bossin_users, name='users'),
    
    # System Settings
    path('settings/', views_bossin_admin.bossin_settings, name='settings'),
]

