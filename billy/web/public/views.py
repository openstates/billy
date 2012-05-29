import re
import operator

from operator import itemgetter
from itertools import repeat, islice

import pymongo

from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView
from django.http import Http404
from django.conf import settings

import requests

import billy.models
from billy.models import db, Metadata, DoesNotExist
from billy.models.pagination import CursorPaginator, IteratorPaginator

from .forms import get_state_select_form, ChamberSelectForm, FindYourLegislatorForm
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


def sort_by_district(obj):
        matchobj = re.search(r'\d+', obj['district'])
        if matchobj:
            return int(matchobj.group())
        else:
            return obj['district']


def state_not_active_yet(request, args, kwargs):
    return render_to_response(
        template_name=templatename('state_not_active_yet'),
        dictionary=dict(
            metadata=Metadata.get_object(kwargs['abbr']),
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def homepage(request):
    return render_to_response(
        template_name=templatename('homepage'),
        dictionary=dict(
            active_states=map(Metadata.get_object, settings.ACTIVE_STATES),
            second_last=len(settings.ACTIVE_STATES) - 1,
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


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

        # Setup the paginator arguments.
        show_per_page = int(get('show_per_page', 20))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        # Get the related object.
        collection = getattr(billy.models.db, collection_name)

        try:
            obj = collection.find_one(_id)
        except DoesNotExist:
            raise Http404

        objects = getattr(obj, self.query_attr)

        # The related collection of objects might be a
        # function or a manager class.
        # This is to work around a pain-point in models.py.
        if callable(objects):
            objects = objects()

        # Apply any specified sorting.
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
    column_headers = ('feeds',)
    statenav_active = 'bills'


def state_nav(active_collection):
    'Produce data for the state navigation bar.'
    collections = ('legislators', 'bills', 'committees',)
    return ((active_collection == c, c) for c in collections)


def state(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    return render_to_response(
        template_name=templatename('state'),
        dictionary=dict(abbr=abbr,
            metadata=meta,
            sessions=report.session_link_data(),
            lower=overview.chamber(abbr, 'lower'),
            upper=overview.chamber(abbr, 'upper'),
            recent_actions=overview.recent_actions(abbr),
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def state_selection(request):
    '''Handle submission of the state selection form
    in the base template.
    '''
    form = get_state_select_form()(request.GET)
    abbr = form.data['abbr']
    if len(abbr) != 2:
        return redirect('pick_a_state')
    return redirect('state', abbr=abbr)


def pick_a_state(request):
    metadata = db.metadata.find({}, ['_id', 'name'],
                                sort=[('name', 1)])

    def columns(cursor, num_columns):
        percolumn, _ = divmod(cursor.count(), num_columns)
        iterator = iter(cursor)
        for i in range(num_columns):
            yield list(islice(iterator, percolumn))

    return render_to_response(
        template_name=templatename('pick_a_state'),
        dictionary=dict(
            columns=columns(metadata, 3),
            metadata=metadata,
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def chamber_select(request, collection_name):
    '''Handle the chamber selection radio button, i.e.,
    in legislators_chamber and committees_chamber views.
    '''
    if collection_name not in ('legislators', 'committees'):
        raise Http404

    form = ChamberSelectForm(request.GET)
    chamber = form.data['chamber']
    abbr = form.data['abbr']

    if chamber != 'both':
        return redirect('%s_chamber' % collection_name, abbr, chamber)
    else:
        return redirect(collection_name, abbr)


def find_your_legislator(request):

    form = FindYourLegislatorForm(request.GET)

    url = 'http://rpc.geocoder.us/service/csv?address=%s'
    url = url % form.data['address'].replace(' ', '+')
    resp = requests.get(url)
    lat, lng, _ = resp.text.split(',', 2)
    import pdb;pdb.set_trace()


def legislators(request, abbr):

    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    fields = ['leg_id', 'full_name', 'photo_url', 'district', 'party',
              'chamber', 'state', 'last_name']
    fields = dict(zip(fields, repeat1))

    sort_key = 'district'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])

    spec = {'active': True}

    legislators = meta.legislators(extra_spec=spec, fields=fields)

    def sort_by_district(obj):
        matchobj = re.search(r'\d+', obj['district'])
        if matchobj:
            return int(matchobj.group())
        else:
            return obj['district']

    legislators = sorted(legislators, key=sort_by_district)

    if sort_key != 'district':
        legislators = sorted(legislators, key=itemgetter(sort_key),
                             reverse=(sort_order == -1))

    sort_order = {1: -1, -1: 1}[sort_order]

    legislators = list(legislators)

    chamber_select_form = ChamberSelectForm.unbound(meta)

    return render_to_response(
        template_name=templatename('legislators_chamber'),
        dictionary=dict(
            metadata=meta,
            chamber_select_form=chamber_select_form,
            chamber_select_template=templatename('chamber_select_form'),
            chamber_select_collection='legislators',
            show_chamber_column=True,
            abbr=abbr,
            legislators=legislators,
            sort_order=sort_order,
            sort_key=sort_key,
            legislator_table=templatename('legislator_table'),
            statenav_active='legislators',
            tweet_text='Test cow!',
            ),
        context_instance=RequestContext(request, default_context))


def legislators_chamber(request, abbr, chamber):
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    chamber_name = meta['%s_chamber_name' % chamber]

    # Query params
    spec = {'chamber': chamber, 'active': True}

    fields = ['leg_id', 'full_name', 'photo_url', 'district', 'party',
              'chamber', 'state', 'last_name']
    fields = dict(zip(fields, repeat1))

    sort_key = 'district'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])

    legislators = meta.legislators(extra_spec=spec, fields=fields)

    def sort_by_district(obj):
            matchobj = re.search(r'\d+', obj['district'])
            if matchobj:
                return int(matchobj.group())
            else:
                return obj['district']

    legislators = sorted(legislators, key=sort_by_district)

    if sort_key != 'district':
        legislators = sorted(legislators, key=itemgetter(sort_key),
                             reverse=(sort_order == -1))

    sort_order = {1: -1, -1: 1}[sort_order]

    legislators = list(legislators)

    chamber_select_form = ChamberSelectForm.unbound(meta, chamber)

    return render_to_response(
        template_name=templatename('legislators_chamber'),
        dictionary=dict(
            metadata=meta,
            chamber_name=chamber_name,
            chamber_select_form=chamber_select_form,
            chamber_select_template=templatename('chamber_select_form'),
            chamber_select_collection='legislators',
            show_chamber_column=False,
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
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    try:
        legislator = db.legislators.find_one({'_id': leg_id})
    except DoesNotExist:
        raise Http404

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
            metadata=meta,
            legislator=legislator,
            sources=legislator['sources'],
            sponsored_bills=sponsored_bills,
            legislator_votes=legislator_votes,
            has_votes=has_votes,
            statenav_active='legislators'),
        context_instance=RequestContext(request, default_context))


#----------------------------------------------------------------------------
def committees(request, abbr):

    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    chamber = request.GET.get('chamber', 'both')
    if chamber in ('upper', 'lower'):
        chamber_name = meta['%s_chamber_name' % chamber]
        spec = {'chamber': chamber}
        show_chamber_column = False
    else:
        chamber = 'both'
        spec = {}
        show_chamber_column = True
        chamber_name = ''

    fields = ['committee', 'subcommittee', 'members', 'state',
              'chamber']
    fields = dict(zip(fields, repeat1))

    sort_key = 'committee'
    sort_order = 1

    sort_key = request.GET.get('key', 'committee')
    sort_order = int(request.GET.get('order', 1))

    committees = meta.committees(spec, fields=fields,
                                  sort=[(sort_key, sort_order)])

    sort_order = {1: -1, -1: 1}[sort_order]

    chamber_select_form = ChamberSelectForm.unbound(meta, chamber)

    return render_to_response(
        template_name=templatename('committees_chamber'),
        dictionary=dict(
            chamber=chamber,
            committees=committees,
            abbr=abbr,
            metadata=meta,
            chamber_name=chamber_name,
            chamber_select_form=chamber_select_form,
            chamber_select_template=templatename('chamber_select_form'),
            committees_table_template=templatename('committees_table'),
            chamber_select_collection='committees',
            show_chamber_column=show_chamber_column,
            sort_order=sort_order,
            statenav_active='committees'),
        context_instance=RequestContext(request, default_context))


def committees_chamber(request, abbr, chamber):

    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    chamber_name = meta['%s_chamber_name' % chamber]

    # Query params
    spec = {'chamber': chamber}

    fields = ['committee', 'subcommittee', 'members']
    fields = dict(zip(fields, repeat1))

    sort_key = 'committee'
    sort_order = 1

    if request.GET:
        sort_key = request.GET['key']
        sort_order = int(request.GET['order'])

    committees = meta.committees(spec, fields=fields,
                                  sort=[(sort_key, sort_order)])

    sort_order = {1: -1, -1: 1}[sort_order]

    chamber_select_form = ChamberSelectForm.unbound(meta, chamber)

    return render_to_response(
        template_name=templatename('committees_chamber'),
        dictionary=dict(
            committees=committees,
            abbr=abbr,
            metadata=meta,
            chamber_name=chamber_name,
            chamber_select_form=chamber_select_form,
            chamber_select_template=templatename('chamber_select_form'),
            committees_table_template=templatename('committees_table'),
            chamber_select_collection='committees',
            sort_order=sort_order,
            statenav_active='committees'),
        context_instance=RequestContext(request, default_context))


def committee(request, abbr, committee_id):
    try:
        committee = db.committees.find_one({'_id': committee_id})
    except DoesNotExist:
        raise Http404

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
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    return render_to_response(
        template_name=templatename('bills'),
        dictionary=dict(
            committee=committee,
            abbr=abbr,
            metadata=meta,
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))


def bills_by_subject(request, abbr, subject):
    pass


def bill(request, abbr, bill_id):
    try:
        bill = db.bills.find_one({'_id': bill_id})
    except DoesNotExist:
        raise Http404

    return render_to_response(
        template_name=templatename('bill'),
        dictionary=dict(
            vote_preview_row_template=templatename('vote_preview_row'),
            bill_progress_template=templatename('bill_progress_template'),
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            first_five=bill.sponsors_manager.first_five(),
            sources=bill['sources'],
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))


def vote(request, abbr, bill_id, vote_index):
    try:
        bill = db.bills.find_one({'_id': bill_id})
    except DoesNotExist:
        raise Http404

    return render_to_response(
        template_name=templatename('vote'),
        dictionary=dict(
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            vote=nth(bill.votes_manager, int(vote_index)),
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))
