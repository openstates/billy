'''
Pushes stored user favorites to Scout for alert tracking.

To run stand-alone for debugging, openstates_site has to be on sys.path and
DJANGO_SETTINGS_MODULE has to be set to openstates_site/localsettings.py.
See commented-out lines below for example.
'''
# import sys
# sys.path.insert(0, '/home/thom/sunlight/openstates/site/openstates_site')
# import os
# os.environ['DJANGO_SETTINGS_MODULE'] = 'local_settings'

import json
import logging
import urlparse

from celery.task.base import Task
from django.contrib.auth.models import User
from billy.core import settings, user_db
from billy.utils import JSONEncoderPlus

import requests


class ScoutPush(Task):
    # no results needed
    ignore_result = True
    _log = logging.getLogger('billy.tasks.ScoutPush')

    def run(self, user_id):
        user = User.objects.get(pk=user_id)
        payload = {'email': user.email,
                   'secret_key': settings.SCOUT_SECRET_KEY,
                   'service': settings.SCOUT_SERVICE,
                   'notifications': 'email_daily'}
        interests = []
        for favorite in user_db.favorites.find({'user_id': user_id}):
            if favorite['obj_type'] in ('legislator', 'bill', 'committee'):
                interest = {'interest_type': 'item',
                            'item_type': 'state_' + favorite['obj_type'],
                            'item_id': favorite['obj_id'],
                           }
            elif favorite['obj_type'] == 'search':
                params = urlparse.parse_qs(favorite['search_params'])
                interest = {
                    'interest_type': 'search',
                    'search_type': 'state_bills',
                    'query_type': 'advanced',
                    'filters': self._translate_filter_data(favorite, params)
                }
                if 'search_text' in params:
                    interest['in'] = params.get('search_text').pop()
                else:
                    interest['in'] = ''

            else:
                self._log.warning('Unknown favorite type: %s',
                                  favorite['obj_type'])
                continue

            interest['active'] = favorite['is_favorite']
            interest['changed_at'] = favorite['timestamp']
            interests.append(interest)

        payload['interests'] = interests
        self._log.info('pushing %s interests for %s', len(interests),
                       payload['email'])

        url = 'http://scout.sunlightfoundation.com/remote/service/sync'
        payload = json.dumps(payload, cls=JSONEncoderPlus)
        requests.post(url, data=payload)

    def _translate_filter_data(self, favorite, params):
        '''Edit the favorite['search_params'] object and make them
        match the param names used in an api request.
        '''
        # some api params have no analog in the front-end search: updated_since
        api_param_name_set = set([
            'state',
            'search_window',
            'chamber',
            'subjects',
            'sponsor_id',
            'session',
            'type',
            'status'])

        result = {}

        # Rename certain front-end parameters to their api equivalents.
        api_param_names = {
            'session': 'search_window',
            'sponsor__leg_id': 'sponsor_id'
        }

        for k, v in params.items():

            if k == 'session':
                v = 'session:' + v.pop()

            api_param_name = api_param_names.get(k, k)

            if api_param_name in api_param_name_set:

                # Flatten any single-item param arrays into strings.
                if isinstance(v, list) and k not in ['status', 'subjects']:
                    if len(v) == 1:
                        v = v.pop()

                result[api_param_name] = v

        # Add the state abbreviation.
        if 'search_abbr' in favorite:
            result['state'] = favorite['search_abbr'].upper()

        return result

