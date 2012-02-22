from billy import db
from billy.commands import BaseCommand
from oyster.core import kernel

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
                    kernel.track_url(version['url'],
                                     bill['state'] + ':billdoc',
                                     id=version['doc_id'],
                                     # metadata
                                     name=version['name'],
                                     state=bill['state'],
                                     session=bill['session'],
                                     chamber=bill['chamber'],
                                     bill_id=bill['bill_id'],
                                     openstates_bill_id=bill['_id'])
