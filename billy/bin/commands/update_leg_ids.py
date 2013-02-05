from __future__ import print_function
from billy.core import db
from billy.bin.commands import BaseCommand
from billy.utils import metadata
from billy.importers.names import get_legislator_id
from billy.importers.bills import match_sponsor_ids
from billy.core import settings


class UpdateLegIds(BaseCommand):
    name = 'update_leg_ids'
    help = '''update leg_ids for a specific session'''

    def add_args(self):
        self.add_argument('abbr', help='abbr to run matching for')
        self.add_argument('term', help='term to run matching for')

    def handle(self, args):
        for t in metadata(args.abbr)['terms']:
            if t['name'] == args.term:
                sessions = t['sessions']
                break
        else:
            print('No such term for %s: %s' % (args.abbr, args.term))
            return

        for session in sessions:
            bills = db.bills.find({settings.LEVEL_FIELD: args.abbr,
                                   'session': session})

            for bill in bills:
                match_sponsor_ids(args.abbr, bill)
                db.bills.save(bill, safe=True)

            votes = db.votes.find({settings.LEVEL_FIELD: args.abbr,
                                   'session': session})
            for vote in votes:
                vote['_voters'] = []
                for type in ('yes_votes', 'no_votes', 'other_votes'):
                    for voter in vote[type]:
                        voter['leg_id'] = get_legislator_id(args.abbr,
                                                            vote['session'],
                                                            vote['chamber'],
                                                            voter['name'])
                        if voter['leg_id']:
                            vote['_voters'].append(voter['leg_id'])
                db.votes.save(vote, safe=True)
