from decimal import Decimal, Context, Inexact
import pdb

from django import template


register = template.Library()

@register.filter
def sorted_items(value):
    return sorted(value.items())

@register.filter
def decimal_format(value, TWOPLACES=Decimal(10) ** -2 ):
    n = Decimal(str(value))
    n = n.quantize(TWOPLACES)#, context=Context(traps=[Inexact]))
    return n
        
