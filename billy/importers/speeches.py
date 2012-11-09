from billy.importers.names import get_legislator_id
from billy.importers.utils import prepare_obj
from billy.core import db, settings

from collections import defaultdict

import logging
import json
import glob
import os


logger = logging.getLogger('billy')


def import_speeches(abbr, data_dir):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'speeches', '*.json')
    speech_record_ids = defaultdict(set)

    for path in glob.iglob(pattern):
        # OK, We need to first go through all the JSON and load the document
        # IDs to clear out.
        with open(path) as f:
            data = prepare_obj(json.load(f))

        session = data['session']
        chamber = data['chamber']

        speech_record_ids[session].add((chamber, data['record_id']))

    for session in speech_record_ids:
        for obj in speech_record_ids[session]:
            chamber, record = obj
            # XXX: Should we really be clearing them all up front? Should
            #      we clear as we process each record block? Is it OK to
            #      store everything in memory? (there's a lot)
            #
            #      this will result in broken data if the import breaks
            #      below.
            #  -- PRT
            clear_old_speeches(abbr, chamber, session, record)

    for path in glob.iglob(pattern):
        # OK, now we need to import all the JSON. We don't keep the objects
        # from above, since that'd really dent memory, and a few more ms on
        # import isn't the end of the world.
        with open(path) as f:
            data = prepare_obj(json.load(f))
        import_speech(data)


def clear_old_speeches(abbr, chamber, session, record_id):
    db.speeches.remove({
        "session": session,
        "record_id": record_id,
        settings.LEVEL_FIELD: abbr,
        "chamber": chamber
    }, safe=True)


def import_speech(data):
    abbr = data[settings.LEVEL_FIELD]
    rid = data['record_id']
    session = data['session']
    chamber = data['chamber']

    # before we get too far, let's find the event we link against.

    event = db.events.find_one({
        "record_id": rid,
        "session": session
    })

    if event:
        data['event_id'] = event['_id']
    else:
        data['event_id'] = None

    # OK, let's now look up the Legislator.

    leg_id = get_legislator_id(abbr,
                               session,
                               chamber,
                               data['speaker'])
    data['speaker_id'] = leg_id

    logger.info("Saving speech %s %s %s %s" % (
        rid,
        data['event_id'],
        data['sequence'],
        data['speaker']
    ))

    db.speeches.insert(data, safe=True)
