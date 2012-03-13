#!/usr/bin/env python
import os
import sys
import json
import glob
import logging
import argparse
import unicodecsv

import datetime as dt

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
        # silence error only when alldata is present
        if ('alldata' in options.types and
            str(e.orig_exception) == 'No module named %s' % scraper_type):
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
        return [{
            "type": scraper_type,
            "start_time": dt.datetime.utcnow(),
            "noscraper": True,
            "end_time": dt.datetime.utcnow()
        }]

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

    runs = []

    # Removed from the inner loop due to non-bicameral scrapers
    scrape = {
        "type": scraper_type
    }
    scrape['start_time'] = dt.datetime.utcnow()

    # run scraper against year/session/term
    for time in times:
        for chamber in options.chambers:
            scraper.scrape(chamber, time)

        if scraper_type == 'events' and len(options.chambers) == 2:
            scraper.scrape('other', time)

    scrape['end_time'] = dt.datetime.utcnow()
    runs.append(scrape)

    return runs


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

    report = {}

    if 'legislators' in args.types:
        report['legislators'] = \
                import_legislators(abbrev, settings.BILLY_DATA_DIR)

    if 'bills' in args.types:
        report['bills'] = import_bills(abbrev, settings.BILLY_DATA_DIR,
                                       args.oyster)

    if 'committees' in args.types:
        report['committees'] = \
                import_committees(abbrev, settings.BILLY_DATA_DIR)

    if 'events' in args.types:
        report['events'] = \
                import_events(abbrev, settings.BILLY_DATA_DIR)

    return report


def _do_reports(abbrev, args):
    from billy import db
    from billy.reports.bills import bill_report
    from billy.reports.legislators import legislator_report
    from billy.reports.committees import committee_report

    report = db.reports.find_one({'_id': abbrev})
    if not report:
        report = {'_id': abbrev}

    if 'legislators' in args.types:
        report['legislators'] = legislator_report(abbrev)
    if 'bills' in args.types:
        report['bills'] = bill_report(abbrev)
    if 'committees' in args.types:
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
        what.add_argument('--bills', action='append_const', dest='types',
                          const='bills', help="scrape bill data")
        what.add_argument('--legislators', action='append_const', dest='types',
                          const='legislators', help="scrape legislator data")
        what.add_argument('--committees', action='append_const', dest='types',
                          const='committees', help="scrape committee data")
        what.add_argument('--votes', action='append_const', dest='types',
                          const='votes', help="scrape vote data")
        what.add_argument('--events', action='append_const', dest='types',
                          const='events', help="scrape event data")
        scrape.add_argument('--nonstrict', action='store_false', dest='strict',
                            default=True, help="don't fail immediately when"
                            " encountering validation warning")
        scrape.add_argument('--oyster', action='store_true', dest='oyster',
                            default=False, help="push documents to oyster"
                            " document tracking daemon")
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
        # actions
        parser.add_argument('--scrapeonly', help="run specified scrapers",
                            dest='actions', action="append_const",
                            const="scrape")
        parser.add_argument('--importonly', dest="actions",
                            action="append_const", const="import",
                            help="run specified import process")
        parser.add_argument('--reportonly', help="run specified reports",
                            dest='actions', action="append_const",
                            const="report")

        args = parser.parse_args()

        settings.update(args)

        # inject scraper paths so scraper module can be found
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)

        # get metadata
        module = __import__(args.module)
        metadata = module.metadata
        abbrev = metadata['abbreviation']

        configure_logging(args.module)

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

        if not args.actions:
            if old_scrape_compat:
                args.actions = ['scrape']
            else:
                args.actions = ['scrape', 'update', 'report']

        if not args.types:
            args.types = ['bills', 'legislators', 'votes', 'committees',
                          'events', 'alldata']

        plan = 'billy-update abbr=%s actions=%s types=%s' % (
            args.module, ','.join(args.actions), ','.join(args.types)
        )
        logging.getLogger('billy').info(plan)

        scrape_data = {}

        if 'scrape' in args.actions:
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
                logging.getLogger('billy').warning(
                    'metadata validation error: ' + str(e))

            with open(os.path.join(args.output_dir, 'metadata.json'),
                      'w') as f:
                json.dump(metadata, f, cls=JSONDateEncoder)

            run_record = []
            exec_record = {
                "run_record": run_record,
                "args": sys.argv,
                "state": abbrev
            }

            lex = None

            # run scrapers
            exec_start = dt.datetime.utcnow()
            order = ('legislators', 'committees', 'votes', 'bills', 'events')
            try:
                for stype in order:
                    if stype in args.types:
                        run_record += _run_scraper(stype, args, metadata)
            except Exception as e:
                run_record += [{"exception": e, "type": stype}]
                lex = e

            exec_end = dt.datetime.utcnow()
            exec_record['started'] = exec_start
            exec_record['ended'] = exec_end
            scrape_data['scraped'] = exec_record
            scrape_data['state'] = abbrev

            for record in run_record:
                if "exception" in record:
                    ex = record['exception']
                    record['exception'] = {
                        "type": ex.__class__.__name__,
                        "message": ex.message
                    }
                    scrape_data['failure'] = True
            if lex:
                if 'import' in args.actions:
                    try:
                        db.billy_runs.save(scrape_data, safe=True)
                    except Exception:
                        raise lex
                        # XXX: This should *NEVER* happen, but it has
                        # in the past, so we're going to catch any errors
                        # writing # to pymongo, and raise the original
                        # exception rather then let it look like Mongo's fault.
                        # Thanks for catching this, Thom.
                        #
                        # We loose the stack trace, but the Exception is the
                        # same in every other way.
                        #  -- paultag
                raise

        # imports
        if 'import' in args.actions:
            import_report = _do_imports(abbrev, args)
            scrape_data['imported'] = import_report
            # We're tying the run-logging into the import stage - since import
            # already writes to the DB, we might as well throw this in too.
            db.billy_runs.save(scrape_data, safe=True)

        # reports
        if 'report' in args.actions:
            _do_reports(abbrev, args)

    except ScrapeError as e:
        print 'Error:', e
        sys.exit(1)


def scrape_compat_main():
    main(True)

if __name__ == '__main__':
    main()
