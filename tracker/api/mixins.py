"""API view mixins for tenant resolution and response helpers."""

from django.http import Http404

from tracker.api.utils import get_organization_by_slug, success_response, error_response
from tracker.api.exceptions import subscription_expired_response
from tracker.api.utils import check_subscription_active
from tracker.permissions import get_user_org_role


class TenantMixin:
    """
    Resolve organization from URL org_slug kwarg and attach to request.tenant.
    Also attaches request.org_membership with the user's role.
    """

    def initial(self, request, *args, **kwargs):
        org_slug = kwargs.get('org_slug')
        if org_slug:
            try:
                request.tenant = get_organization_by_slug(org_slug)
            except Exception:
                raise Http404('Organization not found or is inactive.')

            request.org_membership = None
            if request.user.is_authenticated:
                from tracker.models import OrganizationUser
                try:
                    request.org_membership = OrganizationUser.objects.get(
                        user=request.user,
                        organization=request.tenant,
                        is_active=True,
                    )
                except OrganizationUser.DoesNotExist:
                    request.org_membership = None
        else:
            request.tenant = None
            request.org_membership = None

        super().initial(request, *args, **kwargs)

    def get_organization(self):
        return getattr(self.request, 'tenant', None)

    def get_user_role(self):
        organization = self.get_organization()
        if not organization:
            return None
        return get_user_org_role(self.request.user, organization)


class APIResponseMixin:
    """Helpers for consistent API responses."""

    def api_success(self, data=None, status=200, meta=None):
        return success_response(data, status=status, meta=meta)

    def api_error(self, message, status=400, extra=None):
        return error_response(message, status=status, extra=extra)

    def check_subscription_or_respond(self):
        """Return 402 response if subscription expired (non-viewers)."""
        organization = self.get_organization()
        if not organization:
            return None

        role = self.get_user_role()
        if role == 'viewer':
            return None

        is_active, status_info = check_subscription_active(organization)
        if not is_active:
            return subscription_expired_response(status_info.get('error'))
        return None
