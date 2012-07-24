import datetime
from collections import defaultdict

from billy import db

yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
last_month = datetime.datetime.utcnow() - datetime.timedelta(days=30)
last_year = datetime.datetime.utcnow() - datetime.timedelta(days=365)


def update_common(obj, report):
    """ do updated_at checks """
    # updated checks
    if obj['updated_at'] >= yesterday:
        report['_updated_today_count'] += 1
        if obj['updated_at'] >= last_month:
            report['_updated_this_month_count'] += 1
            if obj['updated_at'] >= last_year:
                report['_updated_this_year_count'] += 1


QUALITY_EXCEPTIONS = {
    'bills:no_actions': 'Bill is missing actions',
    'bills:no_sponsors': 'Bill is missing sponsors',
    'bills:no_versions': 'Bill is missing versions',
    'votes:bad_yes_count': 'Vote has a bad "yes" count',
    'votes:bad_no_count': 'Vote has a bad "no" count',
    'votes:bad_other_count': 'Vote has a bad "other" count',
}


def get_quality_exceptions(abbr):
    quality_exceptions = defaultdict(set)
    for qe in db.quality_exceptions.find({'abbr': abbr}):
        quality_exceptions[qe['type']].update(qe['ids'])
    return quality_exceptions
