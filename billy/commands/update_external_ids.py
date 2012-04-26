import json
import urllib
import urllib2
import time
import sys

from billy import db
from billy.conf import settings
from billy.commands import BaseCommand


def update_transparencydata_legislators(meta):
    current_term = meta['terms'][-1]['name']
    query = {'roles': {'$elemMatch':
                       {'type': 'member',
                        'level': meta['level'],
                        meta['level']: meta['abbreviation'],
                        'term': current_term},
                      },
             'transparencydata_id': None,
             'active': True,
            }

    updated = 0
    initial_count = db.legislators.find(query).count()
    abbrev = meta['_id'].upper()

    for leg in db.legislators.find(query):
        query = urllib.urlencode({'apikey': settings.SUNLIGHT_SERVICES_KEY,
                                  'search': leg['full_name'].encode('utf8')})
        url = 'http://transparencydata.com/api/1.0/entities.json?' + query
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

    print 'Updated %s of %s missing transparencydata ids' % (updated,
                                                             initial_count)


class UpdateMissingIds(BaseCommand):

    name = 'update-ext-ids'
    help = 'update TransparencyData and Vote Smart ids'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='abbreviations for data to update')
        self.add_argument('--sunlight_key', help='the Sunlight API key to use',
                          dest='SUNLIGHT_SERVICES_KEY')

    def handle(self, args):
        for abbr in args.abbrs:

            meta = db.metadata.find_one({'_id': abbr.lower()})
            if not meta:
                print "'{0}' does not exist in the database.".format(abbr)
                sys.exit(1)
            else:
                print "Updating ids for {0}".format(abbr)

            print "Updating TransparencyData ids..."
            update_transparencydata_legislators(meta)

            time.sleep(30)
