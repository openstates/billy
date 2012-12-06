from __future__ import print_function
import sys
import traceback

from billy.core import db, settings
from billy.commands import BaseCommand
from billy.fulltext.elasticsearch import ElasticSearchPush


class SyncVersions(BaseCommand):

    name = 'sync-versions'
    help = 'download latest versions and optionally push them to S3'

    def add_args(self):
        self.add_argument('abbr', metavar='ABBR', type=str,
                          help='abbreviation for versions to sync')
        self.add_argument('--immediate', action='store_true')
        self.add_argument('--elasticsearch', action='store_true')

    def handle(self, args):
        # inject scraper paths so scraper module can be found
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)

        errors = 0
        spec = {settings.LEVEL_FIELD: args.abbr}
        if args.elasticsearch:
            spec['_elasticsearch'] = None
            task = ElasticSearchPush
        documents = db.tracked_versions.find(spec, timeout=False)
        doc_count = documents.count()

        print('starting {0} for {1} documents ({2})'.format(
            task.__name__, doc_count,
            'immediate' if args.immediate else 'queued'))

        for doc in documents:
            if args.immediate:
                try:
                    task.apply((doc['_id'],), throw=True)
                except Exception:
                    errors += 1
                    traceback.print_exc()
            else:
                task.delay(doc['_id'])

        print('{0} {1} for {2} documents, {3} errors'.format(
            'ran' if args.immediate else 'queued', task.__name__, doc_count,
            errors))
