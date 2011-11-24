import datetime
from collections import defaultdict

from billy import db

def scan_committees(abbr):
    metadata = db.metadata.find_one({'_id': abbr})
    level = metadata['level']

    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    last_month = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    last_year = datetime.datetime.utcnow() - datetime.timedelta(days=365)

    duplicate_sources = defaultdict(int)
    report = {'upper_count': 0,
              'lower_count': 0,
              'joint_count': 0,
              'empty_count': 0,
              '_updated_today_count': 0,
              '_updated_this_month_count': 0,
              '_updated_this_year_count': 0,
              '_member_count': 0,
              '_members_with_leg_id_count': 0,
              'sourceless': set(),
             }

    for com in db.committees.find({'level': level, level: abbr}):

        # updated checks
        if com['updated_at'] >= yesterday:
            report['_updated_today_count'] += 1
            if com['updated_at'] >= last_month:
                report['_updated_this_month_count'] += 1
                if com['updated_at'] >= last_year:
                    report['_updated_this_year_count'] += 1

        if com['chamber'] == 'upper':
            report['upper_count'] += 1
        elif com['chamber'] == 'lower':
            report['lower_count'] += 1
        elif com['chamber'] == 'joint':
            report['joint_count'] += 1

        # members
        if not com['members']:
            report['empty_count'] += 1

        for member in com['members']:
            report['_member_count'] += 1
            if member.get('leg_id'):
                report['_members_with_leg_id_count'] += 1

        # sources
        for source in com['sources']:
            duplicate_sources[source['url']] += 1
        if not com['sources']:
            report['sourceless'].add(com['_id'])

    report['duplicate_sources'] = []
    for url, n in duplicate_sources.iteritems():
        if n > 1:
            report['duplicate_sources'].append(url)

    return report


def calculate_percentages(report):
    total_count = float(report['lower_count'] + report['upper_count'] +
                        report['joint_count'])/100
    if total_count:
        report['updated_this_year'] = (report.pop('_updated_this_year_count') /
                                       total_count)
        report['updated_this_month'] = (report.pop('_updated_this_month_count')
                                        / total_count)
        report['updated_today'] = (report.pop('_updated_today_count') /
                                   total_count)

    member_count = float(report['_member_count'])/100
    if member_count:
        report['members_with_leg_id'] = (
            report.pop('_members_with_leg_id_count') / member_count)


def committee_report(abbr):
    report = scan_committees(abbr)
    calculate_percentages(report)
    return report
