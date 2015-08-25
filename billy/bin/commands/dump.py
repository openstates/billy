#!/usr/bin/env python
import datetime
import json
import logging
import os
import re
import urllib
import zipfile
import unicodecsv

from billy.core import settings
from billy.utils import metadata
from billy.bin.commands import BaseCommand
from billy.core import db

import scrapelib
import validictory
import boto
from boto.s3.key import Key
from boto.s3.connection import OrdinaryCallingFormat


def extract_fields(d, fields, delimiter='|'):
    """ get values out of an object ``d`` for saving to a csv """
    rd = {}
    for f in fields:
        v = d.get(f, None)
        if isinstance(v, (str, unicode)):
            v = v.encode('utf8')
        elif isinstance(v, list):
            v = delimiter.join(v)
        rd[f] = v
    return rd


# TODO: make prefix/use_cname configurable
def upload(abbr, filename, type, s3_prefix='downloads/', use_cname=True):
    today = datetime.date.today()

    # build URL
    s3_bucket = settings.AWS_BUCKET
    s3_path = '%s%s-%02d-%02d-%s-%s.zip' % (s3_prefix, today.year, today.month,
                                            today.day, abbr, type)
    if use_cname:
        s3_url = 'http://%s/%s' % (s3_bucket, s3_path)
    else:
        s3_url = 'http://%s.s3.amazonaws.com/%s' % (s3_bucket, s3_path)

    # S3 upload
    s3conn = boto.connect_s3(settings.AWS_KEY, settings.AWS_SECRET,
                             calling_format=OrdinaryCallingFormat())
    bucket = s3conn.create_bucket(s3_bucket)
    k = Key(bucket)
    k.key = s3_path
    logging.info('beginning upload to %s' % s3_url)
    k.set_contents_from_filename(filename)
    k.set_acl('public-read')

    meta = metadata(abbr)
    meta['latest_%s_url' % type] = s3_url
    meta['latest_%s_date' % type] = datetime.datetime.utcnow()
    db.metadata.save(meta, safe=True)

    logging.info('uploaded to %s' % s3_url)

# JSON ################################


class APIValidator(validictory.SchemaValidator):
    def validate_type_datetime(self, val):
        if not isinstance(val, basestring):
            return False

        return re.match(r'^\d{4}-\d\d-\d\d( \d\d:\d\d:\d\d)?$', val)


def api_url(path):
    return "%s%s/?apikey=%s" % (settings.API_BASE_URL, urllib.quote(path),
                                settings.API_KEY)

# CSV ################################


def _make_csv(abbr, name, fields):
    filename = '/tmp/{0}_{1}'.format(abbr, name)
    f = unicodecsv.DictWriter(open(filename, 'w'), fields)
    f.writerow(dict(zip(fields, fields)))
    return filename, f


def dump_legislator_csvs(abbr):
    leg_fields = ('leg_id', 'full_name', 'first_name', 'middle_name',
                  'last_name', 'suffixes', 'nickname', 'active',
                  settings.LEVEL_FIELD, 'chamber', 'district', 'party',
                  'transparencydata_id', 'photo_url', 'created_at',
                  'updated_at')
    leg_csv_fname, leg_csv = _make_csv(abbr, 'legislators.csv', leg_fields)

    role_fields = ('leg_id', 'type', 'term', 'district', 'chamber',
                   settings.LEVEL_FIELD, 'party', 'committee_id', 'committee',
                   'subcommittee', 'start_date', 'end_date')
    role_csv_fname, role_csv = _make_csv(abbr, 'legislator_roles.csv',
                                         role_fields)

    com_fields = ('id', settings.LEVEL_FIELD, 'chamber', 'committee',
                  'subcommittee', 'parent_id')
    com_csv_fname, com_csv = _make_csv(abbr, 'committees.csv', com_fields)

    for legislator in db.legislators.find({settings.LEVEL_FIELD: abbr}):
        leg_csv.writerow(extract_fields(legislator, leg_fields))

        # go through roles to create role csv
        all_roles = legislator['roles']
        for roles in legislator.get('old_roles', {}).values():
            all_roles.extend(roles)

        for role in all_roles:
            d = extract_fields(role, role_fields)
            d.update({'leg_id': legislator['leg_id']})
            role_csv.writerow(d)

    for committee in db.committees.find({settings.LEVEL_FIELD: abbr}):
        cdict = extract_fields(committee, com_fields)
        cdict['id'] = committee['_id']
        com_csv.writerow(cdict)

    return leg_csv_fname, role_csv_fname, com_csv_fname


def dump_bill_csvs(abbr):
    bill_fields = (settings.LEVEL_FIELD, 'session', 'chamber',
                   'bill_id', 'title', 'created_at', 'updated_at', 'type',
                   'subjects')
    bill_csv_fname, bill_csv = _make_csv(abbr, 'bills.csv', bill_fields)

    action_fields = (settings.LEVEL_FIELD, 'session', 'chamber',
                     'bill_id', 'date', 'action', 'actor', 'type')
    action_csv_fname, action_csv = _make_csv(abbr, 'bill_actions.csv',
                                             action_fields)

    sponsor_fields = (settings.LEVEL_FIELD, 'session', 'chamber',
                      'bill_id', 'type', 'name', 'leg_id')
    sponsor_csv_fname, sponsor_csv = _make_csv(abbr, 'bill_sponsors.csv',
                                               sponsor_fields)

    vote_fields = (settings.LEVEL_FIELD, 'session', 'chamber',
                   'bill_id', 'vote_id', 'vote_chamber', 'motion', 'date',
                   'type', 'yes_count', 'no_count', 'other_count')
    vote_csv_fname, vote_csv = _make_csv(abbr, 'bill_votes.csv', vote_fields)

    legvote_fields = ('vote_id', 'leg_id', 'name', 'vote')
    legvote_csv_fname, legvote_csv = _make_csv(abbr,
                                               'bill_legislator_votes.csv',
                                               legvote_fields)

    _bill_info = {}
    for bill in db.bills.find({settings.LEVEL_FIELD: abbr}):
        bill_csv.writerow(extract_fields(bill, bill_fields))

        bill_info = extract_fields(
            bill, ('bill_id', settings.LEVEL_FIELD, 'session', 'chamber'))
        _bill_info[bill['_id']] = bill_info

        # basically same behavior for actions, sponsors and votes:
        #    extract fields, update with bill_info, write to csv
        for action in bill['actions']:
            adict = extract_fields(action, action_fields)
            adict.update(bill_info)
            action_csv.writerow(adict)

        for sponsor in bill['sponsors']:
            sdict = extract_fields(sponsor, sponsor_fields)
            sdict.update(bill_info)
            sponsor_csv.writerow(sdict)

    for vote in db.votes.find({settings.LEVEL_FIELD: abbr}):
        vdict = extract_fields(vote, vote_fields)
        # copy chamber from vote into vote_chamber
        vdict['vote_chamber'] = vdict['chamber']
        vdict.update(_bill_info[vote['bill_id']])
        vote_csv.writerow(vdict)

        for vtype in ('yes', 'no', 'other'):
            for leg_vote in vote[vtype + '_votes']:
                legvote_csv.writerow({'vote_id': vote['vote_id'],
                                      'leg_id': leg_vote['leg_id'],
                                      'name': leg_vote['name'].encode('utf8'),
                                      'vote': vtype})

    return (bill_csv_fname, action_csv_fname, sponsor_csv_fname,
            vote_csv_fname, legvote_csv_fname)


class DumpCSV(BaseCommand):
    name = 'dumpcsv'
    help = 'create CSV archive and (optionally) upload it to S3'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='the abbreviation for the data to export')
        self.add_argument('--file', '-f',
                          help='filename to output to (defaults to <abbr>.zip)'
                         )
        self.add_argument('--upload', '-u', action='store_true', default=False,
                          help='upload the created archives to S3')

    def handle(self, args):
        for abbr in args.abbrs:
            if not args.file:
                args.file = abbr + '.zip'
            self.dump(abbr, args.file)
            if args.upload:
                upload(abbr, args.file, 'csv')

    def dump(self, abbr, filename):
        files = []
        files += dump_legislator_csvs(abbr)
        files += dump_bill_csvs(abbr)

        zfile = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
        for fname in files:
            arcname = fname.split('/')[-1]
            zfile.write(fname, arcname=arcname)
            os.remove(fname)


class DumpJSON(BaseCommand):
    name = 'dumpjson'
    help = 'create JSON archive and (optionally) upload it to S3'

    def add_args(self):
        self.add_argument('abbrs', metavar='ABBR', type=str, nargs='+',
                          help='the abbreviation for the data to export')
        self.add_argument('--file', '-f',
                          help='filename to output to (defaults to <abbr>.zip)'
                         )
        self.add_argument('--upload', '-u', action='store_true', default=False,
                          help='upload the created archives to S3')
        self.add_argument('--apikey', dest='API_KEY',
                          help='the API key to use')
        self.add_argument('--schema_dir', default=None,
                          help='directory to use for API schemas (optional)')
        self.add_argument('--novalidate', action='store_true', default=False,
                          help="don't run validation")

    def handle(self, args):
        for abbr in args.abbrs:
            if not args.file:
                args.file = abbr + '.zip'
            self.dump(abbr, args.file, not args.novalidate, args.schema_dir)
            if args.upload:
                upload(abbr, args.file, 'json')

    def dump(self, abbr, filename, validate, schema_dir):
        scraper = scrapelib.Scraper(requests_per_minute=600, retry_attempts=3)

        zip = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)

        if not schema_dir:
            cwd = os.path.split(__file__)[0]
            schema_dir = os.path.join(cwd, "../../schemas/api/")

        with open(os.path.join(schema_dir, "bill.json")) as f:
            bill_schema = json.load(f)

        with open(os.path.join(schema_dir, "legislator.json")) as f:
            legislator_schema = json.load(f)

        with open(os.path.join(schema_dir, "committee.json")) as f:
            committee_schema = json.load(f)

        # write out metadata
        response = scraper.get(api_url('metadata/%s' % abbr)).content
        zip.writestr('metadata.json', response)

        logging.info('exporting %s legislators...' % abbr)
        for legislator in db.legislators.find({settings.LEVEL_FIELD: abbr}):
            path = 'legislators/%s' % legislator['_id']
            url = api_url(path)

            response = scraper.get(url).content
            if validate:
                validictory.validate(json.loads(response), legislator_schema,
                                     validator_cls=APIValidator)

            zip.writestr(path, response)

        logging.info('exporting %s committees...' % abbr)
        for committee in db.committees.find({settings.LEVEL_FIELD: abbr}):
            path = 'committees/%s' % committee['_id']
            url = api_url(path)

            response = scraper.get(url).content
            if validate:
                validictory.validate(json.loads(response), committee_schema,
                                     validator_cls=APIValidator)

            zip.writestr(path, response)

        logging.info('exporting %s bills...' % abbr)
        for bill in db.bills.find({settings.LEVEL_FIELD: abbr}, timeout=False):
            path = "bills/%s/%s/%s/%s" % (abbr, bill['session'],
                                          bill['chamber'], bill['bill_id'])
            url = api_url(path)

            response = scraper.get(url).content
            if validate:
                validictory.validate(json.loads(response), bill_schema,
                                     validator_cls=APIValidator)

            zip.writestr(path, response)

        zip.close()
