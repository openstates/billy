#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import pdb
import json
import glob
import logging
import inspect
import argparse
import traceback
import importlib
import unicodecsv

import datetime as dt

from billy.core import db
from billy.core import settings, base_arg_parser
from billy.scrape import ScrapeError, get_scraper, check_sessions
from billy.utils import term_for_session
from billy.scrape.validator import DatetimeValidator


def _clear_scraped_data(output_dir, scraper_type=''):
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
        if 'alldata' in options.types and ('no %s scraper found in' % scraper_type) in str(e):
            return None
        else:
            raise e

    return ScraperClass(metadata,
                        output_dir=options.output_dir,
                        strict_validation=options.strict,
                        fastmode=options.fastmode)


def _is_old_scrape(f):
    argspec = inspect.getargspec(f)
    return 'chamber' in argspec.args


def _run_scraper(scraper_type, options, metadata):
    """
        scraper_type: bills, legislators, committees, votes
    """
    _clear_scraped_data(options.output_dir, scraper_type)
    if scraper_type == 'speeches':
        _clear_scraped_data(options.output_dir, 'events')

    scraper = _get_configured_scraper(scraper_type, options, metadata)
    ua_email = os.environ.get('BILLY_UA_EMAIL')
    if ua_email:
        scraper.user_agent += ' ({})'.format(ua_email)
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

    if scraper_type in ('bills', 'votes', 'events', 'speeches'):
        times = options.sessions
        for time in times:
            scraper.validate_session(time, scraper.latest_only)
    elif scraper_type in ('committees', 'legislators'):
        times = options.terms
        for time in times:
            scraper.validate_term(time, scraper.latest_only)

    # run scraper against year/session/term
    for time in times:
        # old style
        chambers = options.chambers
        if scraper_type == 'events' and len(options.chambers) == 2:
            chambers.append('other')

        if _is_old_scrape(scraper.scrape):
            for chamber in chambers:
                scraper.scrape(chamber, time)
        else:
            scraper.scrape(time, chambers=chambers)

        # error out if events or votes don't scrape anything
        if not scraper.object_count and scraper_type not in ('events',
                                                             'votes'):
            raise ScrapeError("%s scraper didn't save any objects" %
                              scraper_type)

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
    from billy.importers.speeches import import_speeches

    # always import metadata and districts
    import_metadata(abbrev)
    report = {}

    if 'legislators' in args.types:
        report['legislators'] = \
            import_legislators(abbrev, settings.BILLY_DATA_DIR)

    if 'bills' in args.types:
        report['bills'] = import_bills(abbrev, settings.BILLY_DATA_DIR)

    if 'committees' in args.types:
        report['committees'] = \
            import_committees(abbrev, settings.BILLY_DATA_DIR)

    if 'events' in args.types or 'speeches' in args.types:
        report['events'] = import_events(abbrev, settings.BILLY_DATA_DIR)

    if 'speeches' in args.types:
        report['speeches'] = import_speeches(abbrev, settings.BILLY_DATA_DIR)

    return report


def _do_reports(abbrev, args):
    from billy.core import db
    from billy.reports.bills import bill_report
    from billy.reports.votes import vote_report
    from billy.reports.legislators import legislator_report
    from billy.reports.committees import committee_report
    from billy.reports.speeches import speech_report

    report = db.reports.find_one({'_id': abbrev})
    if not report:
        report = {'_id': abbrev}

    if 'legislators' in args.types:
        report['legislators'] = legislator_report(abbrev)
    if 'bills' in args.types:
        report['bills'] = bill_report(abbrev)
        report['votes'] = vote_report(abbrev)
    if 'committees' in args.types:
        report['committees'] = committee_report(abbrev)
    if 'speeches' in args.types:
        report['speeches'] = speech_report(abbrev)

    db.reports.save(report, safe=True)


def main():
    try:
        parser = argparse.ArgumentParser(
            description='update billy data',
            parents=[base_arg_parser],
        )

        what = parser.add_argument_group(
            'what to scrape', 'flags that help select what data to scrape')
        scrape = parser.add_argument_group('scraper config',
                                           'settings for the scraper')

        parser.add_argument('module', type=str, help='scraper module (eg. nc)')
        parser.add_argument('--pdb', action='store_true', default=False,
                            help='invoke PDB when exception is raised')
        parser.add_argument('--ipdb', action='store_true', default=False,
                            help='invoke PDB when exception is raised')
        parser.add_argument('--pudb', action='store_true', default=False,
                            help='invoke PUDB when exception is raised')
        what.add_argument('-s', '--session', action='append',
                          dest='sessions', default=[],
                          help='session(s) to scrape')
        what.add_argument('-t', '--term', action='append', dest='terms',
                          help='term(s) to scrape', default=[])

        for arg in ('upper', 'lower'):
            what.add_argument('--' + arg, action='append_const',
                              dest='chambers', const=arg)
        for arg in ('bills', 'legislators', 'committees',
                    'votes', 'events', 'speeches'):
            what.add_argument('--' + arg, action='append_const', dest='types',
                              const=arg)
        for arg in ('scrape', 'import', 'report', 'session-list'):
            parser.add_argument('--' + arg, dest='actions',
                                action="append_const", const=arg,
                                help='only run %s step' % arg)

        # special modes for debugging
        scrape.add_argument('--nonstrict', action='store_false', dest='strict',
                            default=True, help="don't fail immediately when"
                            " encountering validation warning")
        scrape.add_argument('--fastmode', help="scrape in fast mode",
                            action="store_true", default=False)

        # scrapelib overrides
        scrape.add_argument('-r', '--rpm', action='store', type=int,
                            dest='SCRAPELIB_RPM')
        scrape.add_argument('--timeout', action='store', type=int,
                            dest='SCRAPELIB_TIMEOUT')
        scrape.add_argument('--retries', type=int,
                            dest='SCRAPELIB_RETRY_ATTEMPTS')
        scrape.add_argument('--retry_wait', type=int,
                            dest='SCRAPELIB_RETRY_WAIT_SECONDS')

        args = parser.parse_args()

        if args.pdb or args.pudb or args.ipdb:
            _debugger = pdb
            if args.pudb:
                try:
                    import pudb
                    _debugger = pudb
                except ImportError:
                    pass
            if args.ipdb:
                try:
                    import ipdb
                    _debugger = ipdb
                except ImportError:
                    pass

            # turn on PDB-on-error mode
            # stolen from http://stackoverflow.com/questions/1237379/
            # if this causes problems in interactive mode check that page
            def _tb_info(type, value, tb):
                traceback.print_exception(type, value, tb)
                _debugger.pm()
            sys.excepthook = _tb_info

        # inject scraper paths so scraper module can be found
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)

        # get metadata
        module = importlib.import_module(args.module)
        metadata = module.metadata
        module_settings = getattr(module, 'settings', {})
        abbrev = metadata['abbreviation']

        # load module settings, then command line settings
        settings.update(module_settings)
        settings.update(args)

        # make output dir
        args.output_dir = os.path.join(settings.BILLY_DATA_DIR, abbrev)

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
            args.actions = ['scrape', 'import', 'report']

        if not args.types:
            args.types = ['bills', 'legislators', 'votes', 'committees',
                          'alldata']

            if 'events' in metadata['feature_flags']:
                args.types.append('events')

            if 'speeches' in metadata['feature_flags']:
                args.types.append('speeches')

        plan = """billy-update abbr=%s
    actions=%s
    types=%s
    sessions=%s
    terms=%s""" % (args.module, ','.join(args.actions), ','.join(args.types),
                   ','.join(args.sessions), ','.join(args.terms))
        logging.getLogger('billy').info(plan)

        scrape_data = {}

        if 'scrape' in args.actions:
            _clear_scraped_data(args.output_dir)

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

            run_record = []
            exec_record = {
                "run_record": run_record,
                "args": sys.argv,
            }

            lex = None
            exc_traceback = None

            # start to run scrapers
            exec_start = dt.datetime.utcnow()

            # scraper order matters
            order = ('legislators', 'committees', 'votes', 'bills',
                     'events', 'speeches')
            _traceback = None
            try:
                for stype in order:
                    if stype in args.types:
                        run_record += _run_scraper(stype, args, metadata)
            except Exception as e:
                _traceback = _, _, exc_traceback = sys.exc_info()
                run_record += [{"exception": e, "type": stype}]
                lex = e

            exec_end = dt.datetime.utcnow()
            exec_record['started'] = exec_start
            exec_record['ended'] = exec_end
            scrape_data['scraped'] = exec_record
            scrape_data['abbr'] = abbrev

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
            import_report = _do_imports(abbrev, args)
            scrape_data['imported'] = import_report
            # We're tying the run-logging into the import stage - since import
            # already writes to the DB, we might as well throw this in too.
            db.billy_runs.save(scrape_data, safe=True)

        # reports
        if 'report' in args.actions:
            _do_reports(abbrev, args)

        if 'session-list' in args.actions:
            if hasattr(module, 'session_list'):
                print("\n".join(module.session_list()))
            else:
                raise ScrapeError('session_list() is not defined')

    except ScrapeError as e:
        logging.getLogger('billy').critical('Error: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
