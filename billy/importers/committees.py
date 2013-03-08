#!/usr/bin/env python
import os
import glob
import json
import datetime
import logging

from billy.core import db
from billy.core import settings
from billy.importers.names import get_legislator_id
from billy.importers.utils import prepare_obj, update, insert_with_id

logger = logging.getLogger('billy')


def import_committees_from_legislators(current_term, abbr):
    """ create committees from legislators that have committee roles """

    # for all current legislators
    for legislator in db.legislators.find({'roles': {'$elemMatch': {
            'term': current_term, settings.LEVEL_FIELD: abbr}}}):

        # for all committee roles
        for role in legislator['roles']:
            if (role['type'] == 'committee member' and
                    'committee_id' not in role):

                spec = {settings.LEVEL_FIELD: abbr,
                        'chamber': role['chamber'],
                        'committee': role['committee']}
                if 'subcommittee' in role:
                    spec['subcommittee'] = role['subcommittee']

                committee = db.committees.find_one(spec)

                if not committee:
                    committee = spec
                    committee['_type'] = 'committee'
                    # copy LEVEL_FIELD from legislator to committee
                    committee[settings.LEVEL_FIELD] = \
                        legislator[settings.LEVEL_FIELD]
                    committee['members'] = []
                    committee['sources'] = []
                    if 'subcommittee' not in committee:
                        committee['subcommittee'] = None
                    insert_with_id(committee)

                for member in committee['members']:
                    if member['leg_id'] == legislator['leg_id']:
                        break
                else:
                    committee['members'].append(
                        {'name': legislator['full_name'],
                         'leg_id': legislator['leg_id'],
                         'role': role.get('position') or 'member'})
                    for source in legislator['sources']:
                        if source not in committee['sources']:
                            committee['sources'].append(source)
                    db.committees.save(committee, safe=True)

                    role['committee_id'] = committee['_id']

        db.legislators.save(legislator, safe=True)


def import_committee(data, current_session, current_term):
    abbr = data[settings.LEVEL_FIELD]
    spec = {settings.LEVEL_FIELD: abbr,
            'chamber': data['chamber'],
            'committee': data['committee']}
    if 'subcommittee' in data:
        spec['subcommittee'] = data['subcommittee']

    # insert/update the actual committee object
    committee = db.committees.find_one(spec)

    committee_return_status = None

    if not committee:
        insert_with_id(data)
        committee = data
        committee_return_status = "insert"
    else:
        update(committee, data, db.committees)
        committee_return_status = "update"

    # deal with the members, add roles
    for member in committee['members']:
        if not member['name']:
            continue

        leg_id = get_legislator_id(abbr, current_session, data['chamber'],
                                   member['name'])

        if not leg_id:
            logger.debug("No matches for %s" % member['name'].encode('ascii',
                                                                     'ignore'))
            member['leg_id'] = None
            continue

        legislator = db.legislators.find_one({'_all_ids': leg_id})

        if not legislator:
            logger.warning('No legislator with ID %s' % leg_id)
            member['leg_id'] = None
            continue

        member['leg_id'] = legislator['_id']

        for role in legislator['roles']:
            if (role['type'] == 'committee member' and
                    role['term'] == current_term and
                    role.get('committee_id') == committee['_id']):
                # if the position hadn't been copied over before, copy it now
                if role.get('position') != member['role']:
                    role['position'] = member['role']
                    db.legislators.save(legislator, safe=True)
                break
        else:
            new_role = {'type': 'committee member',
                        'committee': committee['committee'],
                        'term': current_term,
                        'chamber': committee['chamber'],
                        'committee_id': committee['_id'],
                        'position': member['role']}
            # copy over all necessary fields from committee
            new_role[settings.LEVEL_FIELD] = committee[settings.LEVEL_FIELD]

            if 'subcommittee' in committee:
                new_role['subcommittee'] = committee['subcommittee']
            legislator['roles'].append(new_role)
            legislator['updated_at'] = datetime.datetime.utcnow()
            db.legislators.save(legislator, safe=True)

    db.committees.save(committee, safe=True)
    return committee_return_status


def import_committees(abbr, data_dir):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'committees', '*.json')

    counts = {
        "update": 0,
        "insert": 0,
        "total": 0
    }

    meta = db.metadata.find_one({'_id': abbr})
    current_term = meta['terms'][-1]['name']
    current_session = meta['terms'][-1]['sessions'][-1]

    paths = glob.glob(pattern)

    for committee in db.committees.find({settings.LEVEL_FIELD: abbr}):
        committee['members'] = []
        db.committees.save(committee, safe=True)

    # import committees from legislator roles, no standalone committees scraped
    if not paths:
        import_committees_from_legislators(current_term, abbr)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        counts["total"] += 1
        ret = import_committee(data, current_session, current_term)
        counts[ret] += 1

    logger.info('imported %s committee files' % len(paths))

    link_parents(abbr)

    return counts


def link_parents(abbr):
    for comm in db.committees.find({settings.LEVEL_FIELD: abbr}):
        sub = comm.get('subcommittee')
        if not sub:
            comm['parent_id'] = None
        else:
            parent = db.committees.find_one({settings.LEVEL_FIELD: abbr,
                                             'chamber': comm['chamber'],
                                             'committee': comm['committee'],
                                             'subcommittee': None})
            if not parent:
                logger.warning("Failed finding parent for: %s" % sub)
                comm['parent_id'] = None
            else:
                comm['parent_id'] = parent['_id']

        db.committees.save(comm, safe=True)
