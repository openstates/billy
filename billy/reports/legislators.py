import datetime
from collections import defaultdict

from billy import db

# semi-optional keys to check for on active legislators
checked_keys = ('photo_url', 'url', 'votesmart_id', 'transparencydata_id')


def scan_legislators(abbr):
    metadata = db.metadata.find_one({'_id': abbr})
    level = metadata['level']

    yesterday = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    last_month = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    last_year = datetime.datetime.utcnow() - datetime.timedelta(days=365)

    duplicate_sources = defaultdict(int)
    report = {'upper_active_count': 0,
              'lower_active_count': 0,
              'inactive_count': 0,
              '_updated_today_count': 0,
              '_updated_this_month_count': 0,
              '_updated_this_year_count': 0,
              'sourceless': set(),
             }
    seats_filled = {'upper': defaultdict(int), 'lower': defaultdict(int)}
    for key in checked_keys:
        report[key] = 0

    for leg in db.legislators.find({'level': level, level: abbr}):

        # updated checks
        if leg['updated_at'] >= yesterday:
            report['_updated_today_count'] += 1
            if leg['updated_at'] >= last_month:
                report['_updated_this_month_count'] += 1
                if leg['updated_at'] >= last_year:
                    report['_updated_this_year_count'] += 1

        # most checks only apply to active set
        if leg.get('active'):
            if leg['chamber'] == 'upper':
                report['upper_active_count'] += 1
            elif leg['chamber'] == 'lower':
                report['lower_active_count'] += 1

            seats_filled[leg['chamber']][leg['district']] += 1
            # TODO: check seats_filled against districts

            for key in checked_keys:
                if leg.get(key):
                    report[key] += 1
        else:
            report['inactive_count'] += 1

        # sources
        for source in leg['sources']:
            duplicate_sources[source['url']] += 1
        if not leg['sources']:
            report['sourceless'].add(leg['_id'])

    report['duplicate_sources'] = []
    for url, n in duplicate_sources.iteritems():
        if n > 1:
            report['duplicate_sources'].append(url)

    return report


def calculate_percentages(report):
    active_count = float(report['lower_active_count'] +
                         report['upper_active_count'])
    total_count = active_count + float(report['inactive_count'])/100
    if active_count:
        for key in checked_keys:
            report[key] /= (active_count/100)
    if total_count:
        report['updated_this_year'] = (report.pop('_updated_this_year_count') /
                                       total_count)
        report['updated_this_month'] = (report.pop('_updated_this_month_count')
                                        / total_count)
        report['updated_today'] = (report.pop('_updated_today_count') /
                                   total_count)


def legislator_report(abbr):
    report = scan_legislators(abbr)
    calculate_percentages(report)
    return report
