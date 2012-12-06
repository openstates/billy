import datetime
import logging
from collections import defaultdict

from billy.core import db
from billy.core import settings
from billy.utils import term_for_session
from billy.reports.utils import (update_common, get_quality_exceptions,
                                 combine_reports)

logger = logging.getLogger('billy')


def _bill_report_dict():
    return {'upper_count': 0,
            'lower_count': 0,
            'bill_types': defaultdict(int),
            '_updated_this_year_count': 0,
            '_updated_this_month_count': 0,
            '_updated_today_count': 0,
            'actions_unsorted': set(),
            'actionless_count': 0,
            'action_count': 0,
            'actions_per_type': defaultdict(int),
            'actions_per_actor': defaultdict(int),
            'actions_per_month': defaultdict(int),
            'sponsorless_count': 0,
            '_sponsor_count': 0,
            '_sponsors_with_id_count': 0,
            'sponsors_per_type': defaultdict(int),
            '_subjects_count': 0,
            'bills_per_subject': defaultdict(int),
            'versionless_count': 0,
            'version_count': 0,
            'unmatched_sponsors': set(),
            'progress_meter_gaps': set(),
            }


def scan_bills(abbr):
    duplicate_sources = defaultdict(int)
    duplicate_versions = defaultdict(int)
    other_actions = defaultdict(int)
    uncategorized_subjects = defaultdict(int)
    sessions = defaultdict(_bill_report_dict)

    # load exception data into sets of ids indexed by exception type
    quality_exceptions = get_quality_exceptions(abbr)

    for bill in db.bills.find({settings.LEVEL_FIELD: abbr}):
        session_d = sessions[bill['session']]

        # chamber count & bill_types
        if bill['chamber'] == 'lower':
            session_d['lower_count'] += 1
        elif bill['chamber'] == 'upper':
            session_d['upper_count'] += 1
        for type in bill['type']:
            session_d['bill_types'][type] += 1

        update_common(bill, session_d)

        # actions
        last_date = datetime.datetime(1900, 1, 1)
        for action in bill['actions']:
            date = action['date']
            if date < last_date:
                session_d['actions_unsorted'].add(bill['_id'])
            session_d['action_count'] += 1
            for type in action['type']:
                session_d['actions_per_type'][type] += 1
            if 'other' in action['type']:
                other_actions[action['action']] += 1
            session_d['actions_per_actor'][action['actor']] += 1
            session_d['actions_per_month'][date.strftime('%Y-%m')] += 1

        # handle no_actions bills
        if not bill['actions']:
            if bill['_id'] not in quality_exceptions['bills:no_actions']:
                session_d['actionless_count'] += 1
            else:
                quality_exceptions['bills:no_actions'].remove(bill['_id'])

        # sponsors
        for sponsor in bill['sponsors']:
            session_d['_sponsor_count'] += 1
            if sponsor.get('leg_id') or sponsor.get('committee_id'):
                session_d['_sponsors_with_id_count'] += 1
            else:
                # keep list of unmatched sponsors
                session_d['unmatched_sponsors'].add(
                    (term_for_session(abbr, bill['session']), bill['chamber'],
                     sponsor['name'])
                )
            session_d['sponsors_per_type'][sponsor['type']] += 1

        # handle no sponsors bills
        if not bill['sponsors']:
            if bill['_id'] not in quality_exceptions['bills:no_sponsors']:
                session_d['sponsorless_count'] += 1
            else:
                quality_exceptions['bills:no_sponsors'].remove(bill['_id'])

        # subjects
        for subj in bill.get('scraped_subjects', []):
            uncategorized_subjects[subj] += 1
        if bill.get('subjects'):
            session_d['_subjects_count'] += 1
            for subject in bill['subjects']:
                session_d['bills_per_subject'][subject] += 1

        # sources
        for source in bill['sources']:
            duplicate_sources[source['url']] += 1

        # versions
        if not bill['versions']:
            # total num of bills w/o versions
            if bill['_id'] not in quality_exceptions['bills:no_versions']:
                session_d['versionless_count'] += 1
            else:
                quality_exceptions['bills:no_versions'].remove(bill['_id'])
        else:
            # total num of versions
            session_d['version_count'] += len(bill['versions'])
        for doc in bill['versions']:
            duplicate_versions[doc['url']] += 1
        # TODO: add duplicate document detection back in?

        # Check for progress meter gaps.
        progress_meter_gaps = session_d['progress_meter_gaps']
        action_dates = bill['action_dates']
        bill_chamber = bill['chamber']
        other_chamber = dict(lower='upper', upper='lower')[bill_chamber]

        # Check for bills that were signed but didn't pass both chambers.
        if bill['type'] == 'bill':
            if action_dates['signed']:
                if not action_dates['passed_upper']:
                    progress_meter_gaps.add(bill['_id'])
                elif not action_dates['passed_lower']:
                    progress_meter_gaps.add(bill['_id'])

        else:
            # Check for nonbills that were signed but didn't pass their
            # house of origin.
            if action_dates['signed']:
                if not action_dates['passed_' + bill_chamber]:
                    progress_meter_gaps.add(bill['_id'])

        if action_dates['passed_' + other_chamber]:
            if not action_dates['passed_' + bill_chamber]:
                progress_meter_gaps.add(bill['_id'])

    dup_version_urls = []
    dup_source_urls = []
    for url, n in duplicate_versions.iteritems():
        if n > 1:
            dup_version_urls.append(url)
    for url, n in duplicate_sources.iteritems():
        if n > 1:
            dup_source_urls.append(url)

    # do logging of unnecessary exceptions
    for qe_type, qes in quality_exceptions.iteritems():
        if qes:
            logger.warning('unnecessary {0} exceptions for {1} bills: \n  {2}'
                           .format(qe_type, len(qes), '\n  '.join(qes)))

    return {'duplicate_versions': dup_version_urls,
            'duplicate_sources': dup_source_urls,
            'other_actions': other_actions.items(),
            'uncategorized_subjects': uncategorized_subjects.items(),
            'sessions': sessions,
            'progress_meter_gaps': []
           }


def calculate_percentages(report):
    # general bill stuff
    bill_count = float(report['upper_count'] + report['lower_count']) / 100
    if bill_count:
        report['updated_this_year'] = (report.pop('_updated_this_year_count') /
                                       bill_count)
        report['updated_this_month'] = (report.pop('_updated_this_month_count')
                                        / bill_count)
        report['updated_today'] = (report.pop('_updated_today_count') /
                                   bill_count)
        report['have_subjects'] = report.pop('_subjects_count') / bill_count

    # actions
    action_count = float(report['action_count']) / 100
    if action_count:
        for k in report['actions_per_type'].iterkeys():
            report['actions_per_type'][k] /= action_count
        for k in report['actions_per_actor'].iterkeys():
            report['actions_per_actor'][k] /= action_count
        for k in report['actions_per_month'].iterkeys():
            report['actions_per_month'][k] /= action_count

    # sponsors
    _sponsor_count = float(report.pop('_sponsor_count')) / 100
    if _sponsor_count:
        report['sponsors_with_id'] = (
            report.pop('_sponsors_with_id_count') / _sponsor_count)
        for k in report['sponsors_per_type'].iterkeys():
            report['sponsors_per_type'][k] /= _sponsor_count


def bill_report(abbr):
    report = scan_bills(abbr)
    combined_report = combine_reports(report['sessions'],
                                      _bill_report_dict())
    for session in report['sessions'].itervalues():
        calculate_percentages(session)
    calculate_percentages(combined_report)
    report.update(combined_report)
    return report
