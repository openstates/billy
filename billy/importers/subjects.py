from collections import defaultdict

from billy import db
from billy.conf import settings
from billy.utils import metadata


class SubjectCategorizer(object):
    def __init__(self, abbr):
        """ load categorization from subjects mongo table """
        self.abbr = abbr
        self.categorizer = defaultdict(set)
        subs = db.subjects.find({"abbr": abbr})
        for sub in subs:
            self.categorizer[sub['remote']] = sub['normal']

    def categorize_bill(self, bill):
        subjects = set()
        for ss in bill.get('scraped_subjects', []):
            categories = self.categorizer[ss]
            subjects.update(categories)
        bill['subjects'] = list(subjects)

    def categorize_bills(self, latest_term_only=False):
        meta = metadata(self.abbr)
        spec = {settings.LEVEL_FIELD: self.abbr}

        # process just the sessions from the latest term
        if latest_term_only:
            sessions = meta['terms'][-1]['sessions']
            spec['session'] = {'$in': sessions}

        for bill in db.bills.find(spec):
            self.categorize_bill(bill)
            db.bills.save(bill, safe=True)
