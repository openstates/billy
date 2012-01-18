import unicodecsv
from collections import defaultdict

from billy import db
from billy.commands import BaseCommand

def keyfunc(x):
    try:
        district = int(x[2])
    except ValueError:
        district = x[2]
    return x[1], district

class DistrictCSV(BaseCommand):
    name = 'districtcsv'
    help = '''create stub district CSV'''

    def add_args(self):
        self.add_argument('abbr', help='abbr to create district csv stub')


    def handle(self, args):
        fields = ('abbr', 'chamber', 'name', 'num_seats', 'boundary_id')
        out = unicodecsv.writer(open(args.abbr+'_districts.csv', 'w'))
        out.writerow(fields)

        counts = defaultdict(int)
        for leg in db.legislators.find({'state': args.abbr, 'active': True}):
            if 'chamber' in leg:
                counts[(leg['chamber'], leg['district'])] += 1

        data = []
        for key, count in counts.iteritems():
            chamber, district =  key
            data.append((args.abbr, chamber, district, count, ''))

        for item in sorted(data, key=keyfunc):
            out.writerow(item)
