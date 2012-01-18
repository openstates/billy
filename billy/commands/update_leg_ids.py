from billy import db
from billy.commands import BaseCommand
from billy.utils import metadata
from billy.importers.names import NameMatcher

class UpdateLegIds(BaseCommand):
    name = 'update_leg_ids'
    help = '''update leg_ids for a specific session'''

    def add_args(self):
        self.add_argument('abbr', help='abbr to run matching for')
        self.add_argument('term', help='term to run matching for')


    def handle(self, args):
        level = metadata(args.abbr)['level']
        nm = NameMatcher(args.abbr, args.term, level)

        for t in metadata(args.abbr)['terms']:
            if t['name'] == args.term:
                sessions = t['sessions']
                break
        else:
            print 'No such term for %s: %s' % (args.abbr, args.term)
            return

        for session in sessions:
            bills = db.bills.find({'level': level, level: args.abbr,
                                   'session': session})

            for bill in bills:
                for sponsor in bill['sponsors']:
                    if not sponsor['leg_id']:
                        sponsor['leg_id'] = nm.match(sponsor['name'],
                                                     bill['chamber'])
                for vote in bill['votes']:
                    for type in ('yes_votes', 'no_votes', 'other_votes'):
                        for voter in vote[type]:
                            if not voter['leg_id']:
                                voter['leg_id'] = nm.match(voter['name'],
                                                           vote['chamber'])
                db.bills.save(bill, safe=True)
