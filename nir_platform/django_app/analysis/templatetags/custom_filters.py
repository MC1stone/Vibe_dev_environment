"""
Custom template filters for NIR Intelligence Platform
"""

from django import template

register = template.Library()


@register.filter
def replace(value, arg):
    """
    Custom replace filter that works like |replace:'old','new'
    Usage: {{ value|replace:'old,new' }}
    """
    try:
        old, new = arg.split(',')
        return value.replace(old.strip(), new.strip())
    except ValueError:
        return value
