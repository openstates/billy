import re
import pdb
from functools import wraps
from itertools import repeat, islice

import pymongo

from django.views.generic.base import TemplateView
from django.shortcuts import render, redirect, render_to_response
from django.template import RequestContext, loader
from django.core.urlresolvers import reverse

from billy.models import db, Bill, Metadata, Legislator, Committee

from .context_processors import default_processor
from .forms import StateSelectForm
from .viewdata import overview


default_context = dict(base_template='billy/web/public/base.html')

def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)

repeat1 = repeat(1)
def include_fields(*field_names):
    return zip(field_names, repeat1)

def templatename(name):
    return 'billy/web/public/%s.html' % name

def simplified(f):
    '''Render the decorated view to response with the template
    bearing the same name as the view function.
    '''
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        dictionary = f(request, *args, **kwargs)
        dictionary['base_template'] = 'billy/web/public/base.html'
        template = 'billy/web/public/%s.html' % f.__name__
        return render(request, template, dictionary)

    return wrapper

def state_nav(active_collection):
    'Produce data for the state navigation bar.'
    collections = ('legislators', 'bills', 'committees',)
    return ((active_collection == c, c) for c in collections)


def state(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    meta = Metadata.get_object(abbr)

    # Image id.
    img_id = meta['name']
    if ' ' in img_id:
        img_id = meta['name'].split()
        img_id = img_id[0].lower() + ''.join(img_id[1:])

    return render_to_response(
        template_name=templatename('state'),
        dictionary=dict(abbr=abbr,
            state_image_id=img_id,
            metadata=meta,
            sessions=report.session_link_data(),
            lower=overview.chamber(abbr, 'lower'),
            upper=overview.chamber(abbr, 'upper'),
            recent_actions=overview.recent_actions(abbr),
            statenav_active=None),
        context_instance=RequestContext(request, default_context))

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


def legislators_chamber(request, abbr, chamber):

    state = Metadata.get_object(abbr)
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

    legislators = state.legislators(extra_spec=spec, fields=fields,
                                    sort=[(sort_key, sort_order)])

    # Sort in python if the key was "district"
    if sort_key == 'district':
        def sorter(obj):
            matchobj = re.search(r'\d+', obj['district'])
            if matchobj:
                return int(matchobj.group())
            else:
                return obj['district']

        legislators = sorted(legislators, key=sorter,
                             reverse=(sort_order == -1))

    sort_order = {1: -1, -1: 1}[sort_order]

    legislators = list(legislators)
    # import pdb;pdb.set_trace()
    return render_to_response(
        template_name=templatename('legislators_chamber'),
        dictionary=dict(
            state=state,
            chamber_name=chamber_name,
            abbr=abbr,
            legislators=legislators,
            sort_order=sort_order,
            sort_key=sort_key,
            legislator_table=templatename('legislator_table'),
            statenav_active='legislators'),
        context_instance=RequestContext(request, default_context))


def legislator(request, abbr, leg_id):
    '''
    Note - changes needed before we can display "sessions served" info.
    '''
    legislator = db.legislators.find_one({'_id': leg_id})
    roles = list(legislator.roles_manager)

    # Note to self: Slow query
    sponsored_bills = legislator.sponsored_bills(
        limit=5, sort=[('actions.1.date', pymongo.DESCENDING)])

    # Note to self: Another slow query
    legislator_votes = legislator.votes_3_sorted()
    has_votes = bool(legislator_votes)
    return render_to_response(
        template_name=templatename('legislator'),
        dictionary=dict(
            feed_entry_template=templatename('feed_entry'),
            roles=legislator.roles_manager,
            abbr=abbr,
            metadata=Metadata.get_object(abbr),
            legislator=legislator,
            sources=legislator['sources'],
            sponsored_bills=sponsored_bills,
            legislator_votes=legislator_votes,
            has_votes=has_votes,
            statenav_active='legislators'),
        context_instance=RequestContext(request, default_context))


#----------------------------------------------------------------------------
def committees(request, abbr):
    return redirect('committees_chamber', abbr, 'upper')


@simplified
def committees_chamber(request, abbr, chamber):

    state = Metadata.get_object(abbr)
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
    committee = db.committees.find_one({'_id': committee_id})
    sources = committee['sources']
    return locals()

#----------------------------------------------------------------------------
@simplified
def bills(request, abbr):
    state = Metadata.get_object(abbr)
    return locals()

@simplified
def bill(request, abbr, bill_id):
    state = Metadata.get_object(abbr)
    bill = db.bills.find_one({'_id': bill_id})
    sponsors = list(bill.sponsors_manager)
    first_five = bill.sponsors_manager.first_five()
    sources = bill['sources']
    return locals()


#----------------------------------------------------------------------------
@simplified
def votes(request, abbr):
    state = Metadata.get_object(abbr)
    return locals()


def vote(request, abbr, bill_id, vote_index):
    bill = db.bills.find_one({'_id': bill_id})
    return render_to_response(
        template_name=templatename('vote'),
        dictionary=dict(
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            vote=nth(bill.votes_manager, int(vote_index)),
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))