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


@register.filter
def hw_param(value):
    """Render a hardware parameter that may be a scalar, list, or dict.

    Knowledge-base entries such as integration_time arrive as dicts like
    {"default": 100, "min": 1, "max": 10000, "unit": "ms"}; file-header
    values may be scalars or 2-element lists. This returns a short,
    template-safe display string in all three cases so the page never
    crashes on an unexpected shape.
    """
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, dict):
        unit = value.get("unit") or ""
        default = value.get("default")
        lo = value.get("min")
        hi = value.get("max")
        if default is not None:
            base = str(default)
        elif lo is not None and hi is not None:
            base = f"{lo}-{hi}"
        else:
            base = json.dumps(value, default=str)
        return f"{base} {unit}".strip()
    if isinstance(value, (list, tuple)):
        if len(value) >= 2:
            return f"{value[0]}-{value[1]}"
        if len(value) == 1:
            return str(value[0])
        return ""
    return str(value)
