# clientes/templatetags/pedido_extras.py

from django import template

register = template.Library()

@register.filter
def pluck(list_of_dicts, key):
    """Extrai o valor de 'key' de cada dicionário em uma lista."""
    try:
        return [d.get(key, '') for d in list_of_dicts if isinstance(d, dict)]
    except Exception:
        return []

@register.filter
def unique(value):
    """Retorna os itens únicos mantendo a ordem."""
    seen = set()
    result = []
    for item in value:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result

@register.filter
def exclude(value, arg):
    """Exclui da lista os itens que são iguais a 'arg'."""
    try:
        return [item for item in value if item != arg]
    except Exception:
        return value
