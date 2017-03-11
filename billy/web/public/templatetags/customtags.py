from decimal import Decimal
import re
import json
import urllib

from django import template
from django.utils.html import strip_tags

import pytz

from billy.core import settings
from billy.web.public.forms import get_region_select_form
from billy.web.public.views.utils import templatename


register = template.Library()


@register.inclusion_tag(templatename('region_select_form'))
def region_select_form(abbr=None):
    return {'form': get_region_select_form({'abbr': abbr})}


@register.inclusion_tag(templatename('sources'))
def sources(obj):
    return {'sources': obj['sources']}


@register.filter
def sources_urlize(url):
    '''Django's urlize built-in template tag does a lot of other things,
    like linking domain-only links, but it won't hyperlink ftp links,
    so this is a more liberal replacement for source links.
    '''
    return '<a href="%s" rel="nofollow">%s</a>' % (url, url)


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


@register.filter
def event_time(event):
    tz = pytz.timezone(event['timezone'])
    localized = tz.localize(event['when'])

    display_time = (localized + localized.utcoffset())
    hours, minutes = display_time.hour, display_time.minute

    # If the event's time is midnight, there was probably no
    # exact time listed on the site, so don't display likely bogus time.
    if (hours, minutes) == (0, 0):
        return display_time.strftime('%A, %B %d, %Y')

    return display_time.strftime('%A, %B %d, %Y, %I:%M %p %Z')
