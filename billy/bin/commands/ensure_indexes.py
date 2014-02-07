from __future__ import print_function
from billy.core import db
from billy.bin.commands import BaseCommand
from billy.core import settings
import pymongo


class MongoIndex(BaseCommand):
    name = 'mongo-index'
    help = '''make indexes'''

    def add_args(self):
        self.add_argument(
            'collections', nargs='*',
            help='collection(s) to run matching for (defaults to all)'
        )
        self.add_argument('--purge', action='store_true', default=False,
                          help='purge old indexes')

    def handle(self, args):
        all_indexes = {
            'popularity_counts': [
                [('type', pymongo.ASCENDING), ('date', pymongo.ASCENDING),
                 ('obj_id', pymongo.ASCENDING)],
            ],
            'committees': [
                [('_all_ids', pymongo.ASCENDING)],
                [(settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('chamber', pymongo.ASCENDING)],
                [(settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('committee', pymongo.ASCENDING),
                 ('subcommittee', pymongo.ASCENDING)
                ]
            ],
            'events': [
                [('when', pymongo.ASCENDING),
                 (settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('type', pymongo.ASCENDING)],
                [('when', pymongo.DESCENDING),
                 (settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('type', pymongo.ASCENDING)],
                [ (settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('related_bills.bill_id', pymongo.ASCENDING),
                 ('when', pymongo.DESCENDING) ],
            ],
            'legislators': [
                [('_all_ids', pymongo.ASCENDING)],
                [('boundary_id', pymongo.ASCENDING)],
                [(settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('active', pymongo.ASCENDING),
                 ('chamber', pymongo.ASCENDING)],
                #[('roles.' + settings.LEVEL_FIELD, pymongo.ASCENDING),
                # ('roles.type', pymongo.ASCENDING),
                # ('roles.term', pymongo.ASCENDING),
                # ('roles.chamber', pymongo.ASCENDING),
                # ('roles.district', pymongo.ASCENDING)],
                {'role_and_name_parts': [
                    ('roles.' + settings.LEVEL_FIELD, pymongo.ASCENDING),
                    ('roles.type', pymongo.ASCENDING),
                    ('roles.term', pymongo.ASCENDING),
                    ('roles.chamber', pymongo.ASCENDING),
                    ('_scraped_name', pymongo.ASCENDING),
                    ('first_name', pymongo.ASCENDING),
                    ('last_name', pymongo.ASCENDING),
                    ('middle_name', pymongo.ASCENDING),
                    ('suffixes', pymongo.ASCENDING)],
                },
            ],
            'bills': [
                # bill_id is used for search in conjunction with ElasticSearch
                #  sort field (date) comes first
                #  followed by field that we do an $in on
                [('_all_ids', pymongo.ASCENDING)],
                [('created_at', pymongo.DESCENDING),
                 ('bill_id', pymongo.ASCENDING)],
                [('updated_at', pymongo.DESCENDING),
                 ('bill_id', pymongo.ASCENDING)],
                [('action_dates.last', pymongo.DESCENDING),
                 ('bill_id', pymongo.ASCENDING)],
                # primary sponsors index
                [('sponsors.leg_id', pymongo.ASCENDING),
                 ('sponsors.type', pymongo.ASCENDING),
                 (settings.LEVEL_FIELD, pymongo.ASCENDING)
                ],
                # for distinct queries
                [(settings.LEVEL_FIELD, pymongo.ASCENDING),
                 ('type', pymongo.ASCENDING),
                ],
            ],
            'subjects': [
                [('abbr', pymongo.ASCENDING)],
            ],
            'manual.name_matchers': [
                [('abbr', pymongo.ASCENDING)],
            ],
            'votes': [
                [('bill_id', pymongo.ASCENDING), ('date', pymongo.ASCENDING)],
                [('_voters', pymongo.ASCENDING), ('date', pymongo.ASCENDING)]
            ]
        }

        # add a plethora of bill indexes
        search_indexes = [
            ('sponsors.leg_id', settings.LEVEL_FIELD),
            ('chamber', settings.LEVEL_FIELD),
            ('session', settings.LEVEL_FIELD),
            ('session', 'chamber', settings.LEVEL_FIELD),
            ('_term', 'chamber', settings.LEVEL_FIELD),
            ('status', settings.LEVEL_FIELD),
            ('subjects', settings.LEVEL_FIELD),
            ('type', settings.LEVEL_FIELD),
            (settings.LEVEL_FIELD,),
        ]
        for index_keys in search_indexes:
            sort_indexes = ['action_dates.first', 'action_dates.last',
                            'updated_at']
            # chamber-abbr gets indexed w/ every possible sort
            if (index_keys == ('chamber', settings.LEVEL_FIELD) or
                    index_keys == (settings.LEVEL_FIELD,)):
                sort_indexes += ['action_dates.passed_upper',
                                 'action_dates.passed_lower']
            for sort_index in sort_indexes:
                index = [(ikey, pymongo.ASCENDING) for ikey in index_keys]
                index += [(sort_index, pymongo.DESCENDING)]
                all_indexes['bills'].append(index)

        collections = args.collections or all_indexes.keys()

        for collection in collections:
            print('indexing', collection, '...')
            current = set(db[collection].index_information().keys())
            current.discard('_id_')
            if collection == 'bills':
                # basic lookup / unique constraint on abbr/session/bill_id
                current.discard('%s_1_session_1_chamber_1_bill_id_1' %
                                settings.LEVEL_FIELD)
                db.bills.ensure_index([
                    (settings.LEVEL_FIELD, pymongo.ASCENDING),
                    ('session', pymongo.ASCENDING),
                    ('chamber', pymongo.ASCENDING),
                    ('bill_id', pymongo.ASCENDING)
                ], unique=True)
                print('creating level-session-chamber-bill_id index')
            print('currently has', len(current), 'indexes (not counting _id)')
            print('ensuring', len(all_indexes[collection]), 'indexes')
            ensured = set()
            for index in all_indexes[collection]:
                if isinstance(index, list):
                    ensured.add(db[collection].ensure_index(index))
                elif isinstance(index, dict):
                    name, index_spec = index.items()[0]
                    ensured.add(
                        db[collection].ensure_index(index_spec, name=name))
                else:
                    raise ValueError(index)
            new = ensured - current
            old = current - ensured
            if len(new):
                print(len(new), 'new indexes:', ', '.join(new))
            if len(old):
                print(len(old), 'indexes deprecated:', ', '.join(old))
                if args.purge:
                    print('removing deprecated indexes...')
                    for index in old:
                        db[collection].drop_index(index)
