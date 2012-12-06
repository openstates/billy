from decimal import Decimal
import re
import json
import urllib

from django import template
from django.utils.html import strip_tags

from billy.core import settings
from billy.web.public.forms import get_region_select_form
from billy.web.public.views.utils import templatename
from billy.web.public.views.favorites import is_favorite


register = template.Library()


@register.inclusion_tag(templatename('region_select_form'))
def region_select_form(abbr=None):
    return {'form': get_region_select_form({'abbr': abbr})}


@register.inclusion_tag(templatename('sources'))
def sources(obj):
    return {'sources': obj['sources']}


@register.filter
def plusfield(obj, key):
    return obj.get('+' + key)


@register.filter
def party_noun(party, count=1):
    try:
        details = settings.PARTY_DETAILS[party]
        if count == 1:
            # singular
            return details['noun']
        else:
            # try to get special plural, or add s to singular
            try:
                return details['plural_noun']
            except KeyError:
                return details['noun'] + 's'
    except KeyError:
        # if there's a KeyError just return the adjective with or without
        # pluralization
        if count == 1:
            return party
        else:
            return party + 's'


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


@register.inclusion_tag(templatename('_favorite'), takes_context=True)
def favorite(context, obj_id, obj_type, abbr=None, _is_favorite=None,
             params=None):
    '''Check whether the object with the given type and id is currently
    favorited by the user. The test whether the user is authenticated
    currently happens in the template.

    abbr is can be specified in the invocation, since it won't be in the
    request context on the user's favorites page.

    Same for _is_favorite, which needs to be True.

    Same for params, which needs to be passed as a url-encoded string from
    the user homepage.
    '''
    request = context['request']
    extra_spec = {}

    # If the requested page is a search results page with a query string,
    # create an extra spec to help determine whether the search is
    # currently favorited.
    if request.GET and obj_type == "search":
        extra_spec.update(search_text=request.GET['search_text'])
    if _is_favorite is None:
        _is_favorite = is_favorite(obj_id, obj_type, request.user,
                                   extra_spec=extra_spec)
    else:
        _is_favorite = (_is_favorite == 'is_favorite')

    # We need to allow the abbr to be passed in from the user favorites page,
    # to come from the request context in the case of a search results page,
    # and to default to 'all' for the all bills search.
    abbr = abbr or context.get('abbr', 'all')

    return dict(extra_spec,
                obj_type=obj_type, obj_id=obj_id,
                is_favorite=_is_favorite, request=request,
                abbr=abbr or context['abbr'],
                params=params or urllib.urlencode(request.GET))


@register.inclusion_tag(templatename('_notification_preference'))
def notification_preference(obj_type, profile):
    '''Display two radio buttons for turning notifications on or off.
    The default value is is have alerts_on = True.
    '''
    default_alert_value = True
    if not profile:
        alerts_on = True
    else:
        notifications = profile.get('notifications', {})
        alerts_on = notifications.get(obj_type, default_alert_value)
    return dict(alerts_on=alerts_on, obj_type=obj_type)


@register.filter
def json_encode(data):
    return json.dumps(data)
