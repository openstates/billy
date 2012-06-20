import os
import re
import string
import tempfile
import subprocess
from functools import wraps
from billy.scrape.utils import convert_pdf


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
            subprocess.check_call(['abiword', '--to=%s' %txtfile, tmpf.name])
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


PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))


def _clean_text(text):
    if isinstance(text, unicode):
        text = text.encode('ascii', 'ignore')
    else:
        text = text.decode('utf8', 'ignore').encode('ascii', 'ignore')
    text = text.replace(u'\xa0', u' ') # nbsp -> sp
    text = PUNCTUATION.sub(' ', text)  # strip punctuation
    text = re.sub('\s+', ' ', text)    # collapse spaces
    return text


def oyster_text(function):
    @wraps(function)
    def wrapper(oyster_doc, data):
        data = function(oyster_doc, data)
        if data:
            return _clean_text(data)
    return wrapper
