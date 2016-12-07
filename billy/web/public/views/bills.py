import urllib

from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils.feedgenerator import Rss201rev2Feed
from django.views.decorators.csrf import ensure_csrf_cookie

from billy.core import settings
from billy.utils import popularity, fix_bill_id
from billy.models import db, Metadata, Bill
from billy.models.pagination import BillSearchPaginator

from ..forms import get_filter_bills_form
from .utils import templatename, RelatedObjectsList


EVENT_PAGE_COUNT = 10


class RelatedBillsList(RelatedObjectsList):
    show_per_page = 10
    use_table = True
    list_item_context_name = 'bill'
    paginator = BillSearchPaginator
    rowtemplate_name = templatename('bills_list_row')
    nav_active = 'bills'
    column_headers_tmplname = None      # not used
    defer_rendering_title = True

    def get_context_data(self, *args, **kwargs):
        '''
        Context:
            If GET parameters are given:
            - search_text
            - form (FilterBillsForm)
            - long_description
            - description
            - get_params
            Otherwise, the only context item is an unbound FilterBillsForm.

        Templates:
            - Are specified in subclasses.
        '''
        context = super(RelatedBillsList, self).get_context_data(*args,
                                                                 **kwargs)
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
            chamber = form.data.get('chamber')
            session = form.data.get('session')
            type = form.data.get('type')
            status = form.data.getlist('status')
            subjects = form.data.getlist('subjects')
            sponsor = form.data.get('sponsor__leg_id')
            if chamber:
                if metadata:
                    description.append(metadata['chambers'][chamber]['name']
                                      )
                else:
                    description.extend([chamber.title(), 'Chamber'])
            description.append((type or 'Bill') + 's')
            if session:
                description.append(
                    '(%s)' %
                    metadata['session_details'][session]['display_name']
                )
            if 'signed' in status:
                long_description.append('which have been signed into law')
            elif 'passed_upper' in status and 'passed_lower' in status:
                long_description.append('which have passed both chambers')
            elif 'passed_lower' in status:
                chamber_name = (metadata['chambers']['lower']['name']
                                if metadata else 'lower chamber')
                long_description.append('which have passed the ' +
                                        chamber_name)
            elif 'passed_upper' in status:
                chamber_name = (metadata['chambers']['upper']['name']
                                if metadata else 'upper chamber')
                long_description.append('which have passed the ' +
                                        chamber_name)
            if sponsor:
                leg = db.legislators.find_one({'_all_ids': sponsor},
                                              fields=('full_name', '_id'))
                leg = leg['full_name']
                long_description.append('sponsored by ' + leg)
            if subjects:
                long_description.append('related to ' + ', '.join(subjects))
            if search_text:
                long_description.append(u'containing the term "{0}"'.format(
                    search_text))
            context.update(long_description=long_description)
        else:
            if metadata:
                description = [metadata['name'], 'Bills']
            else:
                description = ['All Bills']
            context.update(form=FilterBillsForm())

        context.update(description=' '.join(description))

        # Add the correct path to paginated links.
        params = list(self.request.GET.iterlists())
        for k, v in params[:]:
            if k == 'page':
                params.remove((k, v))
        get_params = urllib.urlencode(params, doseq=True)
        context['get_params'] = get_params

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
            spec['abbr'] = abbr

        # Setup the paginator.
        get = self.request.GET.get
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        try:
            page = int(get('page', 1))
        except ValueError:
            raise Http404('no such page')
        if show_per_page > 100:
            show_per_page = 100

        # If search params are given:
        form = FilterBillsForm(self.request.GET)

        search_text = form.data.get('search_text')

        if form.data:
            form_abbr = form.data.get('abbr')
            if form_abbr:
                spec['abbr'] = form_abbr

            chamber = form.data.get('chamber')
            if chamber:
                spec['chamber'] = chamber

            subjects = form.data.getlist('subjects')
            if subjects:
                spec['subjects'] = subjects

            sponsor_id = form.data.get('sponsor__leg_id')
            if sponsor_id:
                spec['sponsor_id'] = sponsor_id

            if 'status' in form.data:
                status_choices = form.data.getlist('status')
                spec['status'] = status_choices

            type_ = form.data.get('type')
            if type_:
                spec['type_'] = type_

            session = form.data.get('session')
            if session:
                spec['session'] = session

        sort = self.request.GET.get('sort', 'last')

        result = Bill.search(search_text, sort=sort, **spec)

        return self.paginator(result, page=page, show_per_page=show_per_page)

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


class BillList(RelatedBillsList):
    '''
    Context:
        - Determined by RelatedBillsList.get_context_data

    Teamplates:
    - billy/web/public/bills_list.html
    - billy/web/public/_pagination.html
    - billy/web/public/bills_list_row.html
    '''
    template_name = templatename('bills_list')
    collection_name = 'metadata'
    query_attr = 'bills'
    description_template = '''NOT USED'''
    title_template = 'Search bills - {{ metadata.legislature_name }}'


class AllBillList(RelatedBillsList):
    '''
    Context:
        - Determined by RelatedBillsList.get_context_data

    Teamplates:
    - billy/web/public/bills_list.html
    - billy/web/public/_pagination.html
    - billy/web/public/bills_list_row_with_abbr_and_session.html
    '''
    template_name = templatename('bills_list')
    rowtemplate_name = templatename('bills_list_row_with_abbr_and_session')
    collection_name = 'bills'
    use_table = True
    description_template = '''NOT USED'''
    title_template = ('Search All Bills')


class AllBillCSVList(AllBillList):
    '''
    Context:
        - Determined by RelatedBillsList.get_context_data

    Teamplates:
       - None, creates a csv.
    '''
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        p = context['object_list']
        p.limit = p.count

        def escape(what):
            if what == "":
                return what

            return '"%s"' % (what.replace("\"", "\\\""))

        def _gen_csv():
            fields = [
                "Title",
                "State",
                "Legislative Session",
                "Bill ID",
                "Originating Chamber",
                "Sponsors",
                "First Action Date",
                "Last Action Date",
                "Latest Action",
                "Passed Senate",
                "Passed House",
                "OpenStates Link",
                "Versions",
            ]

            yield ",".join((x for x in fields))

            for bill in context['object_list']:
                entries = [bill[x] for x in [
                    "title",
                    "state",
                    "session",
                    "bill_id",
                    "chamber",
                ]]

                entries.append("; ".join([x['name'] for x in bill['sponsors']]))
                dates = sorted(bill['actions'], key=lambda x: x['date'])
                fmt = "%Y-%m-%d"
                entries.append(dates[0]['date'].strftime(fmt))
                entries.append(dates[-1]['date'].strftime(fmt))
                entries.append(dates[-1]['action'])
                ap = lambda x: "bill:passed" in x['type']

                lp = lambda x: x['actor'] == 'lower' and ap(x)
                up = lambda x: x['actor'] == 'lower' and ap(x)

                lower_passages = filter(lp, dates)
                upper_passages = filter(up, dates)
                url = bill.get_absolute_url()

                [entries.append(x[-1]['date'].strftime(fmt) if x else "") for
                 x in [lower_passages, upper_passages]]

                entries.append("http://openstates.org" + url)

                versions = bill.get("versions", [])
                version = versions[0]['url'] if len(versions) > 0 else ""
                entries.append(version)
                # We'll just get a version; figuring out the latest version
                # means a Mongo query for each bill's time. We'll just take
                # the 0th element of the list, since most folks will have to
                # research them all anyway. Putting all the versions in the
                # output is quite unwieldy.

                yield ",".join((escape(x) for x in entries))

        return HttpResponse((x + "\r\n" for x in _gen_csv()),
                            content_type='text/csv')


class BillFeed(BillList):
    """ does everything BillList does but outputs as RSS """

    show_per_page = 100

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        queryset = self.get_queryset()
        link = 'http://%s%s?%s' % (request.get_host(),
                                   reverse('bills', args=args, kwargs=kwargs),
                                   request.META['QUERY_STRING'])
        feed_url = 'http://%s%s?%s' % (request.get_host(),
                                       reverse('bills_feed', args=args,
                                               kwargs=kwargs),
                                       request.META['QUERY_STRING'])
        feed = Rss201rev2Feed(title=context['description'], link=link,
                              feed_url=feed_url, ttl=360,
                              description=context['description'] +
                              '\n'.join(context.get('long_description', '')))
        for item in queryset:
            link = 'http://%s%s' % (request.get_host(),
                                    item.get_absolute_url())
            feed.add_item(title=item['bill_id'], link=link, unique_id=link,
                          description=item['title'])
        return HttpResponse(feed.writeString('utf-8'),
                            content_type='application/xml')


def bill_noslug(request, abbr, bill_id):
    bill = db.bills.find_one({'_all_ids': bill_id})
    if bill is None:
        raise Http404("No such bill (%s)" % (bill_id))

    return redirect('bill',
                    abbr=abbr,
                    session=bill['session'],
                    bill_id=bill['bill_id'])


@ensure_csrf_cookie
def bill(request, abbr, session, bill_id):
    '''
    Context:
        - vote_preview_row_template
        - abbr
        - metadata
        - bill
        - events
        - show_all_sponsors
        - sponsors
        - sources
        - nav_active

    Templates:
        - billy/web/public/bill.html
        - billy/web/public/vote_preview_row.html
    '''
    # get fixed version
    fixed_bill_id = fix_bill_id(bill_id)
    # redirect if URL's id isn't fixed id without spaces
    if fixed_bill_id.replace(' ', '') != bill_id:
        return redirect('bill', abbr=abbr, session=session, bill_id=fixed_bill_id.replace(' ', ''))
    bill = db.bills.find_one({settings.LEVEL_FIELD: abbr, 'session': session,
                              'bill_id': fixed_bill_id})
    if bill is None:
        raise Http404(u'no bill found {0} {1} {2}'.format(abbr, session, bill_id))

    events = db.events.find({
        settings.LEVEL_FIELD: abbr,
        "related_bills.bill_id": bill['_id']
    }).sort("when", -1)
    events = list(events)
    if len(events) > EVENT_PAGE_COUNT:
        events = events[:EVENT_PAGE_COUNT]

    popularity.counter.inc('bills', bill['_id'], abbr=abbr, session=session)

    show_all_sponsors = request.GET.get('show_all_sponsors')
    if show_all_sponsors:
        sponsors = bill.sponsors_manager
    else:
        sponsors = bill.sponsors_manager.first_fifteen

    return render(
        request, templatename('bill'),
        dict(vote_preview_row_template=templatename('vote_preview_row'),
             abbr=abbr,
             metadata=Metadata.get_object(abbr),
             bill=bill,
             events=events,
             show_all_sponsors=show_all_sponsors,
             sponsors=sponsors,
             sources=bill['sources'],
             nav_active='bills'))


def vote(request, abbr, vote_id):
    '''
    Context:
        - abbr
        - metadata
        - bill
        - vote
        - nav_active

    Templates:
        - vote.html
    '''
    vote = db.votes.find_one(vote_id)
    if vote is None:
        raise Http404('no such vote: {0}'.format(vote_id))
    bill = vote.bill()

    return render(request, templatename('vote'),
                  dict(abbr=abbr, metadata=Metadata.get_object(abbr),
                       bill=bill,
                       vote=vote,
                       nav_active='bills'))


def document(request, abbr, session, bill_id, doc_id):
    '''
    Context:
        - abbr
        - session
        - bill
        - version
        - metadata
        - nav_active

    Templates:
        - billy/web/public/document.html
    '''
    # get fixed version
    fixed_bill_id = fix_bill_id(bill_id)
    # redirect if URL's id isn't fixed id without spaces
    if fixed_bill_id.replace(' ', '') != bill_id:
        return redirect('document', abbr=abbr, session=session,
                        bill_id=fixed_bill_id.replace(' ', ''), doc_id=doc_id)

    bill = db.bills.find_one({settings.LEVEL_FIELD: abbr, 'session': session,
                              'bill_id': fixed_bill_id})

    if not bill:
        raise Http404('No such bill.')

    for version in bill['versions']:
        if version['doc_id'] == doc_id:
            break
    else:
        raise Http404('No such document.')

    if not settings.ENABLE_DOCUMENT_VIEW.get(abbr, False):
        return redirect(version['url'])

    return render(request, templatename('document'),
                  dict(abbr=abbr, session=session, bill=bill, version=version,
                       metadata=bill.metadata, nav_active='bills'))


def bill_by_mongoid(request, id_):
    bill = db.bills.find_one(id_)
    return redirect(bill.get_absolute_url())


def show_all(key):
    '''
    Context:
        - abbr
        - metadata
        - bill
        - sources
        - nav_active

    Templates:
        - billy/web/public/bill_all_{key}.html
            - where key is passed in, like "actions", etc.
    '''
    def func(request, abbr, session, bill_id, key):
        # get fixed version
        fixed_bill_id = fix_bill_id(bill_id)
        # redirect if URL's id isn't fixed id without spaces
        if fixed_bill_id.replace(' ', '') != bill_id:
            return redirect('bill', abbr=abbr, session=session,
                            bill_id=fixed_bill_id.replace(' ', ''))
        bill = db.bills.find_one({settings.LEVEL_FIELD: abbr,
                                  'session': session,
                                  'bill_id': fixed_bill_id})
        if bill is None:
            raise Http404('no bill found {0} {1} {2}'.format(abbr, session,
                                                             bill_id))
        return render(request, templatename('bill_all_%s' % key),
                      dict(abbr=abbr, metadata=Metadata.get_object(abbr),
                           bill=bill, sources=bill['sources'],
                           nav_active='bills'))
    return func

all_documents = show_all('documents')
all_versions = show_all('versions')
