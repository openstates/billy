from billy import db
from billy.commands import BaseCommand
from billy.utils import metadata
from billy.importers.names import NameMatcher
from billy.conf import settings


class UpdateLegIds(BaseCommand):
    name = 'update_leg_ids'
    help = '''update leg_ids for a specific session'''

    def add_args(self):
        self.add_argument('abbr', help='abbr to run matching for')
        self.add_argument('term', help='term to run matching for')

    def handle(self, args):
        nm = NameMatcher(args.abbr, args.term)

        for t in metadata(args.abbr)['terms']:
            if t['name'] == args.term:
                sessions = t['sessions']
                break
        else:
            print 'No such term for %s: %s' % (args.abbr, args.term)
            return

        for session in sessions:
            bills = db.bills.find({settings.LEVEL_FIELD: args.abbr,
                                   'session': session})

            for bill in bills:
                for sponsor in bill['sponsors']:
                    sponsor['leg_id'] = nm.match(sponsor['name'],
                                                 bill['chamber'])
                db.bills.save(bill, safe=True)

            votes = db.votes.find({settings.LEVEL_FIELD: args.abbr,
                                   'session': session})
            for vote in votes:
                vote['_voters'] = []
                for type in ('yes_votes', 'no_votes', 'other_votes'):
                    for voter in vote[type]:
                        voter['leg_id'] = nm.match(voter['name'],
                                                   vote['chamber'])
                        if voter['leg_id']:
                            vote['_voters'].append(voter['leg_id'])
                db.votes.save(vote, safe=True)
