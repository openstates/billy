import re
import string
from functools import wraps

PUNCTUATION = re.compile('[%s]' % re.escape(string.punctuation))

def clean_text(text):
    text = re.sub('\s+', ' ', text)
    text = PUNCTUATION.sub('', text)
    return text


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
