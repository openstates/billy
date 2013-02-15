import json
import urllib
import urllib2
import time
import sys

from billy.core import db
from billy.core import settings
from billy.bin.commands import BaseCommand


class UpdateMissingIds(BaseCommand):

    name = 'update-ext-ids'
    help = 'update TransparencyData ids'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='abbreviations for data to update')
        self.add_argument('--apikey', help='the API key to use',
                          dest='API_KEY')

    def handle(self, args):
        for abbr in args.abbrs:

            meta = db.metadata.find_one({'_id': abbr.lower()})
            if not meta:
                print("'{0}' does not exist in the database.".format(abbr))
                sys.exit(1)
            else:
                print("Updating ids for {0}".format(abbr))

            print("Updating TransparencyData ids...")
            current_term = meta['terms'][-1]['name']
            query = {'roles': {'$elemMatch':
                               {'type': 'member',
                                settings.LEVEL_FIELD: meta['abbreviation'],
                                'term': current_term},
                              },
                     'transparencydata_id': None,
                     'active': True,
                    }

            updated = 0
            initial_count = db.legislators.find(query).count()
            abbrev = meta['_id'].upper()

            for leg in db.legislators.find(query):
                query = urllib.urlencode({
                    'apikey': settings.API_KEY,
                    'search': leg['full_name'].encode('utf8')
                })
                url = ('http://transparencydata.com/api/1.0/entities.json?' +
                       query)
                data = urllib2.urlopen(url).read()
                results = json.loads(data)
                matches = []
                for result in results:
                    if (result['state'] == abbrev and
                            result['seat'][6:] == leg['chamber'] and
                            result['type'] == 'politician'):
                        matches.append(result)

                if len(matches) == 1:
                    leg['transparencydata_id'] = matches[0]['id']
                    db.legislators.save(leg, safe=True)
                    updated += 1

            print('Updated %s of %s missing transparencydata ids' % (
                updated, initial_count))

            time.sleep(30)
