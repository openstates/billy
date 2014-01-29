import os
import re
import string
import logging
import tempfile
import importlib
import subprocess

import requests
import boto.s3.key

from billy.scrape.utils import convert_pdf
from billy.core import settings, s3bucket


_log = logging.getLogger('billy.utils.fulltext')


def pdfdata_to_text(data):
    with tempfile.NamedTemporaryFile(delete=True) as tmpf:
        tmpf.write(data)
        tmpf.flush()
        return convert_pdf(tmpf.name, 'text')


def worddata_to_text(data):
    desc, txtfile = tempfile.mkstemp(prefix='tmp-worddata-', suffix='.txt')
    try:
        with tempfile.NamedTemporaryFile(delete=True) as tmpf:
            tmpf.write(data)
            tmpf.flush()
            subprocess.check_call(['timeout', '10', 'abiword',
                                   '--to=%s' % txtfile, tmpf.name])
            f = open(txtfile)
            text = f.read()
            tmpf.close()
            f.close()
    finally:
        os.remove(txtfile)
        os.close(desc)
    return text.decode('utf8')


def text_after_line_numbers(lines):
    text = []
    for line in lines.splitlines():
        # real bill text starts with an optional space, line number
        # more spaces, then real text
        match = re.match('\s*\d+\s+(.*)', line)
        if match:
            text.append(match.group(1))

    # return all real bill text joined w/ newlines
    return '\n'.join(text).decode('utf-8', 'ignore')


def id_to_url(id):
    abbr = id[0:2].lower()
    return 'http://{0}/{1}/{2}'.format(settings.AWS_BUCKET, abbr, id)


def s3_get(abbr, doc):
    if settings.AWS_BUCKET:
        k = boto.s3.key.Key(s3bucket)
        k.key = 'documents/{0}/{1}'.format(abbr, doc['doc_id'])

        # try and get the object, if it doesn't exist- pull it down
        try:
            return k.get_contents_as_string()
        except:
            response = requests.get(doc['url'].replace(' ', '%20'))
            content_type = response.headers.get('content-type')
            if not content_type:
                url = doc['url'].lower()
                if url.endswith('htm') or doc['url'].endswith('html'):
                    content_type = 'text/html'
                elif url.endswith('pdf'):
                    content_type = 'application/pdf'
            headers = {'x-amz-acl': 'public-read', 'Content-Type': content_type}
            k.set_contents_from_string(response.content, headers=headers)
            _log.debug('pushed %s to s3 as %s', doc['url'], doc['doc_id'])
            return response.content
    else:
        return requests.get(doc['url'].replace(' ', '%20')).content


PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))


def plaintext(abbr, doc, doc_bytes):
    # use module to pull text out of the bytes
    module = importlib.import_module(abbr)
    text = module.extract_text(doc, doc_bytes)

    if not text:
        return

    if isinstance(text, unicode):
        text = text.encode('ascii', 'ignore')
    else:
        text = text.decode('utf8', 'ignore').encode('ascii', 'ignore')
    text = text.replace(u'\xa0', u' ')  # nbsp -> sp
    text = PUNCTUATION.sub(' ', text)   # strip punctuation
    text = re.sub('\s+', ' ', text)     # collapse spaces
    return text


def bill_to_elasticsearch(bill):
    esbill = {}
    copy_fields = ('chamber', 'bill_id', 'session', '_term', 'type',
                   'subjects', '_current_session', '_current_term')
    time_format = '%Y-%m-%dT%H:%M:%S'
    for field in copy_fields:
        esbill[field] = bill.get(field)
    esbill['title'] = [bill['title']] + bill['alternate_titles']
    abbr = esbill['jurisdiction'] = bill[settings.LEVEL_FIELD]
    esbill['sponsor_ids'] = [s['leg_id'] for s in bill['sponsors']]
    esbill['updated_at'] = bill['updated_at'].strftime(time_format)
    esbill['created_at'] = bill['created_at'].strftime(time_format)
    esbill['action_dates'] = {k: v.strftime(time_format)
                              for k, v in bill['action_dates'].iteritems()
                              if v}
    esbill['text'] = []
    for doc in bill['versions']:
        try:
            esbill['text'].append(plaintext(abbr, doc, s3_get(abbr, doc)))
        except Exception as e:
            _log.debug('exception %s while processing %s', e, doc['url'])

    return esbill
