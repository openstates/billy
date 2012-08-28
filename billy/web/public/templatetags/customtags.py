from decimal import Decimal
import re

from django import template
from django.utils.html import strip_tags

from billy.web.public.views.utils import templatename
from billy.web.public.forms import get_state_select_form


register = template.Library()


@register.inclusion_tag(templatename('state_select_form'))
def state_select_form(abbr=None):
    return {'form':  get_state_select_form({'abbr': abbr})}


@register.inclusion_tag(templatename('sources'))
def sources(obj):
    return {'sources': obj['sources']}


@register.filter
def plusfield(obj, key):
    return obj.get('+' + key)


@register.filter
def trunc(string):
    if len(string) > 75:
        return "%s [...]" % string[:75]
    else:
        return string


@register.filter
def underscore_field(obj, key):
    return obj['_' + key]


@register.filter
def decimal_format(value, TWOPLACES=Decimal(100) ** -2):
    'Format a decimal.Decimal like to 2 decimal places.'
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWOPLACES)


@register.tag
def striptags(parser, token):
    nodelist = parser.parse(('end_striptags',))
    parser.delete_first_token()
    return StrippedTagsNode(nodelist)


@register.filter
def is_dev(luser):
    return len(luser.groups.filter(name='developer')) == 1


class StrippedTagsNode(template.Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = strip_tags(self.nodelist.render(context))
        return output


@register.tag
def squish_whitespace(parser, token):
    nodelist = parser.parse(('end_squish_whitespace',))
    parser.delete_first_token()
    return SquishedWhitespaceNode(nodelist)


class SquishedWhitespaceNode(template.Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = re.sub(u'\s+', ' ', self.nodelist.render(context))
        output = re.sub(u'\n\s+', '', self.nodelist.render(context))
        return output
