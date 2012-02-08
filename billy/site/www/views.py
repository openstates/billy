import pdb
from functools import wraps

from django.shortcuts import render, redirect
from django.template import RequestContext

from billy.models import *

from viewdata import overview
from forms import StateSelectForm


def simplify(f):
	'''
	Render the decorated view to response with the template
	bearing the same name as the view function. 
	'''
	@wraps(f)
	def wrapper(request, *args, **kwargs):
		dictionary = f(request, *args, **kwargs)
		template = f.__name__ + '.html'
		return render(request, template, dictionary)

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
	metadata = Metadata.get(abbr)
	report = db.reports.find_one({'_id': abbr})

	# Put this in a state wrapper class...
	
	sessions = report.session_link_data

	            
	#------------------------------------------------------------------------
	# Legislators
	chambers = {
		'lower': overview.chamber(abbr, 'lower'),
		'upper': overview.chamber(abbr, 'upper')
		}

	chambers['lower']['name'] = metadata['lower_chamber_name']
	chambers['upper']['name'] = metadata['upper_chamber_name']

	return locals()


def state_selection(request):
	'''
	Handle the "state" dropdown form at the top of the page.
	'''
	form = StateSelectForm(request.POST)
	abbr = form.data['abbr']
	return redirect('/www/%s/' % abbr)




@simplify
def legislators(request, abbr):
	state = Metadata.get(abbr)
	return locals()


@simplify
def committees(request, abbr):
	state = Metadata.get(abbr)
	return locals()


@simplify
def bills(request, abbr):
	state = Metadata.get(abbr)
	return locals()
