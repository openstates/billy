import os
import json
import re
import time
import urllib
import datetime
import urlparse
import contextlib

from bson import ObjectId
from django.core.exceptions import ImproperlyConfigured

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

    return metadata(abbr)['chambers'][chamber]['name'].split()[0]


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
_mi_bill_id_re = re.compile(r'(SJR|HJR)\s*([A-Z]+)')


def fix_bill_id(bill_id):
    bill_id = bill_id.replace('.', '')
    # special case for MI Joint Resolutions
    if _mi_bill_id_re.match(bill_id):
        return _mi_bill_id_re.sub(r'\1 \2', bill_id, 1).strip()
    return _bill_id_re.sub(r'\1 \2', bill_id, 1).strip()


def find_bill(query, fields=None):
    bill = db.bills.find_one(query, fields=fields)
    if not bill and 'bill_id' in query:
        bill_id = query.pop('bill_id')
        query['alternate_bill_ids'] = bill_id
        bill = db.bills.find_one(query, fields=fields)
    return bill

try:
    from django.contrib.sites.models import Site

    def get_domain():
        return Site.objects.get_current().domain
except (ImportError, ImproperlyConfigured):
    def get_domain():           # noqa
        return 'example.com'


@contextlib.contextmanager
def cd(path):
    '''Creates the path if it doesn't exist'''
    old_dir = os.getcwd()
    try:
        os.makedirs(path)
    except OSError:
        pass
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)


class CachedAttr(object):
    '''Computes attribute value and caches it in instance.

    Example:
        class MyClass(object):
            def myMethod(self):
                # ...
            myMethod = CachedAttribute(myMethod)
    Use "del inst.myMethod" to clear cache.

    Source: http://code.activestate.com/recipes/276643-caching-and-aliasing-with-descriptors/'''

    def __init__(self, method, name=None):
        self.method = method
        self.name = name or method.__name__

    def __get__(self, inst, cls):
        if inst is None:
            return self
        result = self.method(inst)
        setattr(inst, self.name, result)
        return result
