#!/usr/bin/env python
import csv
import argparse

from billy.conf import base_arg_parser, settings
from billy import db

def import_district_csv(filename):
    csvfile = csv.DictReader(open(filename))
    for dist in csvfile:

def main():
    parser = argparse.ArgumentParser(
        description='Populate database with district information.',
        parents=[base_arg_parser],
    )

    parser.add_argument('files', metavar='DISTRICT-FILE', type=str, nargs='+',
                help=('the path to the district CSV file to import'))

    args = parser.parse_args()

    settings.update(args)

    for file in args.files:
        import_district_csv(file)


if __name__ == '__main__':
    main()
