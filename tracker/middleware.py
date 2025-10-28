"""
Tenant middleware for multi-tenant support.
Resolves organization from URL slug and sets request.tenant.
"""
from django.utils.deprecation import MiddlewareMixin
from django.http import Http404
from .models import Organization


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
            '/login/',
            '/signup/',
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
