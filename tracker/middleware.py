"""
Tenant middleware for multi-tenant support.
Resolves organization from URL slug and sets request.tenant.
"""
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from .models import Organization, OrganizationUser


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware to resolve the tenant organization from the URL slug.
    Sets request.tenant to the resolved Organization instance.

    URL pattern: /<org_slug>/...
    Example: /bossin-default/dashboard/
    """

    def process_request(self, request):
        """
        Extract org_slug from URL path and resolve to Organization.
        Skips global paths like /admin/, /login/, /accounts/, etc.
        """
        # Paths that don't require tenant resolution
        EXCLUDED_PATHS = [
            '/admin/',
            '/bossin-admin/',  # Bossin Admin Portal
            '/login/',
            '/signup/',
            '/terms/',
            '/accounts/',
            '/logout/',
            '/offline/',
            '/static/',
            '/media/',
        ]

        # Check if path is excluded
        path = request.path
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            request.tenant = None
            return

        # Get the path and split it
        path = request.path.strip('/')
        path_parts = path.split('/')

        # Extract org_slug (first part of path)
        if path_parts and path_parts[0]:
            org_slug = path_parts[0]

            try:
                # Resolve org_slug to Organization
                organization = Organization.objects.get(slug=org_slug, is_active=True)
                request.tenant = organization

                # Store in session for later use
                request.session['tenant_id'] = organization.id
                request.session['tenant_slug'] = organization.slug

            except Organization.DoesNotExist:
                # Organization not found or inactive
                request.tenant = None
                # Raise Http404 with a user-friendly message
                raise Http404(f"Organization '{org_slug}' not found or is inactive.")
        else:
            # No org_slug in URL
            request.tenant = None

    def process_response(self, request, response):
        """
        Ensure tenant is set on response context if available.
        """
        return response


class StaffOnboardingMiddleware(MiddlewareMixin):
    """
    Middleware to redirect staff users to complete onboarding on first login.
    """

    def process_request(self, request):
        """
        Check if authenticated user needs staff onboarding and redirect accordingly.
        """
        if not request.user.is_authenticated:
            return

        # Check if user needs staff onboarding
        if hasattr(request.user, 'userprofile') and request.user.userprofile.needs_onboarding:
            try:
                # Get the user's organization
                org_user = OrganizationUser.objects.filter(
                    user=request.user,
                    is_active=True,
                    role__in=['staff', 'admin']
                ).first()

                if org_user:
                    # Check if we're already on the onboarding page
                    current_path = request.path_info
                    onboarding_url = reverse('tracker:staff_onboarding', kwargs={'org_slug': org_user.organization.slug})

                    if current_path != onboarding_url:
                        # Redirect to onboarding page
                        return redirect(onboarding_url)

            except Exception:
                # If there's any error, continue normally
                pass


class SubscriptionEnforcementMiddleware(MiddlewareMixin):
    """
    If no active subscription and trial expired (>7 days), redirect to subscription page.
    Also auto-updates organization status when trial expires.
    Applies to org owner/admin/staff after login for tenant routes.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return
        if not hasattr(request, 'tenant') or not request.tenant:
            return

        # Exclude subscription and onboarding routes to avoid loops
        path = request.path
        if any(segment in path for segment in [
            '/onboarding/subscription/',
            '/subscription/',
            '/logout/',
            '/admin/login',
        ]):
            return

        # Check role
        try:
            org_user = OrganizationUser.objects.get(user=request.user, organization=request.tenant)
        except OrganizationUser.DoesNotExist:
            return

        if org_user.role not in ['owner', 'admin', 'staff']:
            return

        now = timezone.now()
        org = request.tenant
        
        # Auto-update subscription status if trial expired
        if org.subscription_status == 'FREE_TRIAL' and org.trial_started_at:
            trial_end = org.trial_started_at + timezone.timedelta(days=7)
            if trial_end <= now:
                # Trial expired - update status to NOT_SUBSCRIBED
                org.subscription_status = 'NOT_SUBSCRIBED'
                org.save(update_fields=['subscription_status'])
        
        # Auto-update subscription status if subscription expired
        if org.subscription_status == 'SUBSCRIBED' and org.subscription_expires_at:
            if org.subscription_expires_at <= now:
                # Subscription expired - update status to NOT_SUBSCRIBED
                org.subscription_status = 'NOT_SUBSCRIBED'
                org.save(update_fields=['subscription_status'])
        
        # Check if subscription is active (not expired)
        active_sub = bool(
            org.subscription_status == 'SUBSCRIBED' and 
            org.subscription_expires_at and 
            org.subscription_expires_at > now
        )
        
        # Check if trial is still active
        trial_active = bool(
            org.subscription_status == 'FREE_TRIAL' and
            org.trial_started_at and 
            (org.trial_started_at + timezone.timedelta(days=7) > now)
        )

        # Redirect to subscription renewal page if:
        # 1. Status is NOT_SUBSCRIBED, OR
        # 2. No active subscription and no active trial
        # Use subscription_renewal (not onboarding_subscription) for expired subscriptions
        if org.subscription_status == 'NOT_SUBSCRIBED' or (not active_sub and not trial_active):
            sub_url = reverse('tracker:subscription_renewal', kwargs={'org_slug': org.slug})
            if path != sub_url:
                return redirect(sub_url)
