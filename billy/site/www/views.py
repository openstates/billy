import pdb
from functools import wraps
from itertools import repeat

from django.shortcuts import render, redirect
from django.template import RequestContext

from billy.models import *

from viewdata import overview
from forms import StateSelectForm

from django.core.urlresolvers import reverse

repeat1 = repeat(1)

def simplified(f):
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



@simplified
def state(request, abbr):
    '''
    ''' 
    metadata = Metadata.get(abbr)
    report = db.reports.find_one({'_id': abbr})

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
    form = StateSelectForm(request.GET)
    abbr = form.data['abbr']
    return redirect('state', abbr=abbr)


#----------------------------------------------------------------------------
def legislators(request, abbr):
    return redirect('legislators_chamber', abbr, 'upper')

@simplified
def legislators_chamber(request, abbr, chamber):
    
    state = Metadata.get(abbr)
    chamber_name = state['%s_chamber_name' % chamber]

    # Query params
    spec = {'chamber': chamber}

    fields = ['leg_id', 'full_name', 'photo_url', 'district', 'party']
    fields = dict(zip(fields, repeat1))

    sort_key = 'district'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])
        
    legislators = state.legislators(spec, fields=fields, sort=[(sort_key, sort_order)])

    # Sort in python if the key was "district"
    if sort_key == 'district':
        legislators = sorted(legislators, key=lambda obj: int(obj['district']),
                             reverse=(sort_order == -1))

    sort_order = {1: -1, -1: 1}[sort_order]

    return locals()


@simplified
def legislator(request, abbr, leg_id):
    '''
    Note - changes needed before we can display "sessions served" info.
    '''
    legislator = Legislator.get(_id=leg_id)
    sources = legislator['sources']
    return locals()
    

#----------------------------------------------------------------------------
def committees(request, abbr):
    return redirect('committees_chamber', abbr, 'upper')


@simplified
def committees_chamber(request, abbr, chamber):
    
    state = Metadata.get(abbr)
    chamber_name = state['%s_chamber_name' % chamber]

    # Query params
    spec = {'chamber': chamber}

    fields = ['committee', 'subcommittee', 'members']
    fields = dict(zip(fields, repeat1))

    sort_key = 'committee'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])
        
    committees = state.committees(spec, fields=fields, sort=[(sort_key, sort_order)])

    sort_order = {1: -1, -1: 1}[sort_order] 

    return locals()


@simplified
def committee(request, abbr, committee_id):
    committee = Committee.get(_id=committee_id)
    sources = committee['sources']
    return locals()

#----------------------------------------------------------------------------   
@simplified
def bills(request, abbr):
    state = Metadata.get(abbr)
    return locals()

@simplified
def bill(request, abbr, bill_id):
    state = Metadata.get(abbr)
    bill = Bill.get(_id=bill_id)
    sources = bill['sources']
    return locals()


#----------------------------------------------------------------------------   
@simplified
def votes(request, abbr):
    state = Metadata.get(abbr)
    return locals()

@simplified
def vote(request, abbr, bill_id, vote_index):
    state = Metadata.get(abbr)
    bill = Bill.get(_id=bill_id)
    sources = bill['sources']
    return locals()