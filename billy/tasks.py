'''
A few notes from our initial tests of this (Thom 12/20/2012)
- the user search page allows chamber to be a checkbox with multiple values
  but the api requires a string (upper or lower)
- Some keys don't appear to be supported in the api:
  - type
  - status (checkbox/list)
  So we lose them in the post to Scout unless we add them to the api. this
  just means people will think they're getting alerts for a narrower
  set of contstraints, but will get (ie.,

'''
# import sys, os
# sys.path.append('/home/thom/sunlight/openstates/site')
# os.environ['DJANGO_SETTINGS_MODULE'] = 'openstates_site.settings'

import json
import logging
import urlparse
#from celery.task.base import Task
from django.contrib.auth.models import User
from billy.core import db, elasticsearch, settings, user_db
from billy.utils import JSONEncoderPlus
from billy.utils.fulltext import plaintext

import requests


class Task(object):
    '''A dummy task to temporarily remove celery from the equation.
    '''


class ElasticSearchPush(Task):
    # results go into ES
    ignore_result = True
    _log = logging.getLogger('billy.tasks.ElasticSearchPush')

    def run(self, doc_id):
        doc = db.tracked_versions.find_one(doc_id)

        try:
            text = plaintext(doc_id)

            elasticsearch.index(dict(doc, text=text), 'bills', 'version',
                                id=doc_id)
            db.tracked_versions.update({'_id': doc_id},
                                       {'$set': {'_elasticsearch': True}},
                                       safe=True)
            self._log.info('pushed %s to ElasticSearch', doc_id)

        except Exception:
            self._log.warning('error pushing %s to ElasticSearch', doc_id,
                              exc_info=True)
            raise


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
                search_text = params.pop('search_text').pop()
                interest = {
                    'interest_type': 'search',
                    'search_type': 'state_bills',
                    'query_type': 'advanced',
                    'in': search_text,
                    'filters': self._translate_filter_data(params)
                }

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
        resp = requests.post(url, data=payload)


    def _translate_filter_data(self, params):
        '''Edit the favorite['search_params'] object and make them
        match the param names used in an api request.
        '''
        # Two api params have no analog in the front-end search: bill_id__in
        # and updated_since
        api_param_names = 'q state search_window chamber subjects sponsor_id'
        api_param_name_set = set(api_param_names.split())

        result = {}

        api_param_names = {
            'search_text': 'q',
            'search_state': 'state',
            'session': 'search_window',
            'sponsor__leg_id': 'spnosor_id'
            }

        for k, v in params.items():
            print k, v
            if k == 'session':
                v = 'session:' + v.pop()

            elif k == 'search_state':
                # Scout expects uppercase.
                v = v.upper()

            elif k == 'chamber':
                # XXX Hack: the front-end search allows users to select
                # multiple chambers, but the api method only accepts one.
                v = v.pop()

            api_param_name = api_param_names.get(k)
            if api_param_name is None:
                api_param_name = k

            if api_param_name in api_param_name_set:
                result[api_param_name] = v

        return result



def main():
    for user in user_db.profiles.find():
        ScoutPush().run(user['_id'])


if __name__ == '__main__':
    main()