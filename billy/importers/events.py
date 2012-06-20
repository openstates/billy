#!/usr/bin/env python
import os
import glob
import logging
import datetime
import json

from billy import db
from billy.importers.utils import prepare_obj, update, next_big_id
from billy.scrape.events import Event
from billy.importers.utils import compare_committee
from billy.importers.utils import fix_bill_id

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

def get_committee_id(level, abbr, name, chamber):
    spec = {"state": abbr}
    comms = db.committees.find(spec)
    for committee in comms:
        c = committee['committee']
        if compare_committee(name, c):
            return committee['_id']
    return None

def import_events(abbr, data_dir, import_actions=False):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'events', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))
        for committee in data['participants']:
            cttyid = get_committee_id(data['level'], data['state'],
                                      committee['participant'],
                                      committee['chamber'] )
            if cttyid:
                committee['committee_id'] = cttyid

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


# IMPORTANT: if/when actions_to_events is re-enabled it definitely
# needs to be updated to support level
#    if import_actions:
#        actions_to_events(state)
def actions_to_events(state):
    for bill in db.bills.find({'state': state}):
        count = 1
        for action in bill['actions']:
            guid = "%s:action:%06d" % (bill['_id'], count)
            count += 1

            event = db.events.find_one({'state': state,
                                        '_guid': guid})

            description = "%s: %s" % (bill['bill_id'], action['action'])
            data = Event(bill['session'], action['date'],
                         'bill:action', description, location=action['actor'],
                         action_type=action['type'])
            data.add_participant('actor', action['actor'])
            data['_guid'] = guid
            data['state'] = state

            if not event:
                data['created_at'] = datetime.datetime.utcnow()
                data['updated_at'] = data['created_at']
                _insert_with_id(data)
            else:
                update(event, data, db.events)
