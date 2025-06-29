from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('daily-collection/', views.daily_collection, name='daily_collection'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path('member/add/', views.add_member, name='add_member'),
    path('member/<int:member_id>/edit/', views.edit_member, name='edit_member'),
    path('admin-log/', views.admin_log, name='admin_log'),
    path('import-excel/', views.import_excel, name='import_excel'),
    
    # PWA support
    path('offline/', views.offline_view, name='offline'),
    
    # AJAX endpoints
    path('ajax/update-member/', views.update_member_ajax, name='update_member_ajax'),
    path('ajax/add-member/', views.add_member_ajax, name='add_member_ajax'),
    path('ajax/update-transaction-note/', views.update_transaction_note_ajax, name='update_transaction_note_ajax'),
    path('ajax/record-daily-payment/', views.record_daily_payment_ajax, name='record_daily_payment_ajax'),
] 