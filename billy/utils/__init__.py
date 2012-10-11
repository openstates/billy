import datetime
import json
import re
import time
import urllib
import urlparse

from bson import ObjectId

from billy.core import db
import difflib


# metadata cache
__metadata = {}


def metadata(abbr, __metadata=__metadata):
    """
    Grab the metadata for the given two-letter abbreviation.
    """
    # This data should change very rarely and is queried very often so
    # cache it here
    abbr = abbr.lower()
    if abbr in __metadata:
        return __metadata[abbr]
    rv = db.metadata.find_one({'_id': abbr})
    __metadata[abbr] = rv
    return rv


def chamber_name(abbr, chamber):
    if chamber in ('joint', 'other'):
        return 'Joint'

    return metadata(abbr)['%s_chamber_name' % chamber].split()[0]


def parse_param_dt(dt):
    formats = ['%Y-%m-%d %H:%M',    # here for legacy reasons
               '%Y-%m-%dT%H:%M:%S',
               '%Y-%m-%d']
    for format in formats:
        try:
            return datetime.datetime.strptime(dt, format)
        except ValueError:
            pass
    raise ValueError('unable to parse %s' % dt)


class JSONEncoderPlus(json.JSONEncoder):
    """
    JSONEncoder that encodes datetime objects as Unix timestamps and mongo
    ObjectIds as strings.
    """
    def default(self, obj, **kwargs):
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.utctimetuple())
        elif isinstance(obj, datetime.date):
            return time.mktime(obj.timetuple())
        elif isinstance(obj, ObjectId):
            return str(obj)

        return super(JSONEncoderPlus, self).default(obj, **kwargs)


def term_for_session(abbr, session, meta=None):
    if not meta:
        meta = metadata(abbr)

    for term in meta['terms']:
        if session in term['sessions']:
            return term['name']

    raise ValueError("no such session '%s'" % session)


def urlescape(url):
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(url)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def textual_diff(l1, l2):
    lines = {}
    types = {
        "?": "info",
        "-": "sub",
        "+": "add",
        "": "noop"
    }
    lineno = 0

    for line in '\n'.join(difflib.ndiff(l1, l2)).split("\n"):
        prefix = line[:1].strip()
        lastfix = line[2:].rstrip()

        if lastfix == "":
            continue

        lineno += 1
        lines[lineno] = {
            "type": types[prefix],
            "line": lastfix
        }
    return lines


# fixing bill ids
_bill_id_re = re.compile(r'([A-Z]*)\s*0*([-\d]+)')


def fix_bill_id(bill_id):
    bill_id = bill_id.replace('.', '')
    return _bill_id_re.sub(r'\1 \2', bill_id, 1).strip()


def find_bill(query, fields=None):
    bill = db.bills.find_one(query, fields=fields)
    if not bill and 'bill_id' in query:
        bill_id = query.pop('bill_id')
        query['alternate_bill_ids'] = bill_id
        bill = db.bills.find_one(query, fields=fields)
    return bill
