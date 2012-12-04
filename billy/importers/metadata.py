#!/usr/bin/env python
import datetime
import importlib

from billy.core import db

PRESERVED_FIELDS = ('latest_json_url', 'latest_json_date',
                    'latest_csv_url', 'latest_csv_date')


def import_metadata(abbr):
    preserved = {}
    old_metadata = db.metadata.find_one({'_id': abbr}) or {}
    for field in PRESERVED_FIELDS:
        if field in old_metadata:
            preserved[field] = old_metadata[field]

    module = importlib.import_module(abbr)
    metadata = module.metadata
    metadata['_type'] = 'metadata'

    for term in metadata['terms']:
        for k, v in term.iteritems():
            if isinstance(v, datetime.date):
                term[k] = datetime.datetime.combine(v, datetime.time(0, 0))
    for session in metadata['session_details'].values():
        for k, v in session.iteritems():
            if isinstance(v, datetime.date):
                session[k] = datetime.datetime.combine(v, datetime.time(0, 0))

    metadata['_id'] = abbr
    metadata.update(preserved)

    metadata['latest_update'] = datetime.datetime.utcnow()

    db.metadata.save(metadata, safe=True)
