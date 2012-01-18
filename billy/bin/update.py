#!/usr/bin/env python
import glob
import logging
import os
import sys
import argparse
import json
import unicodecsv

from billy import db
from billy.conf import settings, base_arg_parser
from billy.scrape import (ScrapeError, JSONDateEncoder, get_scraper,
                          check_sessions)
from billy.utils import configure_logging
from billy.scrape.validator import DatetimeValidator


def _clear_scraped_data(output_dir, scraper_type):
    # make or clear directory for this type
    path = os.path.join(output_dir, scraper_type)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != 17:
            raise e
        else:
            for f in glob.glob(path + '/*.json'):
                os.remove(f)

def _get_configured_scraper(scraper_type, options, metadata):
    try:
        ScraperClass = get_scraper(options.module, scraper_type)
    except ScrapeError as e:
        # silence error only for --alldata
        if (options.alldata and str(e.orig_exception) ==
            'No module named %s' % scraper_type):
            return None
        else:
            raise e

    opts = {'output_dir': options.output_dir,
            'no_cache': options.no_cache,
            'requests_per_minute': options.rpm,
            'timeout': options.timeout,
            'strict_validation': options.strict,
            'retry_attempts': settings.SCRAPELIB_RETRY_ATTEMPTS,
            'retry_wait_seconds': settings.SCRAPELIB_RETRY_WAIT_SECONDS,
        }
    if options.fastmode:
        opts['requests_per_minute'] = 0
        opts['use_cache_first'] = True
    scraper = ScraperClass(metadata, **opts)
    return scraper

def _run_scraper(scraper_type, options, metadata):
    """
        scraper_type: bills, legislators, committees, votes
    """
    _clear_scraped_data(options.output_dir, scraper_type)
    scraper = _get_configured_scraper(scraper_type, options, metadata)
    if not scraper:
        return

    # times: the list to iterate over for second scrape param
    if scraper_type in ('bills', 'votes', 'events'):
        if not options.sessions:
            if options.terms:
                times = []
                for term in options.terms:
                    scraper.validate_term(term)
                    for metaterm in metadata['terms']:
                        if term == metaterm['name']:
                            times.extend(metaterm['sessions'])
            else:
                latest_session = metadata['terms'][-1]['sessions'][-1]
                print('No session specified, using latest "%s"' %
                      latest_session)
                times = [latest_session]
        else:
            times = options.sessions

        # validate sessions
        for time in times:
            scraper.validate_session(time)
    elif scraper_type in ('legislators', 'committees'):
        if not options.terms:
            latest_term = metadata['terms'][-1]['name']
            print 'No term specified, using latest "%s"' % latest_term
            times = [latest_term]
        else:
            times = options.terms

        # validate terms
        for time in times:
            scraper.validate_term(time, scraper.latest_only)

    # run scraper against year/session/term
    for time in times:
        for chamber in options.chambers:
            scraper.scrape(chamber, time)
        if scraper_type == 'events' and len(options.chambers) == 2:
            scraper.scrape('other', time)


def _scrape_solo_bills(options, metadata):
    _clear_scraped_data(options.output_dir, 'bills')
    scraper = _get_configured_scraper('bills', options, metadata)

    if len(options.chambers) == 1:
        chamber = options.chambers[0]
    else:
        raise ScrapeError('must specify --chamber when providing a --bill')
    if len(options.sessions):
        session = list(options.sessions)[0]
    else:
        raise ScrapeError('must specify --session when providing a --bill')

    for bill_id in options.solo_bills:
        scraper.scrape_bill(chamber, session, bill_id)


def _do_imports(abbrev, args):
    # do imports here so that scrapers don't depend on mongo
    from billy.importers.metadata import import_metadata
    from billy.importers.bills import import_bills
    from billy.importers.legislators import import_legislators
    from billy.importers.committees import import_committees
    from billy.importers.events import import_events

    # always import metadata and districts
    import_metadata(abbrev, settings.BILLY_DATA_DIR)

    dist_filename = os.path.join(settings.BILLY_MANUAL_DATA_DIR, 'districts',
                                 '%s.csv' % abbrev)
    if os.path.exists(dist_filename):
        dist_csv = unicodecsv.DictReader(open(dist_filename))
        for dist in dist_csv:
            dist['_id'] = '%(abbr)s-%(chamber)s-%(name)s' % dist
            dist['boundary_id'] = dist['boundary_id'] % dist
            dist['num_seats'] = int(dist['num_seats'])
            db.districts.save(dist, safe=True)
    else:
        print "%s not found, continuing without districts" % dist_filename

    if args.legislators:
        import_legislators(abbrev, settings.BILLY_DATA_DIR)
    if args.bills:
        import_bills(abbrev, settings.BILLY_DATA_DIR)
    if args.committees:
        import_committees(abbrev, settings.BILLY_DATA_DIR)
    if args.events:
        import_events(abbrev, settings.BILLY_DATA_DIR)


def _do_reports(abbrev, args):
    from billy import db
    from billy.reports.bills import bill_report
    from billy.reports.legislators import legislator_report
    from billy.reports.committees import committee_report

    report = db.reports.find_one({'_id': abbrev})
    if not report:
        report = {'_id': abbrev}

    if args.legislators:
        report['legislators'] = legislator_report(abbrev)
    if args.bills:
        report['bills'] = bill_report(abbrev)
    if args.committees:
        report['committees'] = committee_report(abbrev)

    db.reports.save(report, safe=True)


def main(old_scrape_compat=False):
    try:
        parser = argparse.ArgumentParser(
          description='Scrape legislative data, saving data to disk as JSON.',
          parents=[base_arg_parser],
        )

        what = parser.add_argument_group('what to scrape',
                                 'flags that help select what data to scrape')
        scrape = parser.add_argument_group('scraper config',
                                 'settings for the scraper')

        parser.add_argument('module', type=str, help='scraper module (eg. nc)')
        what.add_argument('-s', '--session', action='append',
                            dest='sessions', help='session(s) to scrape')
        what.add_argument('-t', '--term', action='append', dest='terms',
                            help='term(s) to scrape')
        what.add_argument('--upper', action='store_true', dest='upper',
                            default=False, help='scrape upper chamber')
        what.add_argument('--lower', action='store_true', dest='lower',
                            default=False, help='scrape lower chamber')
        what.add_argument('--bills', action='store_true', dest='bills',
                            default=False, help="scrape bill data")
        what.add_argument('--legislators', action='store_true',
                            dest='legislators', default=False,
                            help="scrape legislator data")
        what.add_argument('--committees', action='store_true',
                            dest='committees', default=False,
                            help="scrape committee data")
        what.add_argument('--votes', action='store_true', dest='votes',
                            default=False, help="scrape vote data")
        what.add_argument('--events', action='store_true', dest='events',
                            default=False, help='scrape event data')
        what.add_argument('--alldata', action='store_true', dest='alldata',
                            default=False,
                            help="scrape all available types of data")
        scrape.add_argument('--strict', action='store_true', dest='strict',
                            default=False, help="fail immediately when"
                            "encountering validation warning")
        scrape.add_argument('-n', '--no_cache', action='store_true',
                            dest='no_cache', help="don't use web page cache")
        scrape.add_argument('--fastmode', help="scrape in fast mode",
                            action="store_true", default=False)
        scrape.add_argument('-r', '--rpm', action='store', type=int,
                            dest='rpm', default=60)
        scrape.add_argument('--timeout', action='store', type=int,
                            dest='timeout', default=10)
        scrape.add_argument('--retries', type=int,
                            dest='SCRAPELIB_RETRY_ATTEMPTS')
        scrape.add_argument('--retry_wait', type=int,
                            dest='SCRAPELIB_RETRY_WAIT_SECONDS')
        parser.add_argument('--bill', action='append', dest='solo_bills',
                            help='individual bill id(s) to scrape')
        # old_scrape_compat defaults scrape to true, if being called as scrape
        parser.add_argument('--scrape', help="run specified scrapers",
                            action="store_true", default=old_scrape_compat)
        parser.add_argument('--import', dest="do_import",
                            help="run specified import process",
                            action="store_true", default=False)
        parser.add_argument('--report', help="run specified reports",
                            action="store_true", default=False)

        args = parser.parse_args()

        settings.update(args)

        # inject scraper paths so scraper module can be found
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)

        # get metadata
        module = __import__(args.module)
        metadata = module.metadata
        abbrev = metadata['abbreviation']

        configure_logging(args.verbose, args.module)

        # make output dir
        args.output_dir = os.path.join(settings.BILLY_DATA_DIR, abbrev)
        try:
            os.makedirs(args.output_dir)
        except OSError as e:
            if e.errno != 17:
                raise e

        # determine time period to run for
        if args.terms:
            for term in metadata['terms']:
                if term in args.terms:
                    args.sessions.extend(term['sessions'])
        args.sessions = set(args.sessions or [])

        # determine chambers
        args.chambers = []
        if args.upper:
            args.chambers.append('upper')
        if args.lower:
            args.chambers.append('lower')
        if not args.chambers:
            args.chambers = ['upper', 'lower']

        if not (args.scrape or args.do_import or args.report
                or args.solo_bills):
            raise ScrapeError("Must specify at least one of --scrape, "
                              "--import, --report")

        # determine which types to process
        if not (args.bills or args.legislators or args.votes or
                args.committees or args.events or args.alldata or
                args.solo_bills):
            raise ScrapeError("Must specify at least one of --bills, "
                              "--legislators, --committees, --votes, --events,"
                              " --alldata")
        if args.alldata:
            args.bills = True
            args.legislators = True
            args.votes = True
            args.committees = True


        # do full scrape if not solo bills, import only, or report only
        if args.scrape:
            # validate then write metadata

            if hasattr(module, 'session_list'):
                session_list = module.session_list()
            else:
                session_list = []
            check_sessions(metadata, session_list)

            try:
                schema_path = os.path.join(os.path.split(__file__)[0],
                                           '../schemas/metadata.json')
                schema = json.load(open(schema_path))

                validator = DatetimeValidator()
                validator.validate(metadata, schema)
            except ValueError as e:
                logging.getLogger('billy').warning('metadata validation error: '
                                                         + str(e))

            with open(os.path.join(args.output_dir, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, cls=JSONDateEncoder)

            # run scrapers
            if args.legislators:
                _run_scraper('legislators', args, metadata)
            if args.committees:
                _run_scraper('committees', args, metadata)
            if args.votes:
                _run_scraper('votes', args, metadata)
            if args.events:
                _run_scraper('events', args, metadata)
            if args.bills:
                _run_scraper('bills', args, metadata)

        elif args.solo_bills:
            _scrape_solo_bills(args, metadata)

        # imports
        if args.do_import:
            _do_imports(abbrev, args)

        # reports
        if args.report:
            _do_reports(abbrev, args)


    except ScrapeError as e:
        print 'Error:', e
        sys.exit(1)

def scrape_compat_main():
    main(True)

if __name__ == '__main__':
    main()
