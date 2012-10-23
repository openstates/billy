import importlib
from billy.core import settings, db, s3bucket
import boto.s3

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
        doc = db.tracked_documents.find_one(id)
        if not doc:
            return None
        data = scrapelib.urlopen(doc['url'].replace(' ', '%20'))
        content_type = data.response.headers['content-type']
        headers = {'x-amz-acl': 'public-read', 'Content-Type': content_type}
        k.set_contents_from_string(data, headers=headers)
        return data


def plaintext(id):
    abbr = id[0:2].lower()
    doc = db.tracked_documents.find_one(id)
    return importlib.import_module(abbr).extract_text(doc, s3_get(id))
