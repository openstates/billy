#!/usr/bin/env python
from billy import db
from billy.conf import settings, base_arg_parser
from billy.utils import configure_logging
from billy.reports.bills import bill_report
from billy.reports.legislators import legislator_report
from billy.reports.committees import committee_report

def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='generate reports',
                                     parents=[base_arg_parser])
    parser.add_argument('abbrs', nargs='+',
                        help='states to update reports for')
    args = parser.parse_args()
    settings.update(args)
    configure_logging(args.verbose)

    for abbr in args.abbrs:
        report = db.reports.find_one({'_id': abbr})
        if not report:
            report = {'_id': abbr}
        print 'updating %s reports...' % abbr
        report['bills'] = bill_report(abbr)
        report['legislators'] = legislator_report(abbr)
        report['committees'] = committee_report(abbr)

    db.reports.save(report, safe=True)

if __name__ == '__main__':
    main()
