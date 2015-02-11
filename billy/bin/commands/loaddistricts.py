import os
import logging
import unicodecsv

from billy.core import settings, db
from billy.bin.commands import BaseCommand

logger = logging.getLogger('billy')


class LoadDistricts(BaseCommand):
    name = 'loaddistricts'
    help = 'Load in the Open States districts'

    def add_args(self):
        self.add_argument('path', metavar='PATH', type=str,
                          help='path to the manual data')

    def handle(self, args):
        path = args.path
        for file_ in os.listdir(path):
            if not file_.endswith(".csv"):
                continue

            abbr, _ = file_.split(".csv")
            self.load_districts(abbr, os.path.join(path, file_))

    def load_districts(self, abbr, dist_filename):
        if os.path.exists(dist_filename):
            db.districts.remove({'abbr': abbr})
            with open(dist_filename, 'r') as fd:
                dist_csv = unicodecsv.DictReader(fd)
                for dist in dist_csv:
                    dist['_id'] = '%(abbr)s-%(chamber)s-%(name)s' % dist
                    # dist['boundary_id'] = dist['boundary_id'] % dist
                    dist['boundary_id'] = dist['division_id']  # Stop-gap
                    dist['num_seats'] = int(dist['num_seats'])
                    db.districts.save(dist, safe=True)
        else:
            logging.getLogger('billy').warning("%s not found, continuing without "
                                               "districts" % dist_filename)
