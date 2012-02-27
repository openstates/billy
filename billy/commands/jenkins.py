import os
import pdb
import sys
import base64
import logging
import subprocess
import urllib

from StringIO import StringIO
from zipfile import ZipFile, BadZipfile
from os.path import split, join
from urllib2 import urlopen, Request, HTTPError
from optparse import make_option

from billy.conf import settings
from billy.commands import BaseCommand


#-------------------------------------------------------------------------
# The code formerly known as "janky"
states = {
    #'aa': 'Armed Forces Americas',
    #'ae': 'Armed Forces Middle East',
    'ak': 'Alaska',
    'al': 'Alabama',
    #'ap': 'Armed Forces Pacific',
    'ar': 'Arkansas',
    #'as': 'American Samoa',
    'az': 'Arizona',
    'ca': 'California',
    'co': 'Colorado',
    'ct': 'Connecticut',
    'dc': 'District of Columbia',
    'de': 'Delaware',
    'fl': 'Florida',
    #'fm': 'Federated States of Micronesia',
    'ga': 'Georgia',
    #'gu': 'Guam',
    'hi': 'Hawaii',
    'ia': 'Iowa',
    'id': 'Idaho',
    'il': 'Illinois',
    'in': 'Indiana',
    'ks': 'Kansas',
    'ky': 'Kentucky',
    'la': 'Louisiana',
    'ma': 'Massachusetts',
    'md': 'Maryland',
    'me': 'Maine',
    #'mh': 'Marshall Islands',
    'mi': 'Michigan',
    'mn': 'Minnesota',
    'mo': 'Missouri',
    #'mp': 'Northern Mariana Islands',
    'ms': 'Mississippi',
    'mt': 'Montana',
    'nc': 'North Carolina',
    'nd': 'North Dakota',
    'ne': 'Nebraska',
    'nh': 'New Hampshire',
    'nj': 'New Jersey',
    'nm': 'New Mexico',
    'nv': 'Nevada',
    'ny': 'New York',
    'oh': 'Ohio',
    'ok': 'Oklahoma',
    'or': 'Oregon',
    'pa': 'Pennsylvania',
    'pr': 'Puerto Rico',
    #'pw': 'Palau',
    'ri': 'Rhode Island',
    'sc': 'South Carolina',
    'sd': 'South Dakota',
    'tn': 'Tennessee',
    'tx': 'Texas',
    'ut': 'Utah',
    'va': 'Virginia',
    'vi': 'Virgin Islands',
    'vt': 'Vermont',
    'wa': 'Washington',
    'wi': 'Wisconsin',
    'wv': 'West Virginia',
    'wy': 'Wyoming'}

urls = {'data': ('http://staging.openstates.org/jenkins/job/'
                 '{state}/ws/data/{abbr}/*zip*/{abbr}.zip'),
        'cache': ('http://staging.openstates.org/jenkins/job/'
                  '{state}/ws/cache/*zip*/cache.zip')}


# Logging config
logger = logging.getLogger('janky-import')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def _import(abbr, folder):
    path = split(settings.SCRAPER_PATHS[0])[0]

    # Get credentials.
    username = getattr(settings, 'JENKINS_USER', None)
    password = getattr(settings, 'JENKINS_PASSWORD', None)
    if username is None:
        username = raw_input('jenkins username: ')
    if password is None:
        password = getpass.getpass('jenkins password: ')

    auth_header = '%s:%s' % (username, password)
    auth_header = 'Basic ' + base64.encodestring(auth_header)[:-1]

    # Get the data.
    abbr = abbr.lower()
    state = urllib.pathname2url(states.get(abbr))
    zip_url = urls[folder].format(**locals())

    logger.info('requesting {folder} folder for {state}...'.format(**locals()))
    req = Request(zip_url, headers={'Authorization': auth_header})

    try:
        resp = urlopen(req).read()
        # resp = open('foo', 'w')
        # resp.write(urlopen(req))
    except HTTPError:
        logger.warn('Could\'t fetch from url: %s' % zip_url)
        return

    size = len(resp)
    logger.info('response ok [%d bytes]. Unzipping files...' % size)

    # Unzip.
    try:
        os.makedirs(path)
    except OSError:
        pass

    try:
        zipfile = ZipFile(StringIO(resp))
    except BadZipfile:
        logger.warn('%s response wasn\'t a zip file. Skipping.' % state)
        return

    file_count = len(zipfile.namelist())
    zipfile.extractall(path)
    logger.info('Extracted %d files to %s.' % (file_count, path))


def import_data(abbr, path):
    path = join(path, 'data')
    _import(abbr, 'data', path)


def import_cache(abbr):
    _import(abbr, 'cache')


funcs = {'data': import_data,
         'cache': import_cache}


#------------------------------------------------------------------------------
# Setup the management command.
class Jenkins(BaseCommand):

    name = 'jenkins'
    args = '<state1>[, <state2>[..., <stateN>]]'
    help = 'import build artifacts from jenkins'


    def add_args(self):
        self.add_argument('states', nargs="+", help='which states to download data for.')
        self.add_argument('--data', dest='data', default=True,
                          help='whether to download data.')
        self.add_argument('--imp', dest='imp', default=True,
                          help='whether to import downloaded data.')
        self.add_argument('--cache', dest='cache', default=False,
                          help='whether to download cache files')


    def handle(self, args):

        _states = args.states

        if 'all' in args.states:
            _states = states

        for state in _states:

            if args.data:
                import_data(state)

            if args.cache:
                import_cache(state)

            if args.imp:
                c = 'billy-update %s --import --report --alldata -vvv' % state
                subprocess.call(c, shell=True)

