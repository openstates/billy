'''
Pushes stored user favorites to Scout for alert tracking.
'''
import json
import logging
import urlparse
import datetime
from optparse import make_option

from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand

from billy.core import settings, user_db
from billy.utils import JSONEncoderPlus

import requests

_log = logging.getLogger('billy.web.public.management.commands.scout_push')


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--dry-run', action='store_true', dest='dry_run',
                    default=False, help='dry run'),
    )

    def handle_noargs(self, **options):
        usernames = user_db.favorites.distinct('username')

        for username in usernames:
            self.push_user(username, options['dry_run'])

    def push_user(self, username, dry_run):
        user = User.objects.get(username=username)
        payload = {'email': user.email,
                   'secret_key': settings.SCOUT_SECRET_KEY,
                   'service': settings.SCOUT_SERVICE,
                   'notifications': 'email_daily'}

        # Only send alerts if the user has turned alerts on for that
        # object type.
        profile_spec = dict(_id=username)
        profile = user_db.profiles.find_one(profile_spec)
        profile = profile or profile_spec
        notifications = profile.get('notifications', {})

        interests = []
        for favorite in user_db.favorites.find({'username': username}):

            if favorite['obj_type'] in ('legislator', 'bill'):
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

            elif favorite['obj_type'] == 'committee':
                continue        # no tracking for now
            else:
                _log.warning('Unknown favorite type: %s', favorite['obj_type'])
                continue

            send_alerts = notifications.get(favorite['obj_type'], True)
            if favorite['is_favorite'] and send_alerts:
                interest['active'] = True
            else:
                interest['active'] = False

            interest['changed_at'] = favorite['timestamp']
            interests.append(interest)

        payload['interests'] = interests
        _log.info('pushing %s interests for %s', len(interests),
                  payload['email'])

        # Add the last scout sync date to the user's profile.
        profile['last_scout_sync'] = datetime.datetime.utcnow()
        user_db.profiles.save(profile)

        if not dry_run:
            url = 'https://scout.sunlightfoundation.com/remote/service/sync'
            payload = json.dumps(payload, cls=JSONEncoderPlus)
            _log.info(payload)
            resp = requests.post(url, data=payload)
            _log.info('[%s] %s', resp.status_code, resp.content)

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
