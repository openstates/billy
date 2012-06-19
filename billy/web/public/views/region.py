"""
    views that are specific to a state/region
"""
import re
import operator

from django.shortcuts import redirect, render
from django.http import Http404
from django.conf import settings

from billy.models import db, Metadata, DoesNotExist, Bill
from billy.models.pagination import IteratorPaginator
from billy.importers.utils import fix_bill_id
from ..viewdata import overview, funfacts
from ..forms import get_state_select_form
from .utils import templatename


def state_selection(request):
    '''Handle submission of the state selection form
    in the base template.
    '''
    form = get_state_select_form(request.GET)
    abbr = form.data.get('abbr')
    if not abbr or len(abbr) != 2:
        raise Http404
    return redirect('state', abbr=abbr)


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

    # add bill counts to session listing
    sessions = meta.sessions()
    for s in sessions:
        s['bill_count'] = (report['bills']['sessions'][s['id']]['upper_count']
                       + report['bills']['sessions'][s['id']]['lower_count'])

    return render(request, templatename('state'),
                  dict(abbr=abbr, metadata=meta, sessions=sessions,
                       chambers=chambers,
                       recent_actions=overview.recent_actions(abbr),
                       statenav_active='home',
                       funfact=funfacts.get_funfact(abbr)))


def search(request, scope):

    abbr = None
    search_text = request.GET['q']
    scope_name = None
    spec = {}

    # If the input looks like a bill id, try to fetch the bill.
    if re.search(r'\d', search_text):
        bill_id = fix_bill_id(search_text).upper()
        collection = db.bills
        spec.update(bill_id=bill_id)

        if scope != 'all':
            abbr = scope

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

            return render(request, templatename('search_results_bill_id'),
              dict(bill_id=bill_id,
               abbr=abbr,
               rowtemplate_name=templatename('bills_list_row_with_state_and_session'),
               object_list=IteratorPaginator(docs),
               use_table=True,
               column_headers=('Title', 'Session', 'Introduced',
                               'Recent Action', 'Votes'),
               statenav_active=None))

    # The input didn't contain \d{4}, so assuming it's not a bill,
    # search bill title and legislator names.
    if settings.ENABLE_ELASTICSEARCH:
        kwargs = {}
        if scope != 'all':
            kwargs['state'] = scope
        bill_results = Bill.search(search_text, **kwargs)
    else:
        spec = {'title': {'$regex': search_text, '$options': 'i'}}
        if scope != 'all':
            abbr = scope
            scope_name = Metadata.get_object(abbr)['name']
            spec.update(state=abbr)
        bill_results = db.bills.find(spec)

    # See if any legislator names match.
    spec = {'full_name': {'$regex': search_text, '$options': 'i'}}
    if scope != 'all':
        abbr = scope
        scope_name = Metadata.get_object(abbr)['name']
        spec.update(state=abbr)
    legislator_results = db.legislators.find(spec)

    return render(request, templatename('search_results_bills_legislators'),
        dict(search_text=search_text,
             abbr=abbr,
             scope_name=scope_name,
             bills_list=bill_results.limit(5),
             more_bills_available=(5 < bill_results.count()),
             legislators_list=legislator_results.limit(5),
             more_legislators_available=(5 < legislator_results.count()),
             bill_column_headers=('State', 'Title', 'Session', 'Introduced',
                                  'Recent Action',),
             rowtemplate_name=templatename('bills_list_row_with_state_and_session'),
             show_chamber_column=True,
             statenav_active=None))


def not_active_yet(request, args, kwargs):
    try:
        metadata = Metadata.get_object(kwargs['abbr'])
    except DoesNotExist:
        raise Http404

    return render(request, templatename('state_not_active_yet'),
                  dict(metadata=metadata, statenav_active=None))
