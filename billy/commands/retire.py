from billy import db
from billy.commands import BaseCommand
from billy.utils import metadata
from billy.importers.legislators import deactivate_legislators

import datetime

class Retire(BaseCommand):
    name = 'retire'
    help = '''retire a legislator with a given end_date'''

    def add_args(self):
        self.add_argument('leg_id', type=str,
                          help='id of legislator to retire')
        self.add_argument('date', type=str,
                          help='YYYY-MM-DD date to set as legislator end_date')

    def handle(self, args):
        legislator = db.legislators.find_one({'leg_id': args.leg_id})
        level = legislator['level']
        abbr = legislator[level]

        term = metadata(abbr)['terms'][-1]['name']
        cur_role = legislator['roles'][0]
        if cur_role['type'] != 'member' or cur_role['term'] != term:
            raise ValueError('member missing role for %s' % term)

        date = datetime.datetime.strptime(args.date, '%Y-%m-%d')
        cur_role['end_date'] = date
        db.legislators.save(legislator, safe=True)
        print('deactivating legislator {0}'.format(args.leg_id))
        deactivate_legislators(term, abbr, level)

