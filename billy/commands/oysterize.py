from billy import db
from billy.commands import BaseCommand
from billy.importers.bills import oysterize_version


class Oysterize(BaseCommand):
    name = 'oysterize'
    help = 'send bill versions to oyster'

    def add_args(self):
        self.add_argument('state', help='state to oysterize')

    def handle(self, args):
        state = args.state
        bills = db.bills.find({'state': state,
                               'versions.url': {'$exists': True}
                              })
        print '%s bills with versions to oysterize' % bills.count()
        for bill in bills:
            for version in bill['versions']:
                if 'url' in version:
                    oysterize_version(bill, version)
