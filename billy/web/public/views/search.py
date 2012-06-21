import re
import operator

from django.shortcuts import render
from django.conf import settings

from billy.models import db, Metadata, Bill
from billy.importers.utils import fix_bill_id
from .utils import templatename


def search_by_bill_id(abbr, search_text):
    '''Find bills with ids like "HB1234".
    '''
    spec = {}

    # If the input looks like a bill id, try to fetch the bill.
    if re.search(r'\d', search_text):
        bill_id = fix_bill_id(search_text).upper()
        collection = db.bills
        spec.update(bill_id=bill_id)

        if abbr != 'all':
            spec['state'] = abbr

        docs = collection.find(spec)

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

            return docs


def search_combined_bills_legislators(request, scope):

    search_text = request.GET['search_text']

    # Search bills.
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
             rowtemplate_name=templatename('bills_list_row_with'
                                           '_state_and_session'),
             show_chamber_column=True,
             statenav_active=None))
