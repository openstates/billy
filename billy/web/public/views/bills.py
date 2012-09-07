import urllib
import pymongo

from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.feedgenerator import Rss201rev2Feed

from billy.utils import popularity
from billy.models import db, Metadata, Bill
from billy.models.pagination import CursorPaginator, IteratorPaginator
from billy.importers.utils import fix_bill_id

from ..forms import get_filter_bills_form
from .utils import templatename, RelatedObjectsList
from .search import search_by_bill_id


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

            # human readable description of search
            description = []
            if metadata:
                description.append(metadata['name'])
            else:
                description = ['Search All']
            long_description = []
            chamber = form.data.getlist('chamber')
            session = form.data.get('session')
            type = form.data.get('type')
            status = form.data.get('status')
            sponsor = form.data.get('sponsor__leg_id')
            if len(chamber) == 1:
                if metadata:
                    description.append(metadata[chamber[0] + '_chamber_name'])
                else:
                    description.extend([chamber[0].title(), 'Chamber'])
            description.append((type or 'Bill') + 's')
            if session:
                description.append('(%s)' %
                   metadata['session_details'][session]['display_name'])
            if status == 'passed_lower':
                long_description.append(('which have passed the ' +
                                         metadata['lower_chamber_name']))
            elif status == 'passed_upper':
                long_description.append(('which have passed the ' +
                                         metadata['upper_chamber_name']))
            elif status == 'signed':
                long_description.append('which have been signed into law')
            if sponsor:
                leg = db.legislators.find_one({'_all_ids': sponsor},
                                          fields=('full_name', '_id'))
                leg = leg['full_name']
                long_description.append('sponsored by ' + leg)
            if search_text:
                long_description.append('containing the term "{0}"'.format(
                    search_text))
            context.update(long_description=long_description)
        else:
            description = [metadata['name'], 'Bills']
            context.update(form=FilterBillsForm())

        context.update(description=' '.join(description))

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

        # start with the spec
        spec = {}
        if abbr != 'all':
            spec['state'] = abbr

        # Setup the paginator.
        get = self.request.GET.get
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        page = int(get('page', 1))
        if show_per_page > 100:
            show_per_page = 100

        # If search params are given:
        form = FilterBillsForm(self.request.GET)

        # First try to get by bill_id.
        search_text = form.data.get('search_text')
        if search_text:
            found_by_bill_id = search_by_bill_id(self.kwargs['abbr'],
                                                 search_text)
            if found_by_bill_id:
                return IteratorPaginator(found_by_bill_id)

        if settings.ENABLE_ELASTICSEARCH:
            chamber = form.data.get('chamber')
            if chamber:
                spec['chamber'] = chamber

            subjects = form.data.get('subjects')
            if subjects:
                spec['subjects'] = {'$all': [filter(None, subjects)]}

            sponsor_id = form.data.get('sponsor__leg_id')
            if sponsor_id:
                spec['sponsor_id'] = sponsor_id

            status = form.data.get('status')
            if status:
                spec['status'] = {'action_dates.%s' % status: {'$ne': None}}

            type_ = form.data.get('type')
            if type_:
                spec['type_'] = type_

            session = form.data.get('session')
            if session:
                spec['session'] = session

            cursor = Bill.search(search_text, **spec)
        else:
            # Elastic search not enabled--query mongo normally.
            # Mainly here for local work on search views.
            params = ['chamber', 'subjects', 'sponsor__leg_id',
                      'actions__type', 'type', 'status', 'session']
            for key in params:
                val = form.data.get(key)
                if val:
                    key = key.replace('__', '.')
                    spec[key] = val

            if search_text:
                spec['title'] = {'$regex': search_text, '$options': 'i'}

            cursor = db.bills.find(spec)

        sort = self.request.GET.get('sort', 'last')
        if sort not in ('first', 'last', 'signed', 'passed_upper',
                        'passed_lower'):
            sort = 'last'
        sort_key = 'action_dates.{0}'.format(sort)

        # do sorting on the cursor
        cursor.sort([(sort_key, pymongo.DESCENDING)])

        return self.paginator(cursor, page=page,
                              show_per_page=show_per_page)

    def get(self, request, *args, **kwargs):
        # hack to redirect to proper legislator if sponsor_id is an alias
        if 'sponsor__leg_id' in request.GET:
            _id = request.GET.get('sponsor__leg_id')
            leg = db.legislators.find_one({'_all_ids': _id})
            if leg and leg['_id'] != _id:
                new_get = request.GET.copy()
                new_get['sponsor__leg_id'] = leg['_id']
                return HttpResponseRedirect('?'.join(
                    (reverse('bills', args=args, kwargs=kwargs),
                     new_get.urlencode())))
        return super(RelatedBillsList, self).get(request, *args, **kwargs)


class StateBills(RelatedBillsList):
    template_name = templatename('bills_list')
    collection_name = 'metadata'
    query_attr = 'bills'
    paginator = CursorPaginator
    description_template = '''NOT USED'''
    title_template = '''
        Search bills -
        {{ metadata.legislature_name }} - Open States'''


class AllStateBills(RelatedBillsList):
    template_name = templatename('bills_list')
    rowtemplate_name = templatename('bills_list_row_with_state_and_session')
    collection_name = 'bills'
    paginator = CursorPaginator
    use_table = True
    column_headers = ('State', 'Title', 'Session', 'Introduced',
                      'Recent Action')
    description_template = '''NOT USED'''
    title_template = ('Search bills from all 50 states - Open States')


class BillFeed(StateBills):
    """ does everything StateBills does but outputs as RSS """

    show_per_page = 100

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        queryset = self.get_queryset()
        link = 'http://%s%s?%s' % (request.META['SERVER_NAME'],
                            reverse('bills', args=args, kwargs=kwargs),
                            request.META['QUERY_STRING'])
        feed_url = 'http://%s%s?%s' % (request.META['SERVER_NAME'],
                            reverse('bills_feed', args=args, kwargs=kwargs),
                            request.META['QUERY_STRING'])
        feed = Rss201rev2Feed(title=context['description'], link=link,
                              feed_url=feed_url, ttl=360,
                              description=context['description'] +
                              '\n'.join(context.get('long_description', '')))
        for item in queryset:
            link = 'http://%s%s' % (request.META['SERVER_NAME'],
                                    item.get_absolute_url())
            feed.add_item(title=item['bill_id'], link=link, unique_id=link,
                          description=item['title'])
        return HttpResponse(feed.writeString('utf-8'),
                            content_type='application/xml')


def bill(request, abbr, session, bill_id):
    # get fixed version
    fixed_bill_id = fix_bill_id(bill_id)
    # redirect if URL's id isn't fixed id without spaces
    if fixed_bill_id.replace(' ', '') != bill_id:
        return redirect('bill', abbr=abbr, session=session,
                        bill_id=fixed_bill_id.replace(' ', ''))
    bill = db.bills.find_one({'state': abbr, 'session': session,
                              'bill_id': fixed_bill_id})
    if bill is None:
        raise Http404('no bill found {0} {1} {2}'.format(abbr, session,
                                                         bill_id))

    popularity.counter.inc('bills', bill['_id'], abbr=abbr, session=session)

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


def vote(request, abbr, vote_id):
    vote = db.votes.find_one(vote_id)
    if vote is None:
        raise Http404('no such vote: {0}'.format(vote_id))
    bill = vote.bill()

    return render(request, templatename('vote'),
                  dict(abbr=abbr, metadata=Metadata.get_object(abbr),
                       bill=bill,
                       vote=vote,
                       statenav_active='bills'))


def bill_by_mongoid(request, id_):
    bill = db.bills.find_one(id_)
    return redirect(bill.get_absolute_url())


def show_all(key):
    def func(request, abbr, session, bill_id, key):
        # get fixed version
        fixed_bill_id = fix_bill_id(bill_id)
        # redirect if URL's id isn't fixed id without spaces
        if fixed_bill_id.replace(' ', '') != bill_id:
            return redirect('bill', abbr=abbr, session=session,
                            bill_id=fixed_bill_id.replace(' ', ''))
        bill = db.bills.find_one({'state': abbr, 'session': session,
                                  'bill_id': fixed_bill_id})
        if bill is None:
            raise Http404('no bill found {0} {1} {2}'.format(abbr, session,
                                                             bill_id))
        return render(request, templatename('bill_all_%s' % key),
        dict(abbr=abbr,
             metadata=Metadata.get_object(abbr),
             bill=bill,
             sources=bill['sources'],
             statenav_active='bills'))
    return func

all_documents = show_all('documents')
all_versions = show_all('versions')
