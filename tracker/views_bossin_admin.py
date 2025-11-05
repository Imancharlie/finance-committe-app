"""
Bossin Admin Portal Views
Platform-wide administration interface for superusers.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
import json
from django.conf import settings
from decimal import Decimal
from pathlib import Path
import os

from .models import Organization, PaymentRequest, OrganizationUser, User, SystemSettings, Transaction, Member
from .permissions import bossin_admin_required


# ============================================================================
# DASHBOARD
# ============================================================================

@bossin_admin_required
def bossin_dashboard(request):
    """Main Bossin Admin Portal dashboard with analytics."""
    
    # Get pending requests count for navbar
    pending_requests_count = PaymentRequest.objects.filter(status='pending').count()
    
    # Organizations Stats
    total_orgs = Organization.objects.count()
    active_orgs = Organization.objects.filter(is_active=True).count()
    trial_orgs = Organization.objects.filter(subscription_status='FREE_TRIAL').count()
    subscribed_orgs = Organization.objects.filter(subscription_status='SUBSCRIBED').count()
    expired_orgs = Organization.objects.filter(subscription_status='NOT_SUBSCRIBED').count()
    
    # Subscription Stats
    pending_requests = PaymentRequest.objects.filter(status='pending').count()
    approved_today = PaymentRequest.objects.filter(
        status='approved',
        updated_at__date=timezone.now().date()
    ).count()
    
    # Revenue Calculation (from approved payment requests)
    total_revenue = PaymentRequest.objects.filter(
        status='approved'
    ).aggregate(total=Sum('amount_tzs'))['total'] or Decimal('0.00')
    
    monthly_revenue = PaymentRequest.objects.filter(
        status='approved',
        updated_at__month=timezone.now().month,
        updated_at__year=timezone.now().year
    ).aggregate(total=Sum('amount_tzs'))['total'] or Decimal('0.00')
    
    # Backup Health
    backup_dir = Path('backups')
    backup_files = list(backup_dir.glob('db_backup_*.gz')) if backup_dir.exists() else []
    latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime) if backup_files else None
    backup_health = 'healthy' if latest_backup and (timezone.now() - timezone.datetime.fromtimestamp(latest_backup.stat().st_mtime, tz=timezone.get_current_timezone())).days < 2 else 'warning'
    
    # Recent Activity
    recent_requests = PaymentRequest.objects.select_related('organization', 'submitted_by').order_by('-created_at')[:10]
    recent_orgs = Organization.objects.order_by('-created_at')[:5]
    
    # Category Distribution
    category_dist = Organization.objects.values('category').annotate(count=Count('id')).order_by('-count')
    
    # Revenue by month (last 6 months)
    from datetime import date, timedelta
    first_of_this_month = timezone.now().date().replace(day=1)
    # Build 6 month starts
    month_starts = []
    cursor = first_of_this_month
    for _ in range(6):
        month_starts.append(cursor)
        # move back approx 1 month by going to previous month's last day then replace to first
        prev = (cursor - timedelta(days=1)).replace(day=1)
        cursor = prev
    month_starts = list(reversed(month_starts))
    revenue_labels = [ms.strftime('%b') for ms in month_starts]
    revenue_values = []
    for i, ms in enumerate(month_starts):
        if i < len(month_starts) - 1:
            me = month_starts[i + 1]
        else:
            # next month start ~ add 31 days and clamp to first
            me = (ms + timedelta(days=31)).replace(day=1)
        total_month = PaymentRequest.objects.filter(
            status='approved', created_at__gte=ms, created_at__lt=me
        ).aggregate(total=Sum('amount_tzs'))['total'] or 0
        revenue_values.append(int(total_month))
    revenue_labels_json = json.dumps(revenue_labels)
    revenue_values_json = json.dumps(revenue_values)
    
    context = {
        'total_orgs': total_orgs,
        'active_orgs': active_orgs,
        'trial_orgs': trial_orgs,
        'subscribed_orgs': subscribed_orgs,
        'expired_orgs': expired_orgs,
        'pending_requests': pending_requests,
        'pending_requests_count': pending_requests_count,
        'approved_today': approved_today,
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'backup_health': backup_health,
        'latest_backup': latest_backup,
        'recent_requests': recent_requests,
        'recent_orgs': recent_orgs,
        'category_dist': category_dist,
        'revenue_labels_json': revenue_labels_json,
        'revenue_values_json': revenue_values_json,
    }
    
    return render(request, 'bossin_admin/dashboard.html', context)


# ============================================================================
# ORGANIZATION MANAGEMENT
# ============================================================================

@bossin_admin_required
def bossin_organizations(request):
    """List all organizations with filtering and search."""
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    
    orgs = Organization.objects.select_related().all()
    
    if search:
        orgs = orgs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
    
    if status_filter:
        orgs = orgs.filter(subscription_status=status_filter)
    
    if category_filter:
        orgs = orgs.filter(category=category_filter)
    
    # Pagination
    paginator = Paginator(orgs.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    orgs_page = paginator.get_page(page)
    
    context = {
        'organizations': orgs_page,
        'search': search,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'total_count': orgs.count(),
    }
    if request.GET.get('partial') == '1':
        return render(request, 'bossin_admin/organizations/_table.html', context)
    return render(request, 'bossin_admin/organizations/list.html', context)


@bossin_admin_required
def bossin_organization_detail(request, org_id):
    """Organization detail view with management options."""
    org = get_object_or_404(Organization, pk=org_id)
    
    # Get organization owner
    owner = OrganizationUser.objects.filter(organization=org, role='owner').first()
    
    # Get organization stats
    members_count = Member.objects.filter(organization=org).count()
    staff_count = OrganizationUser.objects.filter(organization=org, is_active=True).count()
    transactions_count = Transaction.objects.filter(organization=org).count()
    total_collected = Transaction.objects.filter(organization=org).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Payment requests
    payment_requests = PaymentRequest.objects.filter(organization=org).order_by('-created_at')[:10]
    
    # Staff members
    staff_members = OrganizationUser.objects.filter(organization=org).select_related('user')
    
    context = {
        'organization': org,
        'owner': owner,
        'members_count': members_count,
        'staff_count': staff_count,
        'transactions_count': transactions_count,
        'total_collected': total_collected,
        'payment_requests': payment_requests,
        'staff_members': staff_members,
    }
    
    return render(request, 'bossin_admin/organizations/detail.html', context)


@bossin_admin_required
@require_POST
def bossin_organization_suspend(request, org_id):
    """Suspend or reactivate an organization."""
    org = get_object_or_404(Organization, pk=org_id)
    action = request.POST.get('action')
    
    if action == 'suspend':
        org.is_active = False
        messages.success(request, f'Organization "{org.name}" has been suspended.')
    elif action == 'reactivate':
        org.is_active = True
        messages.success(request, f'Organization "{org.name}" has been reactivated.')
    
    org.save()
    return redirect('bossin_admin:organization_detail', org_id=org_id)


# ============================================================================
# SUBSCRIPTION REQUESTS MANAGEMENT
# ============================================================================

@bossin_admin_required
def bossin_subscriptions(request):
    """Manage payment/subscription requests."""
    status_filter = request.GET.get('status', 'pending')
    search = request.GET.get('search', '')
    
    requests = PaymentRequest.objects.select_related('organization', 'submitted_by').all()
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    if search:
        requests = requests.filter(
            Q(organization__name__icontains=search) |
            Q(reference_note__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(requests.order_by('-created_at'), 25)
    page = request.GET.get('page', 1)
    requests_page = paginator.get_page(page)
    
    # Stats
    pending_count = PaymentRequest.objects.filter(status='pending').count()
    approved_count = PaymentRequest.objects.filter(status='approved').count()
    declined_count = PaymentRequest.objects.filter(status='declined').count()
    
    context = {
        'requests': requests_page,
        'status_filter': status_filter,
        'search': search,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'declined_count': declined_count,
    }
    
    return render(request, 'bossin_admin/subscriptions/list.html', context)


@bossin_admin_required
@require_POST
def bossin_subscription_approve(request, request_id):
    """Approve a payment request."""
    pr = get_object_or_404(PaymentRequest, pk=request_id)
    
    if pr.status != 'pending':
        messages.error(request, 'This request has already been processed.')
        return redirect('bossin_admin:subscriptions')
    
    # Approve and extend subscription
    pr.status = 'approved'
    pr.save()
    
    # Update organization subscription
    org = pr.organization
    now = timezone.now()
    
    if pr.months and pr.months > 0:
        if org.subscription_expires_at and org.subscription_expires_at > now:
            # Extend existing subscription
            org.subscription_expires_at += timezone.timedelta(days=30 * pr.months)
        else:
            # New subscription
            org.subscription_expires_at = now + timezone.timedelta(days=30 * pr.months)
        
        org.subscription_status = 'SUBSCRIBED'
        org.save()
    
    messages.success(request, f'Payment request approved. Subscription extended for {pr.months} months.')
    return redirect('bossin_admin:subscriptions')


@bossin_admin_required
@require_POST
def bossin_subscription_decline(request, request_id):
    """Decline a payment request."""
    pr = get_object_or_404(PaymentRequest, pk=request_id)
    
    if pr.status != 'pending':
        messages.error(request, 'This request has already been processed.')
        return redirect('bossin_admin:subscriptions')
    
    pr.status = 'declined'
    pr.save()
    
    messages.success(request, 'Payment request declined.')
    return redirect('bossin_admin:subscriptions')


# ============================================================================
# BACKUP MANAGEMENT
# ============================================================================

@bossin_admin_required
def bossin_backups(request):
    """Backup management interface."""
    backup_dir = Path('backups')
    
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all backup files
    backup_files = []
    for backup_file in backup_dir.glob('db_backup_*.gz'):
        stat = backup_file.stat()
        backup_files.append({
            'name': backup_file.name,
            'path': str(backup_file),
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'created': timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone()),
            'age_days': (timezone.now() - timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())).days,
        })
    
    backup_files.sort(key=lambda x: x['created'], reverse=True)
    
    # Latest backup
    latest_backup = backup_files[0] if backup_files else None
    
    # System settings
    settings = SystemSettings.get_settings()
    
    context = {
        'backups': backup_files,
        'latest_backup': latest_backup,
        'backup_enabled': settings.backup_enabled,
        'retention_days': settings.backup_retention_days,
    }
    
    return render(request, 'bossin_admin/backups/manage.html', context)


@bossin_admin_required
@require_POST
def bossin_backup_create(request):
    """Trigger manual backup."""
    from django.core.management import call_command
    try:
        settings = SystemSettings.get_settings()
        call_command('backup_database', 
                    output_dir='backups',
                    keep_days=settings.backup_retention_days)
        messages.success(request, 'Backup created successfully!')
    except Exception as e:
        messages.error(request, f'Backup failed: {str(e)}')
    
    return redirect('bossin_admin:backups')


@bossin_admin_required
def bossin_backup_download(request):
    """Download backup file."""
    from django.http import FileResponse, Http404
    from pathlib import Path
    
    backup_file = request.GET.get('backup_file')
    if not backup_file:
        raise Http404('Backup file not specified')
    
    # Sanitize filename to prevent path traversal
    backup_file = Path(backup_file).name
    
    backup_path = Path('backups') / backup_file
    if not backup_path.exists():
        raise Http404('Backup file not found')
    
    response = FileResponse(
        open(backup_path, 'rb'),
        as_attachment=True,
        filename=backup_file
    )
    # FileResponse will close the file automatically when done
    return response


@bossin_admin_required
def bossin_backup_restore(request):
    """Restore from backup (GET request with confirmation)."""
    backup_path = request.GET.get('backup_path')
    if not backup_path:
        messages.error(request, 'No backup file specified.')
        return redirect('bossin_admin:backups')
    
    # Check if database is in use (Windows file locking issue)
    import sqlite3
    import platform
    db_path = Path(settings.DATABASES['default']['NAME'])
    
    # On Windows, SQLite files get locked more easily
    if platform.system() == 'Windows':
        try:
            # Try to open database in exclusive mode to check if it's locked
            test_conn = sqlite3.connect(db_path, timeout=0.1)
            test_conn.execute('BEGIN EXCLUSIVE')
            test_conn.rollback()
            test_conn.close()
        except (sqlite3.OperationalError, PermissionError) as e:
            error_msg = str(e).lower()
            if 'locked' in error_msg or 'being used' in error_msg or 'WinError 32' in str(e):
                messages.error(
                    request, 
                    '⚠️ Database is locked! Please STOP the Django server (Ctrl+C) before restoring. '
                    'Then run: python manage.py restore_database ' + backup_path
                )
                return redirect('bossin_admin:backups')
    
    from django.core.management import call_command
    try:
        call_command('restore_database', backup_path, no_input=True)
        messages.success(request, '✅ Database restored successfully! Please restart the server.')
    except Exception as e:
        error_str = str(e)
        if 'WinError 32' in error_str or 'being used' in error_str.lower():
            messages.error(
                request,
                '⚠️ Database file is locked. Please STOP the Django server (Ctrl+C) and run restore manually: '
                f'python manage.py restore_database {backup_path}'
            )
        else:
            messages.error(request, f'Restore failed: {error_str}')
    
    return redirect('bossin_admin:backups')


# ============================================================================
# THEMES & CATEGORIES MANAGEMENT
# ============================================================================

@bossin_admin_required
def bossin_themes(request):
    """Manage categories and default themes."""
    settings = SystemSettings.get_settings()
    
    # Get category choices from Organization model
    categories = Organization.CATEGORY_CHOICES
    
    context = {
        'settings': settings,
        'categories': categories,
        'category_discounts': settings.category_discounts,
    }
    
    return render(request, 'bossin_admin/themes/manage.html', context)


@bossin_admin_required
@require_POST
def bossin_themes_update(request):
    """Update category discounts and default themes."""
    settings = SystemSettings.get_settings()
    
    # Update category discounts
    category_discounts = {}
    for category, _ in Organization.CATEGORY_CHOICES:
        discount = request.POST.get(f'discount_{category}', '35')
        try:
            category_discounts[category] = int(discount)
        except ValueError:
            category_discounts[category] = 35
    
    settings.category_discounts = category_discounts
    settings.save()
    
    messages.success(request, 'Category discounts updated successfully!')
    return redirect('bossin_admin:themes')


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@bossin_admin_required
def bossin_users(request):
    """List and manage users."""
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.all()
    
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users.order_by('-date_joined'), 25)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    # Get organization memberships for each user
    for user in users_page:
        org_memberships = OrganizationUser.objects.filter(user=user).select_related('organization')
        user.org_count = org_memberships.count()
        user.org_names = ', '.join([om.organization.name for om in org_memberships[:3]])
        if org_memberships.count() > 3:
            user.org_names += f' (+{org_memberships.count() - 3} more)'
        user.is_org_owner = OrganizationUser.objects.filter(user=user, role='owner').exists()
    
    context = {
        'users': users_page,
        'search': search,
        'role_filter': role_filter,
    }
    
    return render(request, 'bossin_admin/users/list.html', context)


# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

@bossin_admin_required
def bossin_settings(request):
    """System settings management."""
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings
        settings.base_price_tzs = Decimal(request.POST.get('base_price_tzs', '19800.00'))
        settings.mpesa_number = request.POST.get('mpesa_number', '68256127')
        settings.mpesa_account_name = request.POST.get('mpesa_account_name', 'MIPT SOFTWARES')
        settings.support_email = request.POST.get('support_email', 'support@bossin.com')
        settings.support_phone = request.POST.get('support_phone', '')
        settings.backup_enabled = request.POST.get('backup_enabled') == 'on'
        settings.backup_retention_days = int(request.POST.get('backup_retention_days', '30'))
        settings.backup_location = request.POST.get('backup_location', 'backups')
        settings.save()
        
        messages.success(request, 'System settings updated successfully!')
        return redirect('bossin_admin:settings')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'bossin_admin/settings/edit.html', context)

