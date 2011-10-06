#!/usr/bin/env python
import os
import sys
import json
import random

from billy import db
from billy.conf import settings, base_arg_parser

import scrapelib
import lxml.etree
from oyster.client import get_configured_client

def oysterize_versions(state, update_mins=20000):
    oclient = get_configured_client()
    new_bills = list(db.bills.find({'state': state,
                                    'versions.url': {'$exists': True},
                                    #'versions._oyster_id': {'$exists': False}
                                   }))
    print '%s bills with versions to oysterize' % len(new_bills)
    for bill in new_bills:
        for version in bill['versions']:
            if 'url' in version and '_oyster_id' not in version:
                try:
                    _id = oclient.track_url(version['url'],
                                            update_mins=update_mins,
                                            name=version['name'],
                                            state=bill['state'],
                                            session=bill['session'],
                                            chamber=bill['chamber'],
                                            bill_id=bill['bill_id'],
                                            openstates_bill_id=bill['_id'])
                    #version['_oyster_id'] = _id
                except Exception as e:
                    print e

        # save bill after updating all versions
        #db.bills.save(bill, safe=True)


def sfm_sync(state):
    from billy.fulltext.tasks import SuperFastMatchTask
    oclient = get_configured_client()

    new_versions = list(oclient.db.tracked.find({'state': state,
                                     'superfastmatch_id': {'$exists': False}}))
    print '%s new versions to sync' % len(new_versions)

    # load state-specific extract_text
    for newpath in settings.SCRAPER_PATHS:
        sys.path.insert(0, newpath)
    try:
        extract_text = __import__('%s.fulltext' % state,
                                  fromlist=['extract_text']).extract_text
    except ImportError:
        print 'could not import %s.fulltext.extract_text' % state

    for version in new_versions:
        SuperFastMatchTask.delay(version['_id'], extract_text)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='send bill versions to oyster',
                                     parents=[base_arg_parser])
    parser.add_argument('states', nargs='+', help='states to oysterize')
    parser.add_argument('--sfm', action='store_true', default=False,
                        help='sync to SuperFastMatch too')
    args = parser.parse_args()
    settings.update(args)

    for state in args.states:
        print "Oysterizing %s bill versions" % state
        oysterize_versions(state)
    if args.sfm:
        for state in args.states:
            print "syncing %s bill versions to SFM" % state
            sfm_sync(state)


if __name__ == '__main__':
    main()
