import urllib
from itertools import islice
import pymongo

from django.shortcuts import render
from django.http import Http404
from django.conf import settings

from billy.models import db, Metadata, Bill
from billy.models.pagination import CursorPaginator, IteratorPaginator

from ..forms import get_filter_bills_form
from .utils import templatename, RelatedObjectsList, ListViewBase
from .search import search_by_bill_id


def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)


class BillsList(ListViewBase):

    use_table = True
    list_item_context_name = 'bill'
    paginator = CursorPaginator
    rowtemplate_name = templatename('bills_list_row')
    column_headers = ('Title', 'Introduced', 'Recent Action', 'Votes')
    statenav_active = 'bills'
    show_per_page = 10


class RelatedBillsList(RelatedObjectsList):
    show_per_page = 10
    use_table = True
    list_item_context_name = 'bill'
    paginator = CursorPaginator
    rowtemplate_name = templatename('bills_list_row')
    column_headers = ('Title', 'Introduced', 'Recent Action',)
    statenav_active = 'bills'
    defer_rendering_title = True

    def get_context_data(self, *args, **kwargs):
        context = super(RelatedBillsList, self).get_context_data(
                                                        *args, **kwargs)
        metadata = context['metadata']
        FilterBillsForm = get_filter_bills_form(metadata)

        if self.request.GET:
            form = FilterBillsForm(self.request.GET)
            search_text = form.data.get('search_text')
            context.update(search_text=search_text)
            context.update(form=FilterBillsForm(self.request.GET))
        else:
            context.update(form=FilterBillsForm())

        # Add the correct path to paginated links.
        params = dict(self.request.GET.items())
        if 'page' in params:
            del params['page']
        context.update(get_params=urllib.urlencode(params))

        # Add the abbr.
        context['abbr'] = self.kwargs['abbr']
        return context

    def get_queryset(self):
        abbr = self.kwargs['abbr']
        if abbr != 'all':
            metadata = Metadata.get_object(abbr)
        else:
            metadata = None
        FilterBillsForm = get_filter_bills_form(metadata)

        # Setup the paginator.
        get = self.request.GET.get
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        # If the request is for /xy/bills/ without search params:
        if not self.request.GET:
            spec = {}
            if abbr != 'all':
                spec['state'] = abbr
            cursor = db.bills.find(spec)
            cursor.sort([('updated_at', pymongo.DESCENDING)])
            return self.paginator(cursor, page=page,
                      show_per_page=show_per_page)

        # If search params are given:
        form = FilterBillsForm(self.request.GET)

        # First try to get by bill_id.
        search_text = form.data.get('search_text')
        if search_text is None:
            pass
        else:
            found_by_bill_id = search_by_bill_id(self.kwargs['abbr'],
                                                 search_text)
            if found_by_bill_id:
                return IteratorPaginator(found_by_bill_id)

        # Then fall back to search form use.
        params = [
            'chamber',
            'subjects',
            'sponsor__leg_id',
            'actions__type',
            'type',
            'status',
            'session']

        if settings.ENABLE_ELASTICSEARCH:
            kwargs = {}

            if abbr != 'all':
                kwargs['state'] = abbr

            chamber = form.data.get('chamber')
            if chamber:
                kwargs['chamber'] = chamber

            subjects = form.data.getlist('subjects')
            if subjects:
                kwargs['subjects'] = {'$all': filter(None, subjects)}

            sponsor_id = form.data.get('sponsor__leg_id')
            if sponsor_id:
                kwargs['sponsor_id'] = sponsor_id

            status = form.data.get('status')
            if status:
                kwargs['status'] = {'action_dates.%s' % status: {'$ne': None}}

            type_ = form.data.get('type')
            if type_:
                kwargs['type_'] = type_

            session = form.data.get('session')
            if session:
                kwargs['session'] = session

            cursor = Bill.search(search_text, **kwargs)
            cursor.sort([('updated_at', pymongo.DESCENDING)])

        else:
            # Elastic search not enabled--query mongo normally.
            # Mainly here for local work on search views.
            spec = {}
            if abbr != 'all':
                spec['state'] = metadata['abbreviation']
            for key in params:
                val = form.data.get(key)
                if val:
                    key = key.replace('__', '.')
                    spec[key] = val

            if search_text:
                spec['title'] = {'$regex': search_text, '$options': 'i'}

            cursor = db.bills.find(spec)
            cursor.sort([('updated_at', pymongo.DESCENDING)])

        return self.paginator(cursor, page=page,
                              show_per_page=show_per_page)


class StateBills(RelatedBillsList):
    template_name = templatename('state_bills_list')
    collection_name = 'metadata'
    query_attr = 'bills'
    paginator = CursorPaginator
    description_template = '''
        <a href="{{metadata.get_absolute_url}}">{{metadata.name}}</a> Bills
        '''
    title_template = '''
        Search and filter bills -
        {{ metadata.legislature_name }} - OpenStates'''


class AllStateBills(RelatedBillsList):
    template_name = templatename('state_bills_list')
    rowtemplate_name = templatename('bills_list_row_with_state_and_session')
    collection_name = 'bills'
    paginator = CursorPaginator
    use_table = True
    column_headers = ('State', 'Title', 'Session', 'Introduced',
                      'Recent Action')
    description_template = 'Bills from all 50 States'
    title_template = ('Search and filter bills for all '
                      '50 States - OpenStates')


class SponsoredBillsList(RelatedBillsList):
    collection_name = 'legislators'
    query_attr = 'sponsored_bills'
    description_template = '''
        bills sponsored by
        <a href="{% url legislator abbr obj.id obj.slug %}">
        {{obj.display_name}}</a>
        '''
    title_template = 'Bills sponsored by {{obj.display_name}} - OpenStates'


def bill(request, abbr, bill_id):

    bill = db.bills.find_one({'_id': bill_id})
    if bill is None:
        raise Http404

    show_all_sponsors = request.GET.get('show_all_sponsors')
    if show_all_sponsors:
        sponsors = bill.sponsors_manager
    else:
        sponsors = bill.sponsors_manager.first_fifteen
    return render(request, templatename('bill'),
        dict(vote_preview_row_template=templatename('vote_preview_row'),
             abbr=abbr,
             metadata=Metadata.get_object(abbr),
             bill=bill,
             show_all_sponsors=show_all_sponsors,
             sponsors=sponsors,
             sources=bill['sources'],
             statenav_active='bills'))


def vote(request, abbr, _id):
    vote = db.votes.find_one(_id)
    if vote is None:
        raise Http404
    bill = vote.bill()

    return render(request, templatename('vote'),
                  dict(abbr=abbr, metadata=Metadata.get_object(abbr),
                       bill=bill,
                       vote=vote,
                       statenav_active='bills'))
