from operator import itemgetter

from django import template

from billy import db
from billy.site.www.forms import StateSelectForm

from billy.models import Metadata

register = template.Library()


@register.inclusion_tag('billy/www/sitebase/states_selection.html')
def states_selection():
    form = StateSelectForm
    return locals()

@register.inclusion_tag('billy/www/sitebase/states_sidebar.html')
def states_sidebar(abbr):
    return locals()

