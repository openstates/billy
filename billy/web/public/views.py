import re
import json
import urllib2
import operator

from random import choice

from operator import itemgetter
from itertools import repeat, islice

import pymongo

from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.generic import TemplateView
from django.http import Http404, HttpResponse
from django.conf import settings

import billy.models
from billy.models import db, Metadata, DoesNotExist
from billy.models.pagination import CursorPaginator, IteratorPaginator
from billy.conf import settings as billy_settings
from billy.importers.utils import fix_bill_id

from .forms import (get_state_select_form, ChamberSelectForm,
                    FindYourLegislatorForm, get_filter_bills_form)
from .viewdata import overview


default_context = dict(base_template='billy/web/public/base.html')
openstates_api_host = "http://openstates.org"


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
    try:
        metadata = Metadata.get_object(kwargs['abbr'])
    except DoesNotExist:
        return redirect(pick_a_state)

    return render_to_response(
        template_name=templatename('state_not_active_yet'),
        dictionary=dict(
            metadata=metadata,
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def homepage(request):
    return render_to_response(
        template_name=templatename('homepage'),
        dictionary=dict(
            active_states=map(Metadata.get_object, settings.ACTIVE_STATES),
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def search(request, scope):

    abbr = None
    search_text = request.GET['q']
    spec = {}

    # If the input looks like a bill id, try to fetch the bill.
    if re.search(r'\d', search_text):
        bill_id = fix_bill_id(search_text).upper()
        collection = db.bills
        spec.update(bill_id=bill_id)

        if scope != 'us':
            abbr = scope
            spec.update(state=abbr)

        docs = collection.find(spec, limit=10)

        # If there were actual results, return a bill_id result view.
        if 0 < docs.count():

            def sortkey(doc):
                session = doc['session']
                years = re.findall(r'\d{4}', session)
                try:
                    return int(years[-1])
                except IndexError:
                    return session

            docs = sorted(docs, key=operator.itemgetter('session'),
                          reverse=True)

            return render_to_response(
                template_name=templatename('search_results_bill_id'),
                dictionary=dict(
                    bill_id=bill_id,
                    abbr=abbr,
                    rowtemplate_name=templatename('bills_list_row_with_session'),
                    object_list=IteratorPaginator(docs),
                    use_table=True,
                    column_headers=('Title', 'Session', 'Introduced',
                                    'Recent Action', 'Votes'),
                    statenav_active=None),
                context_instance=RequestContext(request, default_context))

    # The input didn't contain \d{4}, so assuming it's not a bill,
    # search bill title and legislator names.
    scope_name = None
    spec = {'title': {'$regex': search_text, '$options': 'i'}}
    if scope != 'us':
        abbr = scope
        scope_name = Metadata.get_object(abbr)['name']
        spec.update(state=abbr)
    bill_results = db.bills.find(spec)

    spec = {'full_name': {'$regex': search_text, '$options': 'i'}}
    if scope != 'us':
        abbr = scope
        scope_name = Metadata.get_object(abbr)['name']
        spec.update(state=abbr)
    legislator_results = db.legislators.find(spec)

    return render_to_response(
        template_name=templatename('search_results_bills_legislators'),
        dictionary=dict(
            search_text=search_text,
            abbr=abbr,
            scope_name=scope_name,
            bills_list=bill_results.limit(5),
            more_bills_available=(5 < bill_results.count()),
            legislators_list=legislator_results.limit(5),
            more_legislators_available=(5 < legislator_results.count()),
            bill_column_headers=('State', 'Title', 'Session', 'Introduced',
                                 'Recent Action', 'Votes'),
            show_chamber_column=True,
            statenav_active=None),
            context_instance=RequestContext(request, default_context))


class ListViewBase(TemplateView):
    '''Base class for VoteList, FeedList, etc.

    I tried using generic views for bill lists to cut down the
    boilerplate, but I'm not sure that has succeeded. One downside
    has been the reuse of what attempts to be a generic sort of
    template but in reality has become an awful monster template,
    named "object_list.html." Possibly more tuning needed.
    '''

    template_name = templatename('object_list')

    def get_context_data(self, *args, **kwargs):
        super(ListViewBase, self).get_context_data(*args, **kwargs)
        context = {}
        context.update(**default_context)
        context.update(column_headers=self.column_headers,
                       rowtemplate_name=self.rowtemplate_name,
                       description_template=self.description_template,
                       object_list=self.get_queryset(),
                       statenav_active=self.statenav_active,
                       abbr=self.kwargs['abbr'],
                       metadata=Metadata.get_object(self.kwargs['abbr']),
                       url=self.request.path,
                       use_table=getattr(self, 'use_table', False))

        # Include the kwargs to enable references to url paramaters.
        context.update(**kwargs)
        return context


class RelatedObjectsList(ListViewBase):
    '''A generic list view where there's a main object, like a
    legislator or state, and we want to display all of the main
    object's "sponsored_bills" or "introduced_bills." This class
    basically hacks the ListViewBase to add the main object into
    the template context so it can be used to generate a phrase like
    'showing all sponsored bills for Wesley Chesebro.'
    '''
    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(
                                                        *args, **kwargs)
        context.update(obj=self.get_object())
        return context

    def get_object(self):
        try:
            return self.obj
        except AttributeError:
            pass

        try:
            collection_name = self.kwargs['collection_name']
        except KeyError:
            collection_name = self.collection_name

        collection_name = {
            'state': 'metadata',
            }.get(collection_name, collection_name)

        try:
            _id = self.kwargs['id']
        except KeyError:
            _id = self.kwargs['abbr']

        # Get the related object.
        collection = getattr(billy.models.db, collection_name)

        try:
            obj = collection.find_one(_id)
        except DoesNotExist:
            raise Http404

        self.obj = obj
        return obj

    def get_queryset(self):

        get = self.request.GET.get

        # Setup the paginator arguments.
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        objects = getattr(self.get_object(), self.query_attr)

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


class VotesList(RelatedObjectsList):

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
    description_template = templatename('list_descriptions/votes')


class FeedsList(RelatedObjectsList):

    list_item_context_name = 'entry'
    # sort_func = operator.itemgetter('published_parsed')
    # sort_reversed = True
    paginator = CursorPaginator
    query_attr = 'feed_entries'
    rowtemplate_name = templatename('feed_entry')
    column_headers = ('feeds',)
    statenav_active = 'bills'
    description_template = templatename('list_descriptions/feeds')


class BillsList(ListViewBase):

    use_table = True
    list_item_context_name = 'bill'
    paginator = CursorPaginator
    rowtemplate_name = templatename('bills_list_row')
    column_headers = ('Title', 'Introduced', 'Recent Action', 'Votes')
    statenav_active = 'bills'


class RelatedBillsList(RelatedObjectsList):
    show_per_page = 10
    use_table = True
    list_item_context_name = 'bill'
    paginator = CursorPaginator
    rowtemplate_name = templatename('bills_list_row')
    column_headers = ('Title', 'Introduced', 'Recent Action', 'Votes')
    statenav_active = 'bills'


class StateBills(RelatedBillsList):
    template_name = templatename('state_bills_list')
    collection_name = 'metadata'
    query_attr = 'bills'
    description_template = templatename(
        'list_descriptions/bills')

    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(
                                                        *args, **kwargs)
        metadata = context['metadata']
        FilterBillsForm = get_filter_bills_form(metadata)
        context.update(form=FilterBillsForm())
        return context


class FilterBills(RelatedBillsList):
    template_name = templatename('state_bills_list')
    collection_name = 'metadata'
    query_attr = 'bills'
    paginator = CursorPaginator
    description_template = templatename(
        'list_descriptions/bills')

    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(
                                                        *args, **kwargs)
        metadata = context['metadata']
        FilterBillsForm = get_filter_bills_form(metadata)
        form = FilterBillsForm(self.request.GET)
        search_text = form.data.get('search_text')
        context.update(search_text=search_text)
        context.update(form=FilterBillsForm(self.request.GET))
        return context

    def get_queryset(self):

        metadata = Metadata.get_object(self.kwargs['abbr'])
        FilterBillsForm = get_filter_bills_form(metadata)
        form = FilterBillsForm(self.request.GET)

        params = [
            'chamber',
            'subjects',
            'sponsor__leg_id',
            'actions__type',
            'type']

        spec = {'state': metadata['abbreviation']}
        for key in params:
            val = form.data.get(key)
            if val:
                key = key.replace('__', '.')
                spec[key] = val

        search_text = form.data.get('search_text')
        if search_text:
            spec['title'] = {'$regex': search_text, '$options': 'i'}

        return self.paginator(db.bills.find(spec),
                              show_per_page=self.show_per_page)


class SponsoredBillsList(RelatedBillsList):
    query_attr = 'sponsored_bills'
    description_template = templatename(
        'list_descriptions/sponsored_bills')


class BillsBySubject(BillsList):

    description_template = templatename(
        'list_descriptions/bills_by_subject')

    def get_queryset(self, *args, **kwargs):

        get = self.request.GET.get

        subject = self.kwargs['subject']
        abbr = self.kwargs['abbr']
        objects = db.bills.find({'state': abbr, 'subjects': subject})

        # Setup the paginator arguments.
        show_per_page = int(get('show_per_page', 20))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        # Apply any specified sorting.
        sort_func = getattr(self, 'sort_func', None)
        sort_reversed = bool(getattr(self, 'sort_reversed', None))
        if sort_func:
            objects = sorted(objects, key=sort_func,
                             reverse=sort_reversed)

        paginator = self.paginator(objects, page=page,
                                   show_per_page=show_per_page)
        return paginator


class BillsIntroducedUpper(RelatedBillsList):
    collection_name = 'metadata'
    query_attr = 'bills_introduced_upper'
    description_template = templatename(
        'list_descriptions/bills_introduced_upper')


class BillsIntroducedLower(RelatedBillsList):
    collection_name = 'metadata'
    query_attr = 'bills_introduced_lower'
    description_template = templatename(
        'list_descriptions/bills_introduced_lower')


class BillsIntroducedUpper(RelatedBillsList):
    collection_name = 'metadata'
    query_attr = 'bills_introduced_upper'
    description_template = templatename(
        'list_descriptions/bills_introduced_upper')


class BillsPassedUpper(RelatedBillsList):
    collection_name = 'metadata'
    query_attr = 'bills_passed_upper'
    description_template = templatename(
        'list_descriptions/bills_passed_upper')


class BillsPassedLower(RelatedBillsList):
    collection_name = 'metadata'
    query_attr = 'bills_passed_lower'
    description_template = templatename(
        'list_descriptions/bills_passed_lower')


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

    chambers = [
        overview.chamber(abbr, 'upper'),
        overview.chamber(abbr, 'lower'),
    ]

    return render_to_response(
        template_name=templatename('state'),
        dictionary=dict(abbr=abbr,
            metadata=meta,
            sessions=reversed(list(report.session_link_data())),
            chambers=chambers,
            recent_actions=overview.recent_actions(abbr),
            statenav_active=None),
        context_instance=RequestContext(request, default_context))


def state_selection(request):
    '''Handle submission of the state selection form
    in the base template.
    '''
    form = get_state_select_form(request.GET)
    abbr = form.data['abbr']
    if len(abbr) != 2:
        return redirect('pick_a_state')
    return redirect('state', abbr=abbr)


def pick_a_state(request):
    metadata = db.metadata.find({'_id': {'$in': settings.ACTIVE_STATES}},
                                ['_id', 'name'], sort=[('name', 1)])

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
    # check if lat/lon are set
    # if leg_search is set, they most likely don't have ECMAScript enabled.
    # XXX: fallback behavior here for alpha.

    get = request.GET
    kwargs = {}
    template = 'find_your_legislator'

    addrs = [
        "50 Rice Street, Wellesley, MA",
        "20700 North Park Blvd. University Heights, Ohio",
        "1818 N Street NW, Washington, DC"
    ]

    kwargs['address'] = choice(addrs)

    if "q" in get:
        kwargs['request'] = get['q']

    if "lat" in get and "lon" in get:
        # We've got a passed lat/lon. Let's build off it.
        lat = get['lat']
        lon = get['lon']

        kwargs['lat'] = lat
        kwargs['lon'] = lon
        kwargs['located'] = True

        qurl = "%s/api/v1/legislators/geo/?long=%s&lat=%s&apikey=%s" % (
            openstates_api_host,
            lon,
            lat,
            billy_settings.SUNLIGHT_API_KEY
        )
        f = urllib2.urlopen(qurl)

        if "boundary" in get:
            legs = json.load(f)
            to_search = []
            for leg in legs:
                to_search.append(leg['boundary_id'])
            borders = set(to_search)
            ret = {}
            for border in borders:
                qurl = "%s/api/v1/districts/boundary/%s/?apikey=%s" % (
                    openstates_api_host,
                    border,
                    billy_settings.SUNLIGHT_API_KEY
                )
                f = urllib2.urlopen(qurl)
                resp = json.load(f)
                ret[border] = resp
            return HttpResponse(json.dumps(ret))

        kwargs['legislators'] = json.load(f)
        template = 'find_your_legislator_table'

    return render_to_response(
        template_name=templatename(template),
        dictionary=kwargs,
        context_instance=RequestContext(request, default_context))


def legislators(request, abbr):

    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    spec = {'active': True}

    chamber = request.GET.get('chamber', 'both')
    if chamber in ('upper', 'lower'):
        spec['chamber'] = chamber
    else:
        chamber = 'both'

    fields = ['leg_id', 'full_name', 'photo_url', 'district', 'party',
              'chamber', 'state', 'last_name']
    fields = dict(zip(fields, repeat1))

    sort_key = 'district'
    sort_order = 1

    if request.GET:
        sort_key = request.GET.get('key', sort_key)
        sort_order = int(request.GET.get('order', sort_order))

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
    else:
        legislators = sorted(legislators, key=sort_by_district,
                             reverse=bool(0 > sort_order))

    sort_order = {1: -1, -1: 1}[sort_order]
    legislators = list(legislators)
    initial = {'key': 'district', 'chamber': chamber}
    chamber_select_form = ChamberSelectForm.unbound(meta, initial=initial)

    return render_to_response(
        template_name=templatename('legislators_chamber'),
        dictionary=dict(
            metadata=meta,
            chamber=chamber,
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
            ),
        context_instance=RequestContext(request, default_context))


def legislator(request, abbr, leg_id):
    '''
    Note - changes needed before we can display "sessions served" info.
    '''
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    legislator = db.legislators.find_one({'_id': leg_id})
    if legislator is None:
        raise Http404('No legislator was found with led_id = %r' % leg_id)

    if not legislator['active']:
        return legislator_inactive(request, abbr, legislator)

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


def legislator_inactive(request, abbr, legislator):
    '''
    '''
    # Note to self: Slow query
    sponsored_bills = legislator.sponsored_bills(
        limit=5, sort=[('actions.1.date', pymongo.DESCENDING)])

    # Note to self: Another slow query
    legislator_votes = legislator.votes_3_sorted()
    has_votes = bool(legislator_votes)
    return render_to_response(
        template_name=templatename('legislator_inactive'),
        dictionary=dict(
            feed_entry_template=templatename('feed_entry'),
            vote_preview_row_template=templatename('vote_preview_row'),
            old_roles=legislator.old_roles_manager,
            abbr=abbr,
            metadata=legislator.metadata,
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

    committee = db.committees.find_one({'_id': committee_id})
    if committee is None:
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


def bill(request, abbr, bill_id):

    bill = db.bills.find_one({'_id': bill_id})
    if bill is None:
        raise Http404

    show_all_sponsors = request.GET.get('show_all_sponsors')
    return render_to_response(
        template_name=templatename('bill'),
        dictionary=dict(
            vote_preview_row_template=templatename('vote_preview_row'),
            bill_progress_template=templatename('bill_progress_template'),
            abbr=abbr,
            state=Metadata.get_object(abbr),
            bill=bill,
            show_all_sponsors=show_all_sponsors,
            sources=bill['sources'],
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))


def vote(request, abbr, bill_id, vote_index):
    bill = db.bills.find_one({'_id': bill_id})
    if bill is None:
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
