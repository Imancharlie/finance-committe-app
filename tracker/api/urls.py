"""API URL routing for Bossin Finance mobile application."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from tracker.api import views

app_name = 'api'

urlpatterns = [
    # API documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),

    # System
    path('health/', views.HealthCheckAPIView.as_view(), name='health'),
    path('help/', views.HelpInfoAPIView.as_view(), name='help'),

    # Authentication
    path('auth/login/', views.LoginAPIView.as_view(), name='login'),
    path('auth/register/', views.RegisterAPIView.as_view(), name='register'),
    path('auth/refresh/', views.RefreshTokenAPIView.as_view(), name='token_refresh'),
    path('auth/me/', views.MeAPIView.as_view(), name='me'),

    # Organizations
    path('orgs/', views.OrganizationListAPIView.as_view(), name='org_list'),

    # Organization-scoped endpoints
    path(
        'orgs/<slug:org_slug>/',
        views.OrganizationDetailAPIView.as_view(),
        name='org_detail',
    ),
    path(
        'orgs/<slug:org_slug>/theme/',
        views.OrganizationThemeAPIView.as_view(),
        name='org_theme',
    ),
    path(
        'orgs/<slug:org_slug>/dashboard/stats/',
        views.DashboardStatsAPIView.as_view(),
        name='dashboard_stats',
    ),
    path(
        'orgs/<slug:org_slug>/onboarding/',
        views.StaffOnboardingAPIView.as_view(),
        name='staff_onboarding',
    ),

    # Members
    path(
        'orgs/<slug:org_slug>/members/',
        views.MemberListCreateAPIView.as_view(),
        name='member_list',
    ),
    path(
        'orgs/<slug:org_slug>/members/<int:member_id>/',
        views.MemberDetailAPIView.as_view(),
        name='member_detail',
    ),
    path(
        'orgs/<slug:org_slug>/members/<int:member_id>/transactions/',
        views.MemberTransactionsAPIView.as_view(),
        name='member_transactions',
    ),

    # Transactions
    path(
        'orgs/<slug:org_slug>/transactions/',
        views.TransactionListAPIView.as_view(),
        name='transaction_list',
    ),
    path(
        'orgs/<slug:org_slug>/transactions/bulk/',
        views.BulkPaymentAPIView.as_view(),
        name='bulk_payment',
    ),
    path(
        'orgs/<slug:org_slug>/transactions/<int:transaction_id>/',
        views.TransactionDetailAPIView.as_view(),
        name='transaction_detail',
    ),

    # Staff
    path(
        'orgs/<slug:org_slug>/staff/',
        views.StaffListCreateAPIView.as_view(),
        name='staff_list',
    ),
    path(
        'orgs/<slug:org_slug>/staff/<int:staff_id>/',
        views.StaffDetailAPIView.as_view(),
        name='staff_detail',
    ),

    # Audit
    path(
        'orgs/<slug:org_slug>/audit/member-edits/',
        views.MemberEditLogAPIView.as_view(),
        name='member_edit_log',
    ),

    # Subscription
    path(
        'orgs/<slug:org_slug>/subscription/',
        views.SubscriptionStatusAPIView.as_view(),
        name='subscription_status',
    ),
    path(
        'orgs/<slug:org_slug>/subscription/payment-requests/',
        views.PaymentRequestCreateAPIView.as_view(),
        name='payment_request_create',
    ),

    # Export/Import
    path(
        'orgs/<slug:org_slug>/export/members/excel/',
        views.ExportMembersExcelAPIView.as_view(),
        name='export_members_excel',
    ),
    path(
        'orgs/<slug:org_slug>/export/transactions/excel/',
        views.ExportTransactionsExcelAPIView.as_view(),
        name='export_transactions_excel',
    ),
    path(
        'orgs/<slug:org_slug>/export/report/pdf/',
        views.ExportReportPDFAPIView.as_view(),
        name='export_report_pdf',
    ),
    path(
        'orgs/<slug:org_slug>/import/members/excel/',
        views.ImportMembersExcelAPIView.as_view(),
        name='import_members_excel',
    ),
]
