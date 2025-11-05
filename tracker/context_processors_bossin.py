"""
Context processor for Bossin Admin Portal.
Provides common context variables to all admin portal templates.
"""
from .models import PaymentRequest


def bossin_admin_context(request):
    """
    Add common context variables for Bossin Admin Portal.
    """
    context = {}
    
    # Only add context if user is superuser (for admin portal)
    if request.user.is_authenticated and request.user.is_superuser:
        # Get pending requests count for navbar badge
        context['pending_requests_count'] = PaymentRequest.objects.filter(status='pending').count()
    
    return context

