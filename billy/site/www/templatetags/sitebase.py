from operator import itemgetter

from django import template

from billy import db

register = template.Library()

_id = itemgetter('_id')

@register.inclusion_tag('sitebase/states_sidebar.html')
def states_sidebar():
	return {'states': map(_id, db.metadata.find({}, {'_id'}))}