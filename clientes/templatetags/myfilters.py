# clientes/templatetags/myfilters.py

from django import template

register = template.Library()

@register.filter(name='trim')
def trim_filter(value):
    if value is None:
        return ''
    return str(value).strip()
