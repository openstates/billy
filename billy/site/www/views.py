from functools import wraps

from django.shortcuts import render_to_response
from django.template import RequestContext

from billy import db

from viewdata import overview


def simplify(f):
	'''
	Render the decorated view to response with the template
	bearing the same name as the view function. 
	'''
	@wraps(f)
	def wrapper(request, *args, **kwargs):
		dictionary = f(request, *args, **kwargs)
		template_name = f.__name__ + '.html'
		context_instance = RequestContext(request)
		return render_to_response(template_name, dictionary, context_instance)

	return wrapper



@simplify
def state(request, abbr):
	'''
	2-12-2012
	Per the wireframes/spec, this view needs:

	for each house
	- number of legislators
	- partisan breakdown
	- etc...
	current session overview
	- # active
	- # passed
	- etc...
	related links
	- session overview
	- legislators
	- bills
	- current session
	- committees
	'''
	metadata = db.metadata.find_one({'_id': abbr})
	report = db.reports.find_one({'_id': abbr})

	# Put this in a state wrapper class...
	session_details = metadata['session_details']
	sessions = [(k, session_details[k]['display_name']) 
	            for k in report['bills']['sessions']]

	#------------------------------------------------------------------------
	# Legislators
	chambers = {
		'lower': overview.chamber(abbr, 'lower'),
		'upper': overview.chamber(abbr, 'upper')
		}

	chambers['lower']['name'] = metadata['lower_chamber_name']
	chambers['upper']['name'] = metadata['upper_chamber_name']

	return locals()

