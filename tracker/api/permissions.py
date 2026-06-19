"""DRF permission classes mapped from tracker.permissions."""

from rest_framework.permissions import BasePermission, AllowAny

from tracker.permissions import (
    get_user_org_role,
    is_org_member,
    is_org_staff,
    is_org_admin,
    is_org_owner,
    can_record_transactions,
)
from tracker.api.utils import check_subscription_active
from tracker.api.exceptions import subscription_expired_response


class IsOrgMember(BasePermission):
    """User must be an active member of the organization."""

    message = 'You are not a member of this organization.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return is_org_member(request.user, organization)


class IsOrgStaff(BasePermission):
    """User must be staff, admin, or owner."""

    message = 'You do not have staff permissions for this organization.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return is_org_staff(request.user, organization)


class IsOrgAdmin(BasePermission):
    """User must be admin or owner."""

    message = 'You do not have admin permissions for this organization.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return is_org_admin(request.user, organization)


class IsOrgOwner(BasePermission):
    """User must be organization owner."""

    message = 'Only organization owners can perform this action.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return is_org_owner(request.user, organization)


class CanRecordTransactions(BasePermission):
    """User can record transactions (admin or owner)."""

    message = 'You do not have permission to record transactions.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return can_record_transactions(request.user, organization)


class IsOrgViewerOrHigher(BasePermission):
    """Any org member including viewer (read-only role still has access)."""

    message = 'You are not a member of this organization.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        return get_user_org_role(request.user, organization) is not None


class ReadOnlyForViewer(BasePermission):
    """Viewers can only use safe (read) methods."""

    message = 'Viewers have read-only access.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return False
        role = get_user_org_role(request.user, organization)
        if role is None:
            return False
        if role == 'viewer' and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return False
        return True


class SubscriptionActive(BasePermission):
    """
    Organization must have active subscription or trial.
    Viewers are exempt from subscription enforcement.
    """

    message = 'Subscription expired. Please renew to continue.'

    def has_permission(self, request, view):
        organization = getattr(request, 'tenant', None)
        if not organization:
            return True

        role = get_user_org_role(request.user, organization)
        if role == 'viewer':
            return True

        is_active, _ = check_subscription_active(organization)
        return is_active


class AllowAnyPublic(BasePermission):
    """Explicit allow-any for public endpoints."""

    def has_permission(self, request, view):
        return True
