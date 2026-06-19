from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views
app_name = 'tracker'

# Tenant-specific URLs (with org_slug prefix)
tenant_urlpatterns = [
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('daily-collection/', views.daily_collection, name='daily_collection'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path('member/add/', views.add_member, name='add_member'),
    path('member/<int:member_id>/edit/', views.edit_member, name='edit_member'),
    path('admin-log/', views.admin_log, name='admin_log'),
    path('export/admin-log/excel/', views.export_admin_log_excel, name='export_admin_log_excel'),
    path('export/admin-log/pdf/', views.export_admin_log_pdf, name='export_admin_log_pdf'),
    path('export/member-edit-log/excel/', views.export_member_edit_log_excel, name='export_member_edit_log_excel'),
    path('export/member-edit-log/pdf/', views.export_member_edit_log_pdf, name='export_member_edit_log_pdf'),
    path('health/', views.health_check, name='health_check'),
    path('import-excel/', views.import_excel, name='import_excel'),
    path('ajax/update-transaction/', views.update_transaction_ajax, name='update_transaction_ajax'),
    path('ajax/delete-transaction/', views.delete_transaction_ajax, name='delete_transaction_ajax'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('offline/', views.offline_view, name='offline'),
    path('help/', views.help_center, name='help_center'),
    path('help/', views.help_center, name='help_center'),
    
    # Member editing URLs
    path('members/edit/', views.edit_members, name='edit_members'),
    path('ajax/update-member/', views.update_member_ajaxs, name='update_member_ajax'),
    path('ajax/delete-member/', views.delete_member_ajaxs, name='delete_member_ajax'),
    path('ajax/add-member/', views.add_member_ajaxs, name='add_member_ajax'),
    
    # AJAX endpoints
    path('ajax/update-members/', views.update_member_ajax, name='update_member_ajaxs'),
    path('ajax/add-members/', views.add_member_ajax, name='add_member_ajaxs'),
    path('ajax/update-transaction-note/', views.update_transaction_note_ajax, name='update_transaction_note_ajax'),
    path('ajax/record-daily-payment/', views.record_daily_payment_ajax, name='record_daily_payment_ajax'),
    
    # Organization Admin URLs
    path('admin/', views.org_admin_dashboard, name='org_admin_dashboard'),
    path('admin/settings/', views.org_settings, name='org_settings'),
    path('admin/branding/', views.org_branding, name='org_branding'),
    path('admin/billing/', views.org_billing, name='org_billing'),
    path('admin/financial-settings/', views.org_financial_settings, name='org_financial_settings'),
    path('admin/staff/', views.org_staff_management, name='org_staff_management'),
    path('admin/staff/add/', views.add_staff_member, name='add_staff_member'),
    path('admin/staff/<int:staff_id>/edit/', views.edit_staff_member, name='edit_staff_member'),
    path('admin/staff/<int:staff_id>/remove/', views.remove_staff_member, name='remove_staff_member'),
    
    # Onboarding URLs
    path('onboarding/financial/', views.onboarding_financial, name='onboarding_financial'),
    path('onboarding/branding/', views.onboarding_branding, name='onboarding_branding'),
    path('onboarding/staff/', views.onboarding_staff, name='onboarding_staff'),
    path('onboarding/import/', views.onboarding_import, name='onboarding_import'),
    path('onboarding/subscription/', views.onboarding_subscription, name='onboarding_subscription'),
    path('staff/onboarding/', views.staff_onboarding, name='staff_onboarding'),
    
    # Subscription renewal page (for expired subscriptions)
    path('subscription/', views.subscription_renewal, name='subscription_renewal'),
]

# Global URLs (not tenant-specific)
urlpatterns = [
    # Public pages (MUST be before org_slug pattern)
    path('', views.landing_view, name='landing'),
    path('terms/', views.terms_view, name='terms'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    
    # Authentication (global)
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='/accounts/password-change/done/'
    ), name='password_change'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='/login/'
    ), name='logout'),
    path('accounts/password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    
    # Tenant-specific URLs with org_slug prefix (MUST be last)
    path('<slug:org_slug>/', include(tenant_urlpatterns)),
]