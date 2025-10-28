"""
Custom template tags and filters for multi-tenant URL handling.
"""
from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag
def tenant_url(request, view_name, *args, **kwargs):
    """
    Generate a URL for a tenant-specific view.
    
    Usage in templates:
    {% tenant_url request 'tracker:dashboard' %}
    {% tenant_url request 'tracker:member_detail' member.id %}
    
    Automatically includes org_slug from request.tenant.
    """
    if not hasattr(request, 'tenant') or not request.tenant:
        return '#'
    
    # Add org_slug to kwargs
    kwargs['org_slug'] = request.tenant.slug
    
    try:
        return reverse(view_name, args=args, kwargs=kwargs)
    except Exception:
        return '#'


@register.filter
def tenant_url_filter(view_name, request):
    """
    Filter version of tenant_url for simple cases.
    
    Usage in templates:
    {{ 'tracker:dashboard'|tenant_url_filter:request }}
    """
    return tenant_url(request, view_name)


@register.simple_tag
def org_logo_url(request):
    """
    Get the organization logo URL.
    
    Usage in templates:
    <img src="{% org_logo_url request %}" />
    """
    if not hasattr(request, 'tenant') or not request.tenant:
        return ''
    
    try:
        theme = request.tenant.theme
        if theme.logo:
            return theme.logo.url
    except Exception:
        pass
    
    return ''


@register.simple_tag
def org_name(request):
    """
    Get the organization name.
    
    Usage in templates:
    <h1>{{ request|org_name }}</h1>
    """
    if not hasattr(request, 'tenant') or not request.tenant:
        return 'Mission Tracker'
    
    return request.tenant.name


@register.simple_tag
def org_primary_color(request):
    """
    Get the organization primary color.
    
    Usage in templates:
    <style>
        :root { --primary-color: {{ request|org_primary_color }}; }
    </style>
    """
    if not hasattr(request, 'tenant') or not request.tenant:
        return '#2563eb'
    
    try:
        theme = request.tenant.theme
        return theme.primary_color
    except Exception:
        return '#2563eb'
