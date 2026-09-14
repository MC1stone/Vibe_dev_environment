"""Custom template filters for the analysis app."""

import json

from django import template
from django.template.defaultfilters import filesizeformat

register = template.Library()


@register.filter
def div(value, arg):
    """Divide value by arg."""
    try:
        return float(value) / float(arg)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.filter
def mul(value, arg):
    """Multiply value by arg."""
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0


@register.filter
def filesize(value):
    """Format a byte count as a human-readable file size."""
    try:
        return filesizeformat(value)
    except (TypeError, ValueError):
        return value


@register.filter
def parse_json(value):
    """Parse a JSON string into a Python object for template traversal."""
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return {}
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
