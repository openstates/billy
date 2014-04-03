import sys

from billy.core import db, settings
from billy.importers.bills import elasticsearch_push
from billy.utils.fulltext import bill_to_elasticsearch
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
        self.add_argument('--sample', metavar='doc_id', type=str,
                          help='show sample for a given doc_id')

    def handle(self, args):
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)
        if args.sample:
            bill = db.bills.find({'_id': args.sample})[0]
            print(bill_to_elasticsearch(bill))
        else:
            for abbr in args.abbrs:
                for bill in db.bills.find({settings.LEVEL_FIELD: abbr.lower()},
                                          timeout=False):
                    elasticsearch_push(bill)
