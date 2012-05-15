import re
import operator
from functools import wraps
from itertools import repeat, islice

import pymongo

from django.shortcuts import render, redirect, render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView

import billy.models
from billy.models import db, Metadata
from billy.models.pagination import CursorPaginator, IteratorPaginator

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


class ListViewBase(TemplateView):
    'Base class for VoteList, FeedList, etc.'
    template_name = templatename('object_list')

    def get_context_data(self, *args, **kwargs):
        super(ListViewBase, self).get_context_data(*args, **kwargs)
        context = {}
        context.update(**default_context)
        context.update(column_headers=self.column_headers,
                       rowtemplate_name=self.rowtemplate_name,
                       object_list=self.get_queryset(),
                       statenav_active=self.statenav_active,
                       abbr=self.kwargs['abbr'],
                       url=self.request.path,
                       use_table=getattr(self, 'use_table', False))
        return context

    def get_queryset(self, *args, **kwargs):
        collection_name = self.kwargs.get('collection_name')
        collection_name = {
            'state': 'metadata',
            }.get(collection_name, collection_name)
        _id = self.kwargs.get('id')

        get = self.request.GET.get
        show_per_page = int(get('show_per_page', 20))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100
        collection = getattr(billy.models.db, collection_name)
        obj = collection.find_one(_id)
        objects = getattr(obj, self.query_attr)
        if callable(objects):
            objects = objects()
        sort_func = getattr(self, 'sort_func', None)
        sort_reversed = bool(getattr(self, 'sort_reversed', None))
        if sort_func:
            objects = sorted(objects, key=sort_func,
                             reverse=sort_reversed)
        paginator = self.paginator(objects, page=page,
                                   show_per_page=show_per_page)
        return paginator


class VotesList(ListViewBase):

    list_item_context_name = 'vote'
    sort_func = operator.itemgetter('date')
    sort_reversed = True
    paginator = IteratorPaginator
    query_attr = 'votes_manager'
    use_table = True

    rowtemplate_name = templatename('votes_list_row')
    column_headers = ('Bill', 'Date', 'Outcome', 'Yes',
                      'No', 'Other', 'Motion')
    statenav_active = 'bills'


class FeedsList(ListViewBase):

    list_item_context_name = 'entry'
    paginator = CursorPaginator
    query_attr = 'feed_entries'

    rowtemplate_name = templatename('feed_entry')
    column_headers = ('feeds',)  # ('date', 'title', 'author', 'host',
                      #'summary', 'tags')
    statenav_active = 'bills'


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
            vote_preview_row_template=templatename('vote_preview_row'),
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


def committees_chamber(request, abbr, chamber):

    state = Metadata.get_object(abbr)

    # Query params
    spec = {'chamber': chamber}

    fields = ['committee', 'subcommittee', 'members']
    fields = dict(zip(fields, repeat1))

    sort_key = 'committee'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])

    committees = state.committees(spec, fields=fields,
                                  sort=[(sort_key, sort_order)])

    sort_order = {1: -1, -1: 1}[sort_order]
    return render_to_response(
        template_name=templatename('committees_chamber'),
        dictionary=dict(
            committees=committees,
            abbr=abbr,
            metadata=Metadata.get_object(abbr),
            committees_table_template=templatename('committees_table'),
            sort_order=sort_order,
            statenav_active='committees'),
        context_instance=RequestContext(request, default_context))


def committee(request, abbr, committee_id):
    committee = db.committees.find_one({'_id': committee_id})
    return render_to_response(
        template_name=templatename('committee'),
        dictionary=dict(
            committee=committee,
            abbr=abbr,
            metadata=Metadata.get_object(abbr),
            sources=committee['sources'],
            statenav_active='committees'),
        context_instance=RequestContext(request, default_context))


def bills(request, abbr):
    return render_to_response(
        template_name=templatename('bills'),
        dictionary=dict(
            committee=committee,
            abbr=abbr,
            metadata=Metadata.get_object(abbr),
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))


def bill(request, abbr, bill_id):
    bill = db.bills.find_one({'_id': bill_id})
    return render_to_response(
        template_name=templatename('bill'),
        dictionary=dict(
            vote_preview_row_template=templatename('vote_preview_row'),
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            first_five=bill.sponsors_manager.first_five(),
            sources=bill['sources'],
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))


def vote(request, abbr, bill_id, vote_index):
    bill = db.bills.find_one({'_id': bill_id})
    return render_to_response(
        template_name=templatename('vote_test'),
        dictionary=dict(
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            vote=nth(bill.votes_manager, int(vote_index)),
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))
