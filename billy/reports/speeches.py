import logging
from collections import defaultdict

from billy.core import db, settings

logger = logging.getLogger('billy')


def _speech_report_dict():
    return {
        'unmatched_speakers': set(),
        "_speakers_with_id_count": 0
    }


def scan_speeches(abbr):
    sessions = defaultdict(_speech_report_dict)
    for speech in db.speeches.find({settings.LEVEL_FIELD: abbr}):
        session = speech['session']
        obj = sessions[session]
        if "speaker_id" in speech and speech['speaker_id']:
            obj['_speakers_with_id_count'] += 1
        else:
            obj['unmatched_speakers'].add(speech['speaker'])

    sets = ['unmatched_speakers']
    for session in sessions:
        sobj = sessions[session]
        for key in sets:
            sobj[key] = list(sobj[key])
        sessions[session] = sobj
    return sessions


def speech_report(abbr):
    report = scan_speeches(abbr)
    return report
