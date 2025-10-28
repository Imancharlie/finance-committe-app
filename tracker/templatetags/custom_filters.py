from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def format_currency(value):
    """
    Format a number with thousand separators and TZS prefix.
    Example: 1000000 -> "TZS 1,000,000"
    """
    try:
        if value is None:
            return "TZS 0"
        
        # Convert to Decimal if it's a float or int
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        
        # Format with thousand separators
        formatted = "{:,.0f}".format(value)
        return f"TZS {formatted}"
    except (ValueError, TypeError):
        return "TZS 0"


@register.filter
def thousands_separator(value):
    """
    Add thousand separators to a number.
    Example: 1000000 -> "1,000,000"
    """
    try:
        if value is None:
            return "0"
        
        # Convert to Decimal if it's a float or int
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        elif isinstance(value, str):
            value = Decimal(value)
        
        # Format with thousand separators
        formatted = "{:,.0f}".format(value)
        return formatted
    except (ValueError, TypeError):
        return "0"


@register.filter
def currency_display(value):
    """
    Display currency with proper formatting.
    Example: 1000000 -> "1,000,000"
    """
    return thousands_separator(value)


@register.filter
def intcomma(value):
    """
    Convert a number to a string with commas every three digits (no decimals).
    Example: 1000000 -> "1,000,000"
    Example: 1000000.99 -> "1,000,000"
    """
    try:
        if value is None:
            return "0"
        
        # Convert to float first, then to int to remove decimals
        if isinstance(value, str):
            value = float(value)
        
        # Convert to int (removes all decimals)
        value = int(value)
        
        # Format with thousand separators
        return "{:,}".format(value)
    except (ValueError, TypeError):
        return "0"


@register.filter
def abs_value(value):
    """
    Return the absolute value of a number.
    Example: -1000 -> 1000
    Example: -1000.99 -> 1000
    """
    try:
        if value is None:
            return 0
        
        # Convert to float first
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, int):
            value = float(value)
        
        # Return absolute value as int
        return int(abs(value))
    except (ValueError, TypeError):
        return 0
