import logging
from celery.task.base import Task
import boto.s3
import scrapelib
from billy.core import db, elasticsearch, settings, s3bucket
from billy.utils.fulltext import plaintext

_log = logging.getLogger('billy.tasks.fulltext')


def s3_get(doc):
    k = boto.s3.key.Key(s3bucket)
    k.key = 'documents/{0}/{1}'.format(doc[settings.LEVEL_FIELD], doc['_id'])

    # try and get the object, if it doesn't exist- pull it down
    try:
        return k.get_contents_as_string()
    except:
        doc = db.tracked_versions.find_one(id)
        if not doc:
            return None
        data = scrapelib.urlopen(doc['url'].replace(' ', '%20'))
        content_type = data.response.headers['content-type']
        headers = {'x-amz-acl': 'public-read', 'Content-Type': content_type}
        k.set_contents_from_string(data.bytes, headers=headers)
        _log.debug('pushed %s to s3 as %s', doc['url'], id)
        return data.bytes


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
            self._log.warning('error pushing %s to ElasticSearch', doc_id,
                              exc_info=True)
            raise
