import re
import string
import tempfile
from functools import wraps
from billy.scrape.utils import convert_pdf

PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))

def clean_text(text):
    text = text.replace(u'\xa0', ' ')  # nbsp -> sp
    text = re.sub('\s+', ' ', text)    # collapse spaces
    text = PUNCTUATION.sub('', text)   # strip punctuation
    return text


def pdfdata_to_text(data):
    with tempfile.NamedTemporaryFile(delete=False) as tmpf:
        tmpf.write(data)
        tmpf.close()
        return convert_pdf(tmpf.name, 'text')


def extracts_text(function):
    @wraps(function)
    def wrapper(oyster_doc, data):
        oyster_doc['text_content'] = _clean_text(function(oyster_doc, data))
    return wrapper


def text_after_line_numbers(lines):
    text = []
    for line in lines.splitlines():
        # real bill text starts with an optional space, line number
        # more spaces, then real text
        match = re.match('\s*\d+\s+(.*)', line)
        if match:
            text.append(match.group(1))

    # return all real bill text joined w/ spaces
    return ' '.join(text).decode('utf-8', 'ignore')
