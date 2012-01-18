import os
import unicodecsv
from collections import defaultdict

from billy import db
from billy.conf import settings, base_arg_parser
from billy.utils import metadata

class SubjectCategorizer(object):

    def __init__(self, abbr):
        """ load categorization from subjects CSV """
        self.abbr = abbr
        self.categorizer = defaultdict(set)

        filename = os.path.join(settings.BILLY_MANUAL_DATA_DIR,
                                'subjects', abbr + '.csv')
        try:
            reader = unicodecsv.reader(open(filename))

            # build category mapping
            for n,row in enumerate(reader):
                for subj in row[1:]:
                    if subj:
                        subj = subj.strip()
                        if subj not in settings.BILLY_SUBJECTS:
                            raise Exception('invalid subject %s (%s - %s)' %
                                            (subj, row[0], n))
                        self.categorizer[row[0]].add(subj)
        except IOError:
            raise

    def categorize_bill(self, bill):
        subjects = set()
        for ss in bill.get('scraped_subjects', []):
            categories = self.categorizer[ss]
            subjects.update(categories)
        bill['subjects'] = list(subjects)

    def categorize_bills(self, latest_term_only=False):
        meta = metadata(self.abbr)
        spec = {meta['level']: self.abbr}

        # process just the sessions from the latest term
        if latest_term_only:
            sessions = meta['terms'][-1]['sessions']
            spec['session'] = {'$in': sessions}

        for bill in db.bills.find(spec):
            self.categorize_bill(bill)
            db.bills.save(bill, safe=True)
