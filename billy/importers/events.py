#!/usr/bin/env python
import os
import glob
import logging
import datetime
import json

from billy import db
from billy.importers.names import get_legislator_id
from billy.importers.utils import prepare_obj, update, next_big_id
from billy.importers.utils import fix_bill_id, get_committee_id

import pymongo

logger = logging.getLogger('billy')


def ensure_indexes():
    db.events.ensure_index([('when', pymongo.ASCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])
    db.events.ensure_index([('when', pymongo.DESCENDING),
                            ('state', pymongo.ASCENDING),
                            ('type', pymongo.ASCENDING)])


def _insert_with_id(event):
    abbr = event[event['level']]
    id = next_big_id(abbr, 'E', 'event_ids')
    logger.info("Saving as %s" % id)

    event['_id'] = id
    db.events.save(event, safe=True)

    return id


def import_events(abbr, data_dir, import_actions=False):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'events', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

        def _resolve_ctty(committee):
            return get_committee_id(data['level'],
                                    data['state'],
                                    committee['chamber'],
                                    committee['participant'])

        def _resolve_leg(leg):
            chamber = leg['chamber'] if leg['chamber'] in ['upper', 'lower'] \
                else None

            return get_legislator_id(abbr,
                                     data['session'],
                                     chamber,
                                     leg['participant'])

        resolvers = {
            "committee": _resolve_ctty,
            "legislator": _resolve_leg
        }

        for entity in data['participants']:
            type = entity['participant_type']
            id = None
            if type in resolvers:
                id = resolvers[type](entity)
            else:
                logger.warning("I don't know how to resolve a %s" % type)
            entity['id'] = id

        for bill in data['related_bills']:
            bill['_scraped_bill_id'] = bill['bill_id']
            bill_id = bill['bill_id']
            bill_id = fix_bill_id(bill_id)
            bill['bill_id'] = ""
            db_bill = db.bills.find_one({
                "$or": [
                    {
                        "state": abbr,
                        'session': data['session'],
                        'bill_id': bill_id
                    },
                    {
                        "state": abbr,
                        'session': data['session'],
                        'alternate_bill_ids': bill_id
                    }
                ]
            })

            if not db_bill:
                logger.warning("Error: Can't find %s" % bill_id)
                db_bill = {}
                db_bill['_id'] = None

            # Events are really hard to pin to a chamber. Some of these are
            # also a committee considering a bill from the other chamber, or
            # something like that.
            bill['bill_id'] = db_bill['_id']
        import_event(data)
    ensure_indexes()


def import_event(data):
    event = None
    level = data['level']

    if '_guid' in data:
        event = db.events.find_one({'level': level,
                                    level: data[level],
                                    '_guid': data['_guid']})

    if not event:
        event = db.events.find_one({'level': level,
                                    level: data[level],
                                    'when': data['when'],
                                    'end': data['end'],
                                    'type': data['type'],
                                    'description': data['description']})

    if not event:
        data['created_at'] = datetime.datetime.utcnow()
        data['updated_at'] = data['created_at']
        _insert_with_id(data)
    else:
        update(event, data, db.events)
