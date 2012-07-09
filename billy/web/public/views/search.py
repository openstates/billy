import re
import operator

from billy.models import db
from billy.importers.utils import fix_bill_id


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

        # Do a regex search if the input consists solely of digits.
        if 0 == docs.count():
            spec['bill_id'] = {'$regex': bill_id}
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
