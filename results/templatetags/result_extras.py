# results/templatetags/result_extras.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Safely get a dictionary item in templates."""
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
