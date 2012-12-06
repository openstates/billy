import logging
from collections import defaultdict

from billy.core import db, settings
from billy.utils import term_for_session
from billy.reports.utils import get_quality_exceptions, combine_reports

logger = logging.getLogger('billy')


def _vote_report_dict():
    return {'vote_count': 0,
            '_passed_vote_count': 0,
            'votes_per_month': defaultdict(int),
            'votes_per_chamber': defaultdict(int),
            'votes_per_type': defaultdict(int),
            'bad_vote_counts': set(),
            '_rollcall_count': 0,
            '_rollcalls_with_leg_id_count': 0,
            'unmatched_voters': set()
           }


def scan_votes(abbr):
    sessions = defaultdict(_vote_report_dict)

    # load exception data into sets of ids indexed by exception type
    quality_exceptions = get_quality_exceptions(abbr)

    for vote in db.votes.find({settings.LEVEL_FIELD: abbr}):
        session_d = sessions[vote['session']]

        session_d['vote_count'] += 1
        if vote['passed']:
            session_d['_passed_vote_count'] += 1
        session_d['votes_per_chamber'][vote['chamber']] += 1
        if not vote.get('type'):
            logger.warning('vote %s missing type' % vote['_id'])
            continue
        session_d['votes_per_type'][vote.get('type')] += 1
        if not vote.get('date'):
            logger.warning('vote %s missing date' % vote['_id'])
            continue
        session_d['votes_per_month'][vote['date'].strftime('%Y-%m')] += 1

        # roll calls
        has_rollcalls = False
        for rc in (vote['yes_votes'] + vote['no_votes'] +
                   vote['other_votes']):
            has_rollcalls = True
            session_d['_rollcall_count'] += 1
            if rc.get('leg_id'):
                session_d['_rollcalls_with_leg_id_count'] += 1
            else:
                # keep missing leg_ids
                session_d['unmatched_voters'].add(
                    (term_for_session(abbr, vote['session']),
                     vote['chamber'],
                     rc['name'])
                )

        # check counts if any rollcalls are present
        if has_rollcalls:
            if (len(vote['yes_votes']) != vote['yes_count'] and
                    vote['vote_id'] not in
                    quality_exceptions['votes:bad_yes_count']):
                session_d['bad_vote_counts'].add(vote['vote_id'])
            if (len(vote['no_votes']) != vote['no_count'] and
                    vote['vote_id'] not in
                    quality_exceptions['votes:bad_no_count']):
                session_d['bad_vote_counts'].add(vote['vote_id'])
            if (len(vote['other_votes']) != vote['other_count'] and
                    vote['vote_id'] not in
                    quality_exceptions['votes:bad_other_count']):
                session_d['bad_vote_counts'].add(vote['vote_id'])

    # do logging of unnecessary exceptions
    for qe_type, qes in quality_exceptions.iteritems():
        if qes:
            logger.warning('unnecessary {0} exceptions for {1} votes: \n  {2}'
                           .format(qe_type, len(qes), '\n  '.join(qes)))

    return {'sessions': sessions}


def calculate_percentages(report):
    vote_count = float(report['vote_count']) / 100
    if vote_count:
        report['votes_passed'] = report.pop('_passed_vote_count') / vote_count
        for k in report['votes_per_type'].iterkeys():
            report['votes_per_type'][k] /= vote_count
        for k in report['votes_per_chamber'].iterkeys():
            report['votes_per_chamber'][k] /= vote_count
        for k in report['votes_per_month'].iterkeys():
            report['votes_per_month'][k] /= vote_count
    rollcall_count = float(report.pop('_rollcall_count')) / 100
    if rollcall_count:
        report['rollcalls_with_leg_id'] = (
            report.pop('_rollcalls_with_leg_id_count') / rollcall_count
        )


def vote_report(abbr):
    report = scan_votes(abbr)
    combined_report = combine_reports(report['sessions'], _vote_report_dict())
    for session in report['sessions'].itervalues():
        calculate_percentages(session)
    calculate_percentages(combined_report)
    report.update(combined_report)
    return report
