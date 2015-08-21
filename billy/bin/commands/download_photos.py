import os
import sys
import subprocess

import boto
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat
import scrapelib

from billy.core import db
from billy.core import settings
from billy.bin.commands import BaseCommand

scraper = scrapelib.Scraper()

import logging
logging.getLogger('boto').setLevel(logging.CRITICAL)
log = logging.getLogger('billy')


def _upload(fname, bucket):
    # create cache_headers - 30 days
    headers = {'Cache-Control': 'max-age=2592000'}

    # optimize JPEG
    subprocess.check_call(['jpegoptim', '--strip-all', fname])

    k = Key(bucket)
    k.key = fname
    k.set_contents_from_filename(fname, policy='public-read', headers=headers)


class DownloadPhotos(BaseCommand):

    name = 'download-photos'
    help = 'download latest legislator photos and sync to S3'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='abbreviations for photos to update')

    def handle(self, args):
        s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET,
                                 calling_format=OrdinaryCallingFormat())
        bucket = s3conn.create_bucket(settings.AWS_BUCKET)

        for abbr in args.abbrs:

            meta = db.metadata.find_one({'_id': abbr.lower()})
            if not meta:
                log.critical("'{0}' does not exist in the database.".format(
                    abbr))
                sys.exit(1)
            else:
                log.info("Downloading photos for {0}".format(abbr))

            orig_dir = 'photos/original'
            xsmall_dir = 'photos/xsmall'
            small_dir = 'photos/small'
            large_dir = 'photos/large'
            for d in (orig_dir, xsmall_dir, small_dir, large_dir):
                if not os.path.exists(d):
                    os.makedirs(d)

            for leg in db.legislators.find({settings.LEVEL_FIELD: abbr,
                                            'photo_url': {'$exists': True}},
                                           timeout=False):

                fname = os.path.join(orig_dir, '{0}.jpg'.format(leg['_id']))

                # if fname already exists, skip this processing step
                if os.path.exists(fname):
                    continue

                # error retrieving photo, skip it
                try:
                    tmpname, resp = scraper.urlretrieve(leg['photo_url'])
                except Exception as e:
                    log.critical('error fetching %s: %s', leg['photo_url'], e)
                    continue

                try:
                    # original size, standardized filenames
                    fname = os.path.join(orig_dir,
                                         '{0}.jpg'.format(leg['_id']))
                    subprocess.check_call(['convert', tmpname, fname])
                    _upload(fname, bucket)

                    # xsmall - 50x70
                    fname = os.path.join(xsmall_dir,
                                         '{0}.jpg'.format(leg['_id']))
                    subprocess.check_call(['convert', tmpname, '-resize',
                                           '50x75', fname])
                    _upload(fname, bucket)

                    # small - 150x200
                    fname = os.path.join(small_dir,
                                         '{0}.jpg'.format(leg['_id']))
                    subprocess.check_call(['convert', tmpname, '-resize',
                                           '150x200', fname])
                    _upload(fname, bucket)
                except subprocess.CalledProcessError:
                    print('convert failed for ', fname)
