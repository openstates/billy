import os
import json
import random
import subprocess

from billy import db
from billy.commands import BaseCommand
from billy.utils import metadata

from billy.conf import settings, base_arg_parser
from billy.commands.dump import APIValidator, api_url

import scrapelib
import validictory

class ValidateApi(BaseCommand):
    name = 'validateapi'
    help = 'validate data from the API'

    def add_args(self):
        self.add_argument('--sunlight_key', dest='SUNLIGHT_SERVICES_KEY',
                  help='the Sunlight API key to use')
        self.add_argument('--schema_dir', default=None,
                  help='directory to use for API schemas (optional)')

    def handle(self, args):
        for metadata in db.metadata.find():
            validate_api(metadata['abbreviation'], args.schema_dir)


def get_json_schema(name, schema_dir):
    if schema_dir:
        try:
            schema_dir = os.path.abspath(schema_dir)
            with open(os.path.join(schema_dir, name + ".json")) as f:
                return json.load(f)
        except IOError as ex:
            if ex.errno != 2:
                raise

    # Fallback to default schema dir
    cwd = os.path.split(__file__)[0]
    default_schema_dir = os.path.join(cwd, "../schemas/api/")

    with open(os.path.join(default_schema_dir, name + ".json")) as f:
        return json.load(f)


def validate_api(abbr, schema_dir=None):
    metadata_schema = get_json_schema("metadata", schema_dir)
    path = "metadata/%s" % abbr
    url = api_url(path)
    json_response = scrapelib.urlopen(url)
    validictory.validate(json.loads(json_response), metadata_schema,
                         validator_cls=APIValidator)

    bill_schema = get_json_schema("bill", schema_dir)

    level = metadata(abbr)['level']
    spec = {'level': level, level: abbr}
    total_bills = db.bills.find(spec).count()

    for i in xrange(0, 100):
        bill = db.bills.find(spec)[random.randint(0, total_bills - 1)]
        path = "bills/%s/%s/%s/%s" % (abbr, bill['session'],
                                      bill['chamber'], bill['bill_id'])
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), bill_schema,
                                 validator_cls=APIValidator)

    legislator_schema = get_json_schema("legislator", schema_dir)
    for legislator in db.legislators.find(spec):
        path = 'legislators/%s' % legislator['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), legislator_schema,
                             validator_cls=APIValidator)

    committee_schema = get_json_schema("committee", schema_dir)
    for committee in db.committees.find(spec):
        path = "committees/%s" % committee['_id']
        url = api_url(path)

        json_response = scrapelib.urlopen(url)
        validictory.validate(json.loads(json_response), committee_schema,
                             validator_cls=APIValidator)

    event_schema = get_json_schema("event", schema_dir)
    total_events = db.events.find(spec).count()

    if total_events:
        for i in xrange(0, 10):
            event = db.events.find(spec)[random.randint(0, total_events - 1)]
            path = "events/%s" % event['_id']
            url = api_url(path)

            json_response = scrapelib.urlopen(url)
            validictory.validate(json.loads(json_response), event_schema,
                                 validator_cls=APIValidator)
