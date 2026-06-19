"""
Context processors for multi-tenant theming and permissions.
Injects organization, theme, and role data into all templates.
"""
from .permissions import (
    get_user_org_role, is_org_admin, is_org_staff, is_org_viewer, is_org_owner
)


def theme_context(request):
    """
    Inject theme, organization, and permission data into template context.
    
    Available in templates as:
    - {{ tenant }} - Organization instance
    - {{ theme }} - OrganizationTheme instance
    - {{ org_name }} - Organization name
    - {{ org_logo }} - Organization logo URL
    - {{ primary_color }} - Primary brand color
    - {{ secondary_color }} - Secondary color
    - {{ success_color }} - Success color
    - {{ warning_color }} - Warning color
    - {{ danger_color }} - Danger color
    - {{ navbar_title }} - Custom navbar title
    - {{ footer_text }} - Custom footer text
    - {{ watermark_text }} - Watermark text for reports
    - {{ default_pledge_amount }} - Default pledge amount for new members
    - {{ target_amount }} - Target collection amount
    
    Permission variables:
    - {{ user_role }} - User's role in organization (owner, admin, staff, viewer)
    - {{ is_org_owner }} - True if user is owner
    - {{ is_org_admin }} - True if user is admin or owner
    - {{ is_org_staff }} - True if user is staff or higher
    - {{ is_org_viewer }} - True if user is viewer (read-only)
    - {{ can_edit_org }} - True if user can edit organization (owner only)
    - {{ can_manage_staff }} - True if user can manage staff (admin or owner)
    - {{ can_edit_members }} - True if user can edit members (staff or higher)
    - {{ can_record_transactions }} - True if user can record transactions (staff or higher)
    - {{ can_access_admin }} - True if user can access admin dashboard (admin or owner)
    - {{ can_view_admin_log }} - True if user can view admin log (admin or owner)
    - {{ can_import_excel }} - True if user can import Excel (admin or owner)
    """
    context = {
        'tenant': None,
        'theme': None,
        'org_name': 'Mission Tracker',
        'org_logo': None,
        'navbar_title': 'Mission Tracker',
        'footer_text': '',
        'watermark_text': 'Bossin',
        'primary_color': '#7492B9',
        'secondary_color': '#64748b',
        'success_color': '#059669',
        'warning_color': '#d97706',
        'danger_color': '#dc2626',
        # Financial Settings
        'default_pledge_amount': 70000,
        'target_amount': 210000,
        # Permission variables
        'user_role': None,
        'is_org_owner': False,
        'is_org_admin': False,
        'is_org_staff': False,
        'is_org_viewer': False,
        'can_edit_org': False,
        'can_manage_staff': False,
        'can_edit_members': False,
        'can_record_transactions': False,
        'can_access_admin': False,
        'can_view_admin_log': False,
        'can_import_excel': False,
    }

    # If tenant is set in request, inject theme data
    if hasattr(request, 'tenant') and request.tenant:
        context['tenant'] = request.tenant
        context['org_name'] = request.tenant.name
        
        # Get or create theme
        try:
            theme = request.tenant.theme
            context['theme'] = theme
            context['org_logo'] = theme.logo.url if theme.logo else None
            context['navbar_title'] = theme.navbar_title or request.tenant.name
            context['footer_text'] = theme.footer_text
            context['watermark_text'] = theme.watermark_text
            context['primary_color'] = theme.primary_color
            context['secondary_color'] = theme.secondary_color
            context['success_color'] = theme.success_color
            context['warning_color'] = theme.warning_color
            context['danger_color'] = theme.danger_color
            context['default_pledge_amount'] = float(theme.default_pledge_amount)
            context['target_amount'] = float(theme.target_amount)
        except Exception:
            # Theme doesn't exist yet, use defaults
            pass
        
        # Add permission data if user is authenticated
        if request.user.is_authenticated:
            user_role = get_user_org_role(request.user, request.tenant)
            context['user_role'] = user_role
            context['is_org_owner'] = is_org_owner(request.user, request.tenant)
            context['is_org_admin'] = is_org_admin(request.user, request.tenant)
            context['is_org_staff'] = is_org_staff(request.user, request.tenant)
            context['is_org_viewer'] = is_org_viewer(request.user, request.tenant)
            # Permission flags for navbar and views
            context['can_edit_org'] = is_org_owner(request.user, request.tenant)
            context['can_manage_staff'] = is_org_admin(request.user, request.tenant)
            context['can_edit_members'] = is_org_staff(request.user, request.tenant)
            context['can_record_transactions'] = is_org_admin(request.user, request.tenant)  # Admin/Owner only
            context['can_access_admin'] = is_org_admin(request.user, request.tenant)
            context['can_view_admin_log'] = is_org_admin(request.user, request.tenant)
            context['can_import_excel'] = is_org_admin(request.user, request.tenant)

    return context
