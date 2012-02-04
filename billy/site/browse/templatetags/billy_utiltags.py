from decimal import Decimal, Context, Inexact
import urllib
import pdb

from django import template

register = template.Library()

@register.filter
def sorted_items(value):
    return sorted(value.items())

@register.filter
def decimal_format(value, TWOPLACES=Decimal(100) ** -2 ):
    n = Decimal(str(value))
    n = n.quantize(TWOPLACES)#, context=Context(traps=[Inexact]))
    return n

@register.filter
def key(d, key_name):
    try:
        return d[key_name]
    except KeyError:
        return None

@register.filter
def private(d, key_name):
    try:
        return d[( "_" + key_name )]
    except KeyError:
        return None

quote_plus=register.filter(urllib.quote_plus)
