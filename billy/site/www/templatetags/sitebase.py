from operator import itemgetter

from django import template

from billy import db
from billy.site.www.forms import StateSelectForm

from billy.models import Metadata

register = template.Library()


@register.inclusion_tag('sitebase/states_selection.html', takes_context=True)
def states_selection(context):
	'''
	This awkwardness with the context param is necessary to satisfy django'satisfy
	CSRF middleware, since this inclusion tag renders a form that POSTs to an 
	internal url. Explaination here:
	http://squeeville.com/2009/01/27/django-templatetag-requestcontext-and-inclusion_tag/
	'''
	return {'form': StateSelectForm,
			'request': context['request']}



@register.inclusion_tag('sitebase/states_sidebar.html')
def states_sidebar(abbr):
	return locals()

