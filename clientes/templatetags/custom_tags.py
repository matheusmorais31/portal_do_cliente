from django import template

register = template.Library()

@register.filter
def in_list(value, arg):
    """
    Verifica se um valor está presente em uma lista fornecida.
    Exemplo de uso: {{ value|in_list:"item1,item2,item3" }}
    """
    return value in arg.split(',')
