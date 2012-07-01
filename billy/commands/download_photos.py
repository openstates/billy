import os
import sys
import subprocess

import boto
from boto.s3.key import Key
import scrapelib

from billy import db
from billy.conf import settings
from billy.commands import BaseCommand

scraper = scrapelib.Scraper(follow_robots=False)

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)


class DownloadPhotos(BaseCommand):

    name = 'download-photos'
    help = 'download latest legislator photos and sync to S3'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='abbreviations for photos to update')

    def handle(self, args):
        s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET)
        bucket = s3conn.create_bucket(settings.AWS_BUCKET)

        for abbr in args.abbrs:

            meta = db.metadata.find_one({'_id': abbr.lower()})
            if not meta:
                print("'{0}' does not exist in the database.".format(abbr))
                sys.exit(1)
            else:
                print("Updating ids for {0}".format(abbr))

            orig_dir = 'photos/original'
            small_dir = 'photos/small'
            large_dir = 'photos/large'
            for d in (orig_dir, small_dir, large_dir):
                if not os.path.exists(d):
                    os.makedirs(d)

            for leg in db.legislators.find({meta['level']: abbr,
                                            'photo_url': {'$exists': True}}):

                fname = os.path.join(orig_dir, '{0}.jpg'.format(leg['_id']))

                # if fname already exists, skip this processing step
                if os.path.exists(fname):
                    continue

                # error retrieving photo, skip it
                try:
                    tmpname, resp = scraper.urlretrieve(leg['photo_url'])
                except scrapelib.HTTPError:
                    continue
                except Exception:
                    continue

                # original size, standardized filenames
                fname = os.path.join(orig_dir, '{0}.jpg'.format(leg['_id']))
                subprocess.check_call(['convert', tmpname, fname])
                k = Key(bucket)
                k.key = fname
                k.set_contents_from_filename(fname)
                k.set_acl('public-read')

                # small - 150x200
                fname = os.path.join(small_dir, '{0}.jpg'.format(leg['_id']))
                subprocess.check_call(['convert', tmpname, '-resize',
                                       '150x200', fname])
                k = Key(bucket)
                k.key = fname
                k.set_contents_from_filename(fname)
                k.set_acl('public-read')
