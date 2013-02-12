'''
A few notes from our initial tests of this (Thom 12/20/2012)
- Some keys don't appear to be supported in the api:
  - type
  - status (checkbox/list)
  So we lose them in the post to Scout unless we add them to the api.
'''
import sys
sys.path.insert(0, '/home/thom/sunlight/openstates/site/openstates_site')
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'local_settings'

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
                    'filters': self._translate_filter_data(params)
                }
                if 'search_text' in params:
                    interest['in'] = params.get('search_text').pop()

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

        url = 'http://scout.sunlightlabs.com/remote/service/sync'
        payload = json.dumps(payload, cls=JSONEncoderPlus)
        # resp = requests.post(url, data=payload)

    def _translate_filter_data(self, params):
        '''Edit the favorite['search_params'] object and make them
        match the param names used in an api request.
        '''
        # some api params have no analog in the front-end search: updated_since
        api_param_name_set = set([
            'q',
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
            'search_text': 'q',
            'search_state': 'state',
            'session': 'search_window',
            'sponsor__leg_id': 'sponsor_id'
        }

        for k, v in params.items():

            if k == 'session':
                v = 'session:' + v.pop()
            elif k == 'search_state':
                # Scout expects uppercase.
                v = v.upper()

            api_param_name = api_param_names.get(k, k)

            if api_param_name in api_param_name_set:
                result[api_param_name] = v

        import urllib
        import pprint
        pprint.pprint(result)
        result['apikey'] = 'testkey12'
        print urllib.urlencode(result, doseq=True)
        import pdb; pdb.set_trace()
        return result


if __name__ == '__main__':
    from billy.core import user_db
    for profile in user_db.profiles.find():
        ScoutPush().run(profile['_id'])
