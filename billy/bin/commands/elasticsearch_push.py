from billy.core import db, settings
from billy.importers.bills import elasticsearch_push
from billy.bin.commands import BaseCommand

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)
log = logging.getLogger('billy')


class ElasticsearchPush(BaseCommand):

    name = 'elasticsearch-push'
    help = 'sync bills to elasticsearch instance'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='abbreviations for bills to update')

    def handle(self, args):
        for abbr in args.abbrs:
            for bill in db.bills.find({settings.LEVEL_FIELD: abbr.lower()},
                                      timeout=False):
                elasticsearch_push(bill)
