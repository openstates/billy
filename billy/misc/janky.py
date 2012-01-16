import os
import sys
import base64
import logging

from StringIO import StringIO
from zipfile import ZipFile, BadZipfile
from os.path import split, join
from urllib2 import urlopen, Request, HTTPError

import billy_settings


states = {
    'aa': 'Armed Forces Americas',
    'ae': 'Armed Forces Middle East',
    'ak': 'Alaska',
    'al': 'Alabama',
    'ap': 'Armed Forces Pacific',
    'ar': 'Arkansas',
    'as': 'American Samoa',
    'az': 'Arizona',
    'ca': 'California',
    'co': 'Colorado',
    'ct': 'Connecticut',
    'dc': 'District of Columbia',
    'de': 'Delaware',
    'fl': 'Florida',
    'fm': 'Federated States of Micronesia',
    'ga': 'Georgia',
    'gu': 'Guam',
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
    'mh': 'Marshall Islands',
    'mi': 'Michigan',
    'mn': 'Minnesota',
    'mo': 'Missouri',
    'mp': 'Northern Mariana Islands',
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
    'pw': 'Palau',
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

path = split(billy_settings.SCRAPER_PATHS[0])[0]

# Logging config
logger = logging.getLogger('janky-import')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
formatter = logging.Formatter('%(name)s %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def _import(abbr, folder, path=path):

    # Get the data.
    abbr = abbr.lower()
    state = states.get(abbr)
    zip_url = urls[folder].format(**locals())

    logger.info('requesting {folder} folder for {state}...'.format(**locals()))
    req = Request(zip_url, headers={'Authorization': auth_header})

    try:
        resp = urlopen(req).read()
    except HTTPError:
        logger.warn('CRAP: %s' % zip_url)
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

    
def import_data(abbr, path=path):
    path = join(path, 'data')
    _import(abbr, 'data', path)


def import_cache(abbr):
    _import(abbr, 'cache')


funcs = {'data': import_data,
         'cache': import_cache}
    

if __name__ == "__main__":
    import pdb
    import getpass
    import argparse

    parser = argparse.ArgumentParser(description='Download data and cache files from Jenkins.')

    # Options.
    parser.add_argument('abbr', help='state to download data for')

    parser.add_argument('--cache', dest='cache', action='store_const',
                       default=False, const='cache',
                       help='Download the latest cache build for a state.')
    parser.add_argument('--data', dest='data', action='store_const',
                        default=False, const='data',
                        help='Download the latest data build for a state.')
    parser.add_argument('--both', dest='both', action='store_true',
                        default=False,
                        help='Download the latest cache and data build for a state.')
    parser.add_argument('--alldata', dest='alldata', action='store_true',
                        default=False,
                        help='Download data/cache/both for all states.')

    args = parser.parse_args()

    username = raw_input('jenkins username: ')
    password = getpass.getpass('jenkins password: ')

    auth_header = '%s:%s' % (username, password)
    auth_header = 'Basic ' + base64.encodestring(auth_header)[:-1]


    # Program.
    folders = filter(None, [args.data, args.cache])
    if args.both:
        folders = ['data', 'cache']

    if args.abbr == 'all':
        _states = states
        
    else:
        _states = [args.abbr]

    for state in _states:
        for f in folders:
            funcs[f](state)
            
        
    
