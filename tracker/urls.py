from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
app_name = 'tracker'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('accounts/password-change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='/accounts/password-change/done/'
    ), name='password_change'),
    path('accounts/logout/', auth_views.LogoutView.as_view(
        next_page='login'  # or wherever you want to redirect after logout
    ), name='logout'),
    path('accounts/password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('daily-collection/', views.daily_collection, name='daily_collection'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path('member/add/', views.add_member, name='add_member'),
    path('member/<int:member_id>/edit/', views.edit_member, name='edit_member'),
    path('admin-log/', views.admin_log, name='admin_log'),
    path('import-excel/', views.import_excel, name='import_excel'),
    path('ajax/update-transaction/', views.update_transaction_ajax, name='update_transaction_ajax'),
    path('ajax/delete-transaction/', views.delete_transaction_ajax, name='delete_transaction_ajax'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    # PWA support
    path('offline/', views.offline_view, name='offline'),


    # Member editing URLs
    path('members/edit/', views.edit_members, name='edit_members'),
    path('ajax/update-member/', views.update_member_ajaxs, name='update_member_ajax'),
    path('ajax/delete-member/', views.delete_member_ajaxs, name='delete_member_ajax'),
    path('ajax/add-member/', views.add_member_ajaxs, name='add_member_ajax'),

    # # AJAX endpoints
    path('ajax/update-members/', views.update_member_ajax, name='update_member_ajaxs'),
    path('ajax/add-members/', views.add_member_ajax, name='add_member_ajaxs'),
    path('ajax/update-transaction-note/', views.update_transaction_note_ajax, name='update_transaction_note_ajax'),
    path('ajax/record-daily-payment/', views.record_daily_payment_ajax, name='record_daily_payment_ajax'),
]