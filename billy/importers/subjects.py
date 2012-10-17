from collections import defaultdict

from billy.core import db
from billy.core import settings


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

    def categorize_bills(self):
        spec = {settings.LEVEL_FIELD: self.abbr}

        for bill in db.bills.find(spec):
            self.categorize_bill(bill)
            db.bills.save(bill, safe=True)
