from django import template

register = template.Library()

@register.filter
def sorted_items(value):
    return sorted(value.items())

