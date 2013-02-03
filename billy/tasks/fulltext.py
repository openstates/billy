import logging
from celery.task.base import Task
import boto.s3
import scrapelib
from billy.core import db, elasticsearch, settings, s3bucket
from billy.utils.fulltext import plaintext

_log = logging.getLogger('billy.tasks.fulltext')




class ElasticSearchPush(Task):
    # results go into ES
    ignore_result = True

    def run(self, doc_id):
        doc = db.tracked_versions.find_one(doc_id)

        try:
            # get bytes, using s3 as a cache
            doc_bytes = s3_get(doc)

            # extract cleaned text from bytes
            text = plaintext(doc, doc_bytes)

            # push to elasticsearch
            elasticsearch.index(dict(doc, text=text), 'bills', 'version',
                                id=doc_id)

            doc['_elasticsearch'] = True
            db.tracked_versions.save(doc, safe=True)
            _log.info('pushed %s to ElasticSearch', doc_id)

        except Exception:
            _log.warning('error pushing %s to ElasticSearch', doc_id,
                         exc_info=True)
            raise
