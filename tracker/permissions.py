"""
Permission utilities and decorators for multi-tenant role-based access control.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from .models import OrganizationUser


def get_user_org_role(user, organization):
    """
    Get the role of a user in an organization.
    Returns: 'owner', 'admin', 'staff', 'viewer', or None if not a member.
    """
    try:
        org_user = OrganizationUser.objects.get(
            user=user,
            organization=organization,
            is_active=True
        )
        return org_user.role
    except OrganizationUser.DoesNotExist:
        return None


def is_org_owner(user, organization):
    """Check if user is owner of organization."""
    role = get_user_org_role(user, organization)
    return role == 'owner'


def is_org_admin(user, organization):
    """Check if user is admin or owner of organization."""
    role = get_user_org_role(user, organization)
    return role in ['owner', 'admin']


def is_org_staff(user, organization):
    """Check if user is staff, admin, or owner of organization."""
    role = get_user_org_role(user, organization)
    return role in ['owner', 'admin', 'staff']


def is_org_member(user, organization):
    """Check if user is any member of organization."""
    role = get_user_org_role(user, organization)
    return role is not None


def is_org_viewer(user, organization):
    """Check if user is viewer (read-only access)."""
    role = get_user_org_role(user, organization)
    return role == 'viewer'


def can_edit_organization(user, organization):
    """Check if user can edit organization (admin or owner only)."""
    return is_org_admin(user, organization)


def can_manage_staff(user, organization):
    """Check if user can manage staff (admin or owner only)."""
    return is_org_admin(user, organization)


def can_edit_members(user, organization):
    """Check if user can edit members (staff or higher)."""
    return is_org_staff(user, organization)


def can_record_transactions(user, organization):
    """Check if user can record transactions (admin or owner only)."""
    return is_org_admin(user, organization)


# ============================================================================
# DECORATORS
# ============================================================================

def tenant_required(view_func):
    """
    Decorator to ensure request.tenant is set.
    Redirects to 404 if tenant is not found.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            return HttpResponseForbidden("Organization not found.")
        return view_func(request, *args, **kwargs)
    return wrapper


def org_member_required(view_func):
    """
    Decorator to ensure user is a member of the organization.
    Requires @login_required and @tenant_required first.
    """
    @wraps(view_func)
    @login_required
    @tenant_required
    def wrapper(request, *args, **kwargs):
        if not is_org_member(request.user, request.tenant):
            return HttpResponseForbidden("You are not a member of this organization.")
        return view_func(request, *args, **kwargs)
    return wrapper


def org_staff_required(view_func):
    """
    Decorator to ensure user is staff or higher in the organization.
    Requires @login_required and @tenant_required first.
    """
    @wraps(view_func)
    @login_required
    @tenant_required
    def wrapper(request, *args, **kwargs):
        if not is_org_staff(request.user, request.tenant):
            return HttpResponseForbidden("You do not have permission to perform this action.")
        return view_func(request, *args, **kwargs)
    return wrapper


def org_admin_required(view_func):
    """
    Decorator to ensure user is admin or owner of the organization.
    Requires @login_required and @tenant_required first.
    """
    @wraps(view_func)
    @login_required
    @tenant_required
    def wrapper(request, *args, **kwargs):
        if not is_org_admin(request.user, request.tenant):
            return HttpResponseForbidden("You do not have admin permissions for this organization.")
        return view_func(request, *args, **kwargs)
    return wrapper


def org_owner_required(view_func):
    """
    Decorator to ensure user is owner of the organization.
    Requires @login_required and @tenant_required first.
    """
    @wraps(view_func)
    @login_required
    @tenant_required
    def wrapper(request, *args, **kwargs):
        if not is_org_owner(request.user, request.tenant):
            return HttpResponseForbidden("Only organization owners can perform this action.")
        return view_func(request, *args, **kwargs)
    return wrapper
