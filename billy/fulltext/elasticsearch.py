import logging
from celery.task.base import Task

from billy.core import db, elasticsearch
from . import plaintext

log = logging.getLogger('billy.fulltext.elasticsearch')


class ElasticSearchPush(Task):
    # results go into ES
    ignore_result = True

    def run(self, doc_id):
        doc = db.tracked_versions.find_one(doc_id)

        try:
            text = plaintext(doc_id)

            elasticsearch.index(dict(doc, text=text), 'bills', 'version',
                                id=doc_id)
            db.tracked_versions.update({'_id': doc_id},
                                       {'$set': {'_elasticsearch': True}},
                                       safe=True)
            log.info('pushed %s to ElasticSearch', doc_id)

        except Exception:
            log.warning('error pushing %s to ElasticSearch', doc_id, exc_info=True)
            raise
