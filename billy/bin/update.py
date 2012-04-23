#!/usr/bin/env python
import os
import sys
import json
import glob
import logging
import argparse
import traceback
import unicodecsv

import datetime as dt

from billy import db
from billy.conf import settings, base_arg_parser
from billy.scrape import (ScrapeError, JSONDateEncoder, get_scraper,
                          check_sessions)
from billy.utils import configure_logging, term_for_session
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
            'strict_validation': options.strict,
            'requests_per_minute': options.rpm,
           }
    if options.fastmode:
        opts['requests_per_minute'] = 0
        opts['cache_write_only'] = False
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


    runs = []

    # Removed from the inner loop due to non-bicameral scrapers
    scrape = {
        "type": scraper_type
    }
    scrape['start_time'] = dt.datetime.utcnow()

    if scraper_type in ('bills', 'votes', 'events'):
        times = options.sessions
        for time in times:
            scraper.validate_session(time)
    elif scraper_type in ('committees', 'legislators'):
        times = options.terms
        for time in times:
            scraper.validate_term(time, scraper.latest_only)

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
    # do imports here so that scrape doesn't depend on mongo
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
          description='update billy data',
          parents=[base_arg_parser],
        )

        what = parser.add_argument_group('what to scrape',
                                 'flags that help select what data to scrape')
        scrape = parser.add_argument_group('scraper config',
                                 'settings for the scraper')

        parser.add_argument('module', type=str, help='scraper module (eg. nc)')
        what.add_argument('-s', '--session', action='append',
                            dest='sessions', default=[],
                          help='session(s) to scrape')
        what.add_argument('-t', '--term', action='append', dest='terms',
                            help='term(s) to scrape', default=[])
        for arg in ('upper', 'lower'):
            what.add_argument('--' + arg, action='append_const',
                              dest='chambers', const=arg)
        for arg in ('bills', 'legislators', 'committees', 'votes', 'events'):
            what.add_argument('--' + arg, action='append_const', dest='types',
                              const=arg)
        scrape.add_argument('--nonstrict', action='store_false', dest='strict',
                            default=True, help="don't fail immediately when"
                            " encountering validation warning")
        scrape.add_argument('--oyster', action='store_true', dest='oyster',
                            default=False, help="push documents to oyster"
                            " document tracking daemon")
        scrape.add_argument('--fastmode', help="scrape in fast mode",
                            action="store_true", default=False)
        scrape.add_argument('-r', '--rpm', action='store', type=int,
                            dest='rpm', default=60)
        scrape.add_argument('--timeout', action='store', type=int,
                            dest='SCRAPELIB_TIMEOUT', default=10)
        scrape.add_argument('--retries', type=int,
                            dest='SCRAPELIB_RETRY_ATTEMPTS')
        scrape.add_argument('--retry_wait', type=int,
                            dest='SCRAPELIB_RETRY_WAIT_SECONDS')
        # actions
        for arg in ('scrape', 'import', 'report'):
            parser.add_argument('--' + arg, dest='actions',
                                action="append_const", const=arg,
                                help='only run %s step' % arg)

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

        # configure oyster
        if args.oyster:
            from oyster.conf import settings as oyster_settings
            oyster_settings.DOCUMENT_CLASSES[args.module + ':billtext'] = module.document_class

        # make output dir
        args.output_dir = os.path.join(settings.BILLY_DATA_DIR, abbrev)
        try:
            os.makedirs(args.output_dir)
        except OSError as e:
            if e.errno != 17:
                raise e

        # if terms aren't set, use latest
        if not args.terms:
            if args.sessions:
                for session in args.sessions:
                    args.terms.append(
                        term_for_session(metadata['abbreviation'], session,
                                         metadata))
                args.terms = list(set(args.terms or []))
            else:
                latest_term = metadata['terms'][-1]['name']
                args.terms = [latest_term]
        # only set sessions from terms if sessions weren't set
        elif not args.sessions:
            for term in metadata['terms']:
                if term['name'] in args.terms:
                    args.sessions.extend(term['sessions'])
            # dedup sessions
            args.sessions = list(set(args.sessions or []))

        if not args.sessions:
            args.sessions = [metadata['terms'][-1]['sessions'][-1]]

        # determine chambers
        if not args.chambers:
            args.chambers = ['upper', 'lower']

        if not args.actions:
            if old_scrape_compat:
                args.actions = ['scrape']
            else:
                args.actions = ['scrape', 'import', 'report']

        if not args.types:
            args.types = ['bills', 'legislators', 'votes', 'committees',
                          'events', 'alldata']

        plan = """billy-update abbr=%s
    actions=%s
    types=%s
    sessions=%s
    terms=%s""" % (args.module, ','.join(args.actions), ','.join(args.types),
                   ','.join(args.sessions), ','.join(args.terms))
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
            exc_traceback = None

            # run scrapers
            exec_start = dt.datetime.utcnow()
            order = ('legislators', 'committees', 'votes', 'bills', 'events')
            try:
                for stype in order:
                    if stype in args.types:
                        run_record += _run_scraper(stype, args, metadata)
            except Exception as e:
                _traceback = _, _, exc_traceback = sys.exc_info()
                run_record += [{"exception": e, "type": stype }]
                lex = e

            exec_end = dt.datetime.utcnow()
            exec_record['started'] = exec_start
            exec_record['ended'] = exec_end
            scrape_data['scraped'] = exec_record
            scrape_data['state'] = abbrev

            for record in run_record:
                if "exception" in record:
                    ex = record['exception']
                    fb = traceback.format_exception(*_traceback)
                    trace = ""
                    for t in fb:
                        trace += t
                    record['exception'] = {
                        "type": ex.__class__.__name__,
                        "message": ex.message,
                        'traceback': trace
                    }
                    scrape_data['failure'] = True
            if lex:
                if 'import' in args.actions:
                    try:
                        db.billy_runs.save(scrape_data, safe=True)
                    except Exception:
                        raise lex, None, exc_traceback
                        # XXX: This should *NEVER* happen, but it has
                        # in the past, so we're going to catch any errors
                        # writing # to pymongo, and raise the original
                        # exception rather then let it look like Mongo's fault.
                        # Thanks for catching this, Thom.
                        #
                        # We lose the stack trace, but the Exception is the
                        # same in every other way.
                        #  -- paultag
                raise

        # imports
        if 'import' in args.actions:
            print 'doing import'
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
