# Analysis app for NIR Intelligence Platform

from django import template

# Register custom template filters
register = template.Library()

@register.filter
def replace(value, arg):
    """Custom replace filter that mimics the behavior of |replace:'old','new'"""
    old, new = arg.split(',')
    return value.replace(old.strip(), new.strip())
