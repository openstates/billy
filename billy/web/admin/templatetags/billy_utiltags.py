from decimal import Decimal
import urllib
import datetime as dt
from pprint import pformat

from django import template
from billy.core import settings

register = template.Library()


@register.filter
def sorted_items(value):
    return sorted(value.items())


@register.filter
def decimal_format(value, TWOPLACES=Decimal(100) ** -2):
    n = Decimal(str(value))
    n = n.quantize(TWOPLACES)
    return n


@register.filter
def key(d, key_name):
    try:
        return d[key_name]
    except KeyError:
        return None


@register.filter
def level(d):
    return d[settings.LEVEL_FIELD]


@register.filter
def minus(d1, d2):
    return d1 - d2


@register.filter
def private(d, key_name):
    try:
        return d[("_" + key_name)]
    except KeyError:
        return None


@register.filter
def date_display(d):
    formal_date = d.strftime("%a, %B %d")
    ago = dt.datetime.utcnow() - d
    ago_str = "%s days" % (ago.days)
    return "%s (%s ago)" % (formal_date, ago_str)

quote_plus = register.filter(urllib.quote_plus)
pformat = register.filter(pformat)
