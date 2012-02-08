import unicodecsv

from billy import db
from billy.commands import BaseCommand

class LoadLegislators(BaseCommand):
    name = 'loadlegislators'
    help = '''load legislator data from a CSV file allowing for manual updates
of their data'''

    def add_args(self):
        self.add_argument('filename', metavar='FILE', type=str,
                          help='CSV file to import')
        self.add_argument('--save', action='store_true', default=False,
                          help='save changes to database (default is dry run)')


    def handle(self, args):

        # print initial missing counts (a hack)
        state = args.filename.split('_')[0]

        namefile = unicodecsv.DictReader(open(args.filename))

        for row in namefile:
            # get the legislator
            leg = db.legislators.find_one({'leg_id': row['leg_id']})
            if not leg:
                print 'no such leg:', row['leg_id']
                continue

            # backwards compatibility, copy full_name into _scraped_name
            if '_scraped_name' not in leg:
                leg['_scraped_name'] = leg['full_name']

            # check columns
            changed = {}
            keys = set(['first_name', 'middle_name', 'last_name', 'suffixes',
                       'nickname', 'votesmart_id', 'transparencydata_id',
                       'photo_url'])
            keys.intersection_update(namefile.fieldnames)
            for key in keys:
                row[key] = row[key]
                fileval = (row[key] or u'').strip()
                dbval = (leg.get(key, u'') or u'').strip()
                if fileval != dbval:
                    changed[key] = dbval
                    leg[key] = fileval
                if leg.get(key):
                    leg[key] = leg[key].strip()

            # show what changed
            if changed:
                print row['leg_id']
                for k, v in changed.iteritems():
                    print '  %s [%s --> %s]' % (k, v, row[k])

            # reassemble full_name
            full_name = leg['first_name']
            #if leg.get('nickname'):
            #    full_name += ' "%s"' % leg['nickname']
            if leg['middle_name']:
                full_name += u' %s' % leg['middle_name']
            full_name += u' %s' % leg['last_name']
            if leg['suffixes']:
                full_name += u' %s' % leg['suffixes']
            leg['full_name'] = full_name

            if args.save:
                locked = list(set(leg.get('_locked_fields', []) +
                                  changed.keys() + ['full_name']))
                leg['_locked_fields'] = locked
                db.legislators.save(leg, safe=True)
