import logging
import urlparse
from celery.task.base import Task
from django.contrib.auth.models import User
from billy.core import db, elasticsearch, settings, user_db
from billy.utils.fulltext import plaintext


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
                   'source': settings.SCOUT_SOURCE,
                   'notifications': 'email_daily'}
        interests = []
        for favorite in user_db.favorites.find({'user_id': user_id}):
            if favorite['obj_type'] in ('legislator', 'bill'):
                interest = {'interest_type': 'item',
                            'item_type': 'state_' + favorite['obj_type'],
                            'item_id': favorite['obj_type'],
                           }
            elif favorite['obj_type'] == 'search':
                params = urlparse.parse_qs(favorite['search_params'])
                search_text = params.pop('search_text')
                # TODO: handle session, status, type, sponsor__leg_id
                interest = {
                    'interest_type': 'search',
                    'search_type': 'state_bills',
                    'query_type': 'advanced',
                    'in': search_text,
                    'filters': {'state': favorite['search_abbr'].upper()}
                }
            else:
                self._log.warning('Unknown favorite type: %s',
                                  favorite['obj_type'])
                continue

            interest['active'] = favorite['is_favorite']
            interest['timestamp'] = favorite['timestamp']
            interests.append(interest)

        self._log.info('pushing %s interests for %s', len(interests),
                       payload['email'])

        # TODO: push to scout & handle response
