import datetime

from billy import db
from billy.commands import BaseCommand

class PruneCommittees(BaseCommand):
    name = 'prunecommittees'
    help = '''prune all committees that are inactive'''

    def add_args(self):
        self.add_argument('abbr', help='abbr to run for')
        self.add_argument('--days', help='days after which a committee is '
                          'considered inactive', default=30, type=int)
        self.add_argument('--delete', help='actually delete (dry run by '
                          'default)', action='store_true', default=False)

    def handle(self, args):
        empty_and_old = []
        for com in db.committees.find({'state': args.abbr}):
            empty = len(com['members']) == 0
            old = (com['updated_at'] + datetime.timedelta(days=args.days) <
                   datetime.datetime.utcnow())
            if empty and old:
                if com['subcommittee']:
                    name = '[{_id}] {committee}: {subcommittee}'.format(**com)
                else:
                    name = '[{_id}] {committee}'.format(**com)

                if args.delete:
                    print 'removing', name
                    db.committees.remove(com['_id'], safe=True)
                else:
                    print 'would remove', name
