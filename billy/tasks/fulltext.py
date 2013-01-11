import logging
from celery.task.base import Task
from billy.core import db, elasticsearch
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
