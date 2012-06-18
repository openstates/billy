import urllib
import operator

from itertools import islice

import pymongo

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404

from billy.models import db, Metadata, DoesNotExist, Bill
from billy.models.pagination import CursorPaginator, IteratorPaginator

from ..forms import get_filter_bills_form

from .utils import templatename, RelatedObjectsList, ListViewBase


default_context = dict(base_template='billy/web/public/base.html')

def nth(iterable, n, default=None):
    "Returns the nth item or a default value"
    return next(islice(iterable, n, None), default)


def sort_by_district(obj):
    matchobj = re.search(r'\d+', obj['district'])
    if matchobj:
        return int(matchobj.group())
    else:
        return obj['district']

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


class NewsList(RelatedObjectsList):

    list_item_context_name = 'entry'
    # sort_func = operator.itemgetter('published_parsed')
    # sort_reversed = True
    mongo_sort = [('updated_at', pymongo.DESCENDING)]
    paginator = CursorPaginator
    query_attr = 'feed_entries'
    rowtemplate_name = templatename('feed_entry')
    column_headers = ('feeds',)
    statenav_active = 'bills'
    description_template = templatename('list_descriptions/news')


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
    paginator = CursorPaginator
    description_template = templatename('list_descriptions/bills')

    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(
                                                        *args, **kwargs)
        metadata = context['metadata']
        FilterBillsForm = get_filter_bills_form(metadata)

        if self.request.GET:
            form = FilterBillsForm(self.request.GET)
            search_text = form.data.get('search_text')
            context.update(search_text=search_text)
            context.update(form=FilterBillsForm(self.request.GET))

            full_url = self.request.path + '?'
            full_url += urllib.urlencode(self.request.GET)
            context.update(full_url=full_url)
        else:
            context.update(form=FilterBillsForm())

        return context

    def get_queryset(self):

        metadata = Metadata.get_object(self.kwargs['abbr'])
        FilterBillsForm = get_filter_bills_form(metadata)

        # Setup the paginator.
        get = self.request.GET.get
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        if not self.request.GET:
            spec = {}
            cursor = db.bills.find(spec)
            cursor.sort([('updated_at', pymongo.DESCENDING)])
            return self.paginator(cursor, page=page,
                      show_per_page=show_per_page)

        form = FilterBillsForm(self.request.GET)
        params = [
            'chamber',
            'subjects',
            'sponsor__leg_id',
            'actions__type',
            'type']
        search_text = form.data.get('search_text')

        if settings.ENABLE_ELASTICSEARCH:
            kwargs = {}

            abbr = self.kwargs['abbr']
            if abbr != 'us':
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

            cursor = Bill.search(search_text, **kwargs)
            cursor.sort([('updated_at', pymongo.DESCENDING)])

        else:
            # Elastic search not enabled--query mongo normally.
            # Mainly here for local work on search views.
            spec = {'state': metadata['abbreviation']}
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


class SponsoredBillsList(RelatedBillsList):
    collection_name = 'legislators'
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

        # # Apply any specified sorting.
        # sort_func = getattr(self, 'sort_func', None)
        # sort_reversed = bool(getattr(self, 'sort_reversed', None))
        # if sort_func:
        #     objects = sorted(objects, key=sort_func,
        #                      reverse=sort_reversed)

        paginator = self.paginator(objects, page=page,
                                   show_per_page=show_per_page)
        return paginator


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


#----------------------------------------------------------------------------


def bill(request, abbr, bill_id):

    bill = db.bills.find_one({'_id': bill_id})
    if bill is None:
        raise Http404

    show_all_sponsors = request.GET.get('show_all_sponsors')
    return render_to_response(
        template_name=templatename('bill'),
        dictionary=dict(
            vote_preview_row_template=templatename('vote_preview_row'),
            abbr=abbr,
            metadata=Metadata.get_object(abbr),
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
            metadata=Metadata.get_object(abbr),
            bill=bill,
            vote=nth(bill.votes_manager, int(vote_index)),
            statenav_active='bills'),
        context_instance=RequestContext(request, default_context))
