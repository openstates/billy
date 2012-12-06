from collections import defaultdict

from billy.core import db
from billy.core import settings
from billy.reports.utils import update_common

# semi-optional keys to check for on active legislators
checked_keys = ('photo_url', 'url', 'email', 'transparencydata_id', 'offices')


def scan_legislators(abbr):
    duplicate_sources = defaultdict(int)
    report = {'upper_active_count': 0,
              'lower_active_count': 0,
              'inactive_count': 0,
              '_updated_today_count': 0,
              '_updated_this_month_count': 0,
              '_updated_this_year_count': 0,
             }
    for key in checked_keys:
        report[key] = 0

    # initialize seat counts
    district_seats = {'upper': defaultdict(int), 'lower': defaultdict(int)}
    for district in db.districts.find({'abbr': abbr}):
        district_seats[district['chamber']][district['name']] = \
            district['num_seats']

    for leg in db.legislators.find({settings.LEVEL_FIELD: abbr}):

        # do common details
        update_common(leg, report)

        # most checks only apply to active set
        if leg.get('active'):
            chamber = leg.get('chamber')
            if chamber == 'upper':
                report['upper_active_count'] += 1
            elif chamber == 'lower':
                report['lower_active_count'] += 1
            else:
                # TODO: track these? (executives)
                continue

            # decrement empty seats (if it goes negative, we have too many)
            district_seats[chamber][leg['district']] -= 1

            for key in checked_keys:
                if leg.get(key):
                    report[key] += 1
        else:
            report['inactive_count'] += 1

        for source in leg['sources']:
            duplicate_sources[source['url']] += 1

    report['duplicate_sources'] = []
    for url, n in duplicate_sources.iteritems():
        if n > 1:
            report['duplicate_sources'].append(url)

    # copy over seat issues into report
    report['overfilled_seats'] = []
    report['vacant_seats'] = []
    for chamber, chamber_seats in district_seats.iteritems():
        for seat, count in chamber_seats.iteritems():
            if count < 0:
                report['overfilled_seats'].append((chamber, seat, -count))
            elif count > 0:
                report['vacant_seats'].append((chamber, seat, count))

    return report


def calculate_percentages(report):
    active_count = float(report['lower_active_count'] +
                         report['upper_active_count'])
    total_count = float(active_count + report['inactive_count']) / 100
    if active_count:
        for key in checked_keys:
            report[key] /= (active_count / 100)
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
