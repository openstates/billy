from billy import db
from billy.conf import settings
from billy.commands import BaseCommand
from oyster.core import kernel
from billy.importers.bills import oysterize_version


class Oysterize(BaseCommand):
    name = 'oysterize'
    help = 'send bill versions to oyster'

    def add_args(self):
        self.add_argument('abbr', help='abbr of data to oysterize')

    def handle(self, args):
        abbr = args.abbr
        known_ids = kernel.db.tracked.find({'metadata.state': abbr}
                                          ).distinct('_id')
        bills = db.bills.find({settings.LEVEL_FIELD: abbr,
                               'versions.url': {'$exists': True}
                              }, timeout=False)
        print '%s bills with versions to oysterize' % bills.count()
        for bill in bills:
            for version in bill['versions']:
                if 'url' in version and version['doc_id'] not in known_ids:
                    oysterize_version(bill, version)
