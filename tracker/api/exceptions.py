"""Custom API exception handling with consistent response envelope."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def api_exception_handler(exc, context):
    """Wrap DRF exceptions in a consistent {success, data, error} envelope."""
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data
        if isinstance(error_detail, dict):
            if 'detail' in error_detail:
                error_message = str(error_detail['detail'])
            else:
                error_message = error_detail
        else:
            error_message = str(error_detail)

        response.data = {
            'success': False,
            'data': None,
            'error': error_message,
        }
        return response

    return response


class SubscriptionExpiredError(Exception):
    """Raised when organization subscription/trial has expired."""

    def __init__(self, message='Subscription expired. Please renew to continue.'):
        self.message = message
        super().__init__(self.message)


def subscription_expired_response(message=None):
    return Response(
        {
            'success': False,
            'data': None,
            'error': message or 'Subscription expired. Please renew to continue.',
            'subscription_required': True,
        },
        status=status.HTTP_402_PAYMENT_REQUIRED,
    )
