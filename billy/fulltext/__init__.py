import re
import string
import logging
import importlib
from billy.core import settings, db, s3bucket
import boto.s3
import scrapelib

log = logging.getLogger('billy.fulltext.elasticsearch')

def id_to_url(id):
    abbr = id[0:2].lower()
    return 'http://{0}/{1}/{2}'.format(settings.AWS_BUCKET, abbr, id)


def s3_get(id):
    k = boto.s3.key.Key(s3bucket)
    k.key = 'documents/{0}/{1}'.format(id[0:2].lower(), id)

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
        log.debug('pushed %s to s3 as %s', doc['url'], id)
        return data.bytes


PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))


def _clean_text(text):
    if isinstance(text, unicode):
        text = text.encode('ascii', 'ignore')
    else:
        text = text.decode('utf8', 'ignore').encode('ascii', 'ignore')
    text = text.replace(u'\xa0', u' ')  # nbsp -> sp
    text = PUNCTUATION.sub(' ', text)   # strip punctuation
    text = re.sub('\s+', ' ', text)     # collapse spaces
    return text


def plaintext(id):
    abbr = id[0:2].lower()
    doc = db.tracked_versions.find_one(id)
    module = importlib.import_module(abbr)
    text = module.extract_text(doc, s3_get(id))
    return _clean_text(text)
