"""Shared API utility functions."""

from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, Q

from tracker.models import (
    Member,
    Transaction,
    Organization,
    OrganizationUser,
    SystemSettings,
)


def get_organization_by_slug(slug):
    """Resolve an active organization by slug."""
    return Organization.objects.select_related('theme').get(slug=slug, is_active=True)


def get_user_org_membership(user, organization):
    """Get active OrganizationUser record for user in org."""
    return OrganizationUser.objects.select_related('user', 'organization').get(
        user=user,
        organization=organization,
        is_active=True,
    )


def check_subscription_active(organization):
    """
    Check if organization has active subscription or trial.
    Returns (is_active, status_info dict).
    Auto-updates expired statuses like the web middleware.
    """
    now = timezone.now()
    org = organization

    if org.subscription_status == 'FREE_TRIAL' and org.trial_started_at:
        trial_end = org.trial_started_at + timezone.timedelta(days=7)
        if trial_end <= now:
            org.subscription_status = 'NOT_SUBSCRIBED'
            org.save(update_fields=['subscription_status'])

    if org.subscription_status == 'SUBSCRIBED' and org.subscription_expires_at:
        if org.subscription_expires_at <= now:
            org.subscription_status = 'NOT_SUBSCRIBED'
            org.save(update_fields=['subscription_status'])

    active_sub = bool(
        org.subscription_status == 'SUBSCRIBED'
        and org.subscription_expires_at
        and org.subscription_expires_at > now
    )

    trial_active = bool(
        org.subscription_status == 'FREE_TRIAL'
        and org.trial_started_at
        and (org.trial_started_at + timezone.timedelta(days=7) > now)
    )

    days_remaining = None
    if active_sub and org.subscription_expires_at:
        days_remaining = (org.subscription_expires_at - now).days
    elif trial_active and org.trial_started_at:
        trial_end = org.trial_started_at + timezone.timedelta(days=7)
        days_remaining = (trial_end - now).days

    status_info = {
        'subscription_status': org.subscription_status,
        'is_active': active_sub or trial_active,
        'trial_active': trial_active,
        'subscription_active': active_sub,
        'days_remaining': days_remaining,
        'subscription_expires_at': (
            org.subscription_expires_at.isoformat() if org.subscription_expires_at else None
        ),
        'trial_started_at': (
            org.trial_started_at.isoformat() if org.trial_started_at else None
        ),
    }

    is_active = active_sub or trial_active
    if org.subscription_status == 'NOT_SUBSCRIBED':
        is_active = False

    return is_active, status_info


def get_dashboard_stats(organization, members_qs=None):
    """Calculate dashboard statistics for an organization."""
    if members_qs is None:
        members_qs = Member.objects.filter(organization=organization, is_active=True)

    members = list(members_qs)

    try:
        target_amount = Decimal(str(organization.theme.target_amount))
    except Exception:
        target_amount = Decimal('210000.00')

    total_collected = Decimal('0.00')
    total_pledged = Decimal('0.00')
    not_paid_count = 0
    incomplete_count = 0
    complete_count = 0
    exceeded_count = 0

    for member in members:
        pledge = member.pledge if member.pledge is not None else Decimal('70000.00')
        paid_total = member.paid_total if member.paid_total is not None else Decimal('0.00')

        total_pledged += pledge
        total_collected += paid_total

        if paid_total == 0:
            not_paid_count += 1
        elif paid_total < pledge:
            incomplete_count += 1
        elif paid_total == pledge:
            complete_count += 1
        else:
            exceeded_count += 1

    progress_percentage = float(
        (total_collected / target_amount * 100) if target_amount > 0 else 0
    )

    return {
        'total_collected': str(total_collected),
        'total_pledged': str(total_pledged),
        'target_amount': str(target_amount),
        'progress_percentage': round(progress_percentage, 2),
        'member_count': len(members),
        'not_paid_count': not_paid_count,
        'incomplete_count': incomplete_count,
        'complete_count': complete_count,
        'exceeded_count': exceeded_count,
    }


def filter_members_queryset(queryset, search=None, status_filter=None):
    """Apply search and status filters to member queryset."""
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )

    if status_filter == 'not_started':
        queryset = queryset.filter(paid_total=0)
    elif status_filter == 'incomplete':
        queryset = queryset.filter(paid_total__gt=0).extra(
            where=['paid_total < pledge']
        )
    elif status_filter == 'complete':
        queryset = queryset.extra(where=['paid_total >= pledge'])
    elif status_filter == 'exceeded':
        queryset = queryset.extra(where=['paid_total > pledge'])
    elif status_filter == 'pledged':
        queryset = queryset.filter(pledge__gt=Decimal('70000'))

    return queryset


def get_subscription_pricing(organization):
    """Calculate subscription pricing for an organization."""
    settings = SystemSettings.get_settings()
    base_price = settings.base_price_tzs
    category_discount = settings.get_category_discount(organization.category)

    return {
        'base_price_tzs': str(base_price),
        'category_discount_percent': category_discount,
        'category': organization.category,
        'mpesa_number': settings.mpesa_number,
        'mpesa_account_name': settings.mpesa_account_name,
        'support_email': settings.support_email,
        'support_phone': settings.support_phone,
    }


def calculate_subscription_amount(months, organization):
    """Calculate total subscription amount for given months."""
    settings = SystemSettings.get_settings()
    base_price = settings.base_price_tzs
    category_discount = settings.get_category_discount(organization.category)

    months = max(1, min(12, int(months)))
    first_month_price = base_price * (Decimal('100') - Decimal(category_discount)) / Decimal('100')
    total_amount = first_month_price + (base_price * (months - 1))

    return total_amount.quantize(Decimal('1.00')), int(category_discount)


def success_response(data=None, status=200, meta=None):
    """Build a consistent success response."""
    from rest_framework.response import Response

    payload = {'success': True, 'data': data, 'error': None}
    if meta is not None:
        payload['meta'] = meta
    return Response(payload, status=status)


def error_response(message, status=400, extra=None):
    """Build a consistent error response."""
    from rest_framework.response import Response

    payload = {'success': False, 'data': None, 'error': message}
    if extra:
        payload.update(extra)
    return Response(payload, status=status)
