from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Organization, OrganizationTheme, OrganizationUser, Member, Transaction, MemberEditLog, PaymentRequest


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "submitted_by", "months", "is_trial", "amount_tzs", "discount_percent", "status", "payment_method", "created_at")
    list_filter = ("status", "is_trial", "payment_method", "organization", "created_at")
    search_fields = ("organization__name", "submitted_by__username", "reference_note", "staff_comment")
    readonly_fields = ("created_at", "updated_at", "payment_summary")
    actions = ("approve_requests", "decline_requests")
    fieldsets = (
        ('Organization & Submitter', {
            'fields': ('organization', 'submitted_by')
        }),
        ('Payment Details', {
            'fields': ('months', 'is_trial', 'amount_tzs', 'amount_sent', 'discount_percent', 'category_snapshot', 'payment_method', 'reference_note')
        }),
        ('Status & Review', {
            'fields': ('status', 'staff_comment', 'payment_summary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def payment_summary(self, obj):
        """Display a summary of payment information"""
        summary_lines = []
        
        if obj.is_trial:
            summary_lines.append("Type: Free Trial (7 days)")
        else:
            summary_lines.append(f"Type: Paid Subscription ({obj.months} month(s))")
        
        summary_lines.append(f"Amount: {obj.amount_tzs:,.2f} TZS")
        
        if obj.discount_percent > 0:
            summary_lines.append(f"Discount: {obj.discount_percent}%")
        
        if obj.amount_sent:
            summary_lines.append(f"Amount Sent: {obj.amount_sent:,.2f} TZS")
        
        if obj.payment_method:
            summary_lines.append(f"Payment Method: {obj.get_payment_method_display()}")
        
        if obj.reference_note:
            summary_lines.append(f"Reference: {obj.reference_note}")
        
        if obj.status == 'approved' and obj.months > 0:
            org = obj.organization
            if org.subscription_expires_at:
                summary_lines.append(f"Organization subscription expires: {org.subscription_expires_at.strftime('%Y-%m-%d %H:%M')}")
        
        return format_html('<br>'.join(summary_lines))
    payment_summary.short_description = 'Payment Summary'

    def approve_requests(self, request, queryset):
        from django.db import transaction
        
        count = 0
        updated_orgs = []
        errors = []
        
        with transaction.atomic():
            for pr in queryset.filter(status='pending'):
                try:
                    # Update payment request status
                    pr.status = 'approved'
                    pr.save(update_fields=['status', 'updated_at'])
                    
                    # Extend subscription on organization
                    if pr.months and pr.months > 0:
                        # Get fresh organization instance from database with select_for_update to lock it
                        org = Organization.objects.select_for_update().get(pk=pr.organization.pk)
                        now = timezone.now()
                        
                        # Check if subscription is currently active (not expired)
                        subscription_active = org.subscription_expires_at and org.subscription_expires_at > now
                        
                        # Check if user is on free trial that hasn't expired (regardless of current status)
                        trial_active = False
                        remaining_trial_days = 0
                        if org.trial_started_at:
                            trial_end = org.trial_started_at + timezone.timedelta(days=7)
                            if trial_end > now:
                                trial_active = True
                                remaining_trial_days = (trial_end - now).days
                        
                        # Determine subscription start date and calculate expiration
                        # ALWAYS set expiration date - this is critical
                        if subscription_active:
                            # Already subscribed and not expired: extend from current expiration date
                            start = org.subscription_expires_at
                            new_expires_at = start + timezone.timedelta(days=30*pr.months)
                        elif trial_active:
                            # User is on free trial: add remaining trial days to subscription period
                            # Start from now and add remaining trial days + subscription months
                            total_days = remaining_trial_days + (30 * pr.months)
                            new_expires_at = now + timezone.timedelta(days=total_days)
                        else:
                            # Not subscribed, expired, or trial expired: start from now (approval time)
                            # This also handles the case where status is SUBSCRIBED but expiration is missing
                            new_expires_at = now + timezone.timedelta(days=30*pr.months)
                        
                        # Set the expiration date
                        org.subscription_expires_at = new_expires_at
                        
                        # Always update status to SUBSCRIBED when approving paid subscription
                        # This changes status from FREE_TRIAL to SUBSCRIBED if user subscribed during trial
                        org.subscription_status = 'SUBSCRIBED'
                        
                        # Save all fields to ensure everything is persisted
                        org.save()
                        
                        # Verify the save worked
                        org.refresh_from_db()
                        if org.subscription_status != 'SUBSCRIBED' or not org.subscription_expires_at:
                            errors.append(f"{org.name}: Save verification failed")
                        else:
                            # Track updated organizations for feedback
                            updated_orgs.append(f"{org.name} (expires: {org.subscription_expires_at.strftime('%Y-%m-%d %H:%M')})")
                            count += 1
                    elif pr.is_trial:
                        # Handle trial activation
                        # Get fresh organization instance from database with select_for_update
                        org = Organization.objects.select_for_update().get(pk=pr.organization.pk)
                        now = timezone.now()
                        # Only start trial if not already started or if trial has expired
                        trial_expired = False
                        if org.trial_started_at:
                            trial_end = org.trial_started_at + timezone.timedelta(days=7)
                            trial_expired = trial_end <= now
                        
                        if not org.trial_started_at or trial_expired:
                            org.trial_started_at = now
                            org.subscription_status = 'FREE_TRIAL'
                            org.save()
                            org.refresh_from_db()
                            count += 1
                except Exception as e:
                    errors.append(f"PaymentRequest {pr.id}: {str(e)}")
        
        # Build message
        if errors:
            msg = f"Approved {count} payment request(s). Errors: {'; '.join(errors)}"
            self.message_user(request, msg, level='warning')
        elif updated_orgs:
            msg = f"Approved {count} payment request(s). Updated: {', '.join(updated_orgs)}"
            self.message_user(request, msg, level='success')
        else:
            msg = f"Approved {count} payment request(s) and extended subscriptions where applicable."
            self.message_user(request, msg)
    approve_requests.short_description = "Approve selected requests and extend subscription"

    def decline_requests(self, request, queryset):
        updated = queryset.exclude(status='declined').update(status='declined')
        self.message_user(request, f"Declined {updated} payment request(s).")
    decline_requests.short_description = "Decline selected requests"


class CustomAdminMixin:
    """Mixin to add custom CSS to admin classes"""
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }


@admin.register(Organization)
class OrganizationAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'subscription_status', 'subscription_expires_display', 'is_active', 'member_count', 'created_at']
    list_filter = ['is_active', 'category', 'subscription_status', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at', 'subscription_info']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category', 'is_active')
        }),
        ('Subscription & Trial', {
            'fields': ('subscription_status', 'trial_started_at', 'subscription_expires_at', 'subscription_info'),
            'description': 'Manage organization subscription status and trial period.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def subscription_expires_display(self, obj):
        if obj.subscription_expires_at:
            now = timezone.now()
            if obj.subscription_expires_at > now:
                days_left = (obj.subscription_expires_at - now).days
                return format_html(
                    '<span style="color: green;">{}</span> ({} days left)',
                    obj.subscription_expires_at.strftime('%Y-%m-%d %H:%M'),
                    days_left
                )
            else:
                return format_html(
                    '<span style="color: red;">{}</span> (Expired)',
                    obj.subscription_expires_at.strftime('%Y-%m-%d %H:%M')
                )
        return format_html('<span style="color: gray;">—</span>')
    subscription_expires_display.short_description = 'Subscription Expires'
    
    def subscription_info(self, obj):
        """Display comprehensive subscription information"""
        info_lines = []
        now = timezone.now()
        
        # Show current status
        status_display = dict(obj.SUBSCRIPTION_STATUS_CHOICES).get(obj.subscription_status, obj.subscription_status)
        info_lines.append(f"<strong>Current Status:</strong> {status_display}")
        
        # Subscription info (if SUBSCRIBED)
        if obj.subscription_status == 'SUBSCRIBED':
            if obj.subscription_expires_at:
                if obj.subscription_expires_at > now:
                    days_left = (obj.subscription_expires_at - now).days
                    info_lines.append(f"<strong>Subscription active until:</strong> {obj.subscription_expires_at.strftime('%Y-%m-%d %H:%M')} ({days_left} days left)")
                else:
                    info_lines.append(f"<strong>Subscription expired:</strong> {obj.subscription_expires_at.strftime('%Y-%m-%d %H:%M')}")
            else:
                info_lines.append("<span style='color: red;'><strong>⚠ WARNING:</strong> Subscription expiration date not set!</span>")
                # Try to find the last approved payment request to calculate expiration
                from .models import PaymentRequest
                last_approved = PaymentRequest.objects.filter(
                    organization=obj, 
                    status='approved', 
                    is_trial=False
                ).order_by('-created_at').first()
                if last_approved:
                    estimated_expires = last_approved.created_at + timezone.timedelta(days=30*last_approved.months)
                    if estimated_expires > now:
                        info_lines.append(f"<span style='color: orange;'>Estimated expiration: {estimated_expires.strftime('%Y-%m-%d %H:%M')} (needs manual fix)</span>")
        
        # Trial info (only if status is FREE_TRIAL or if trial was active before subscription)
        if obj.trial_started_at:
            trial_end = obj.trial_started_at + timezone.timedelta(days=7)
            if obj.subscription_status == 'FREE_TRIAL':
                if trial_end > now:
                    days_left = (trial_end - now).days
                    info_lines.append(f"<strong>Trial started:</strong> {obj.trial_started_at.strftime('%Y-%m-%d %H:%M')}")
                    info_lines.append(f"<strong>Trial ends:</strong> {trial_end.strftime('%Y-%m-%d %H:%M')} ({days_left} days left)")
                else:
                    info_lines.append(f"<strong>Trial ended:</strong> {trial_end.strftime('%Y-%m-%d %H:%M')}")
            elif obj.subscription_status == 'SUBSCRIBED':
                # Show that trial was converted to subscription
                info_lines.append(f"<strong>Trial converted to subscription:</strong> Trial started {obj.trial_started_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Payment requests count
        from .models import PaymentRequest
        pending_count = PaymentRequest.objects.filter(organization=obj, status='pending').count()
        approved_count = PaymentRequest.objects.filter(organization=obj, status='approved', is_trial=False).count()
        
        if pending_count > 0:
            info_lines.append(f"<strong>Pending payment requests:</strong> {pending_count}")
        if approved_count > 0:
            info_lines.append(f"<strong>Approved payment requests:</strong> {approved_count}")
        
        if len(info_lines) == 1:  # Only status line
            return format_html('<br>'.join(info_lines))
        
        return format_html('<br>'.join(info_lines))
    subscription_info.short_description = 'Subscription Information'

    def member_count(self, obj):
        count = obj.members.count()
        return format_html('<span style="color: #2563eb; font-weight: bold;">{}</span>', count)
    member_count.short_description = 'Staff Members'


@admin.register(OrganizationTheme)
class OrganizationThemeAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['organization', 'primary_color_display', 'has_logo']
    list_filter = ['organization']
    search_fields = ['organization__name']
    readonly_fields = ['created_at', 'updated_at', 'color_preview']
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'navbar_title')
        }),
        ('Colors', {
            'fields': ('primary_color', 'secondary_color', 'success_color', 'warning_color', 'danger_color', 'color_preview')
        }),
        ('Text & Watermark', {
            'fields': ('footer_text', 'watermark_text')
        }),
        ('Financial Settings', {
            'fields': ('default_pledge_amount', 'target_amount'),
            'description': 'Customize the default pledge amount for new members and the organization\'s collection target.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def primary_color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; background-color: {}; border-radius: 3px; margin-right: 10px;"></span>{}',
            obj.primary_color,
            obj.primary_color
        )
    primary_color_display.short_description = 'Primary Color'

    def has_logo(self, obj):
        if obj.logo:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    has_logo.short_description = 'Has Logo'

    def color_preview(self, obj):
        colors = [
            ('Primary', obj.primary_color),
            ('Secondary', obj.secondary_color),
            ('Success', obj.success_color),
            ('Warning', obj.warning_color),
            ('Danger', obj.danger_color),
        ]
        html = '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
        for label, color in colors:
            html += f'<div style="text-align: center;"><div style="width: 50px; height: 50px; background-color: {color}; border-radius: 5px; border: 1px solid #ccc;"></div><small>{label}</small></div>'
        html += '</div>'
        return format_html(html)
    color_preview.short_description = 'Color Preview'


@admin.register(OrganizationUser)
class OrganizationUserAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'is_active', 'joined_at']
    list_filter = ['organization', 'role', 'is_active', 'joined_at']
    search_fields = ['user__username', 'organization__name']
    readonly_fields = ['joined_at', 'updated_at']
    fieldsets = (
        ('Membership', {
            'fields': ('organization', 'user', 'role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Member)
class MemberAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'organization', 'pledge', 'paid_total', 'remaining', 'status', 'phone', 'email']
    list_filter = ['organization', 'created_at', 'updated_at', 'is_active']
    search_fields = ['name', 'phone', 'email', 'course', 'organization__name']
    readonly_fields = ['paid_total', 'created_at', 'updated_at']
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Basic Information', {
            'fields': ('name', 'pledge', 'paid_total', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email'),
            'classes': ('collapse',)
        }),
        ('Academic Information', {
            'fields': ('course', 'year'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status(self, obj):
        if obj.is_complete:
            return format_html('<span style="color: green;">✓ Complete</span>')
        elif obj.is_incomplete:
            return format_html('<span style="color: orange;">⚠ Incomplete</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Started</span>')
    status.short_description = 'Status'

    def remaining(self, obj):
        return f"TZS {obj.remaining:,.2f}"
    remaining.short_description = 'Remaining'


@admin.register(Transaction)
class TransactionAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['member', 'organization', 'amount', 'date', 'added_by', 'note_preview']
    list_filter = ['organization', 'date', 'added_by', 'member']
    search_fields = ['member__name', 'note', 'organization__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Transaction Details', {
            'fields': ('member', 'amount', 'date', 'added_by', 'note')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def note_preview(self, obj):
        if obj.note:
            return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
        return '-'
    note_preview.short_description = 'Note'

    def amount(self, obj):
        return f"TZS {obj.amount:,.2f}"
    amount.short_description = 'Amount'
