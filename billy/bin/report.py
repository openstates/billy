#!/usr/bin/env python
from billy import db
from billy.conf import settings, base_arg_parser
from billy.reports.bills import bill_report

def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='generate reports',
                                     parents=[base_arg_parser])
    parser.add_argument('abbrs', nargs='+',
                        help='states to update reports for')
    args = parser.parse_args()
    settings.update(args)

    for abbr in args.abbrs:
        report = db.reports.find_one({'_id': abbr})
        if not report:
            report = {'_id': abbr}
        print 'updating %s reports...' % abbr
        report['bills'] = bill_report(abbr)

    db.reports.save(report, safe=True)

if __name__ == '__main__':
    main()
