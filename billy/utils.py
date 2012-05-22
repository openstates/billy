import re
import urllib
import urlparse
import logging

from billy import db
import difflib


# metadata cache
__metadata = {}


def metadata(abbr):
    """
    Grab the metadata for the given two-letter abbreviation.
    """
    # This data should change very rarely and is queried very often so
    # cache it here
    abbr = abbr.lower()
    if abbr in __metadata:
        return __metadata[abbr]
    return db.metadata.find_one({'_id': abbr})


def chamber_name(abbr, chamber):
    if chamber in ('joint', 'other'):
        return 'Joint'

    return metadata(abbr)['%s_chamber_name' % chamber].split()[0]


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


def extract_fields(d, fields, delimiter='|'):
    """ get values out of an object ``d`` for saving to a csv """
    rd = {}
    for f in fields:
        v = d.get(f, None)
        if isinstance(v, (str, unicode)):
            v = v.encode('utf8')
        elif isinstance(v, list):
            v = delimiter.join(v)
        rd[f] = v
    return rd


def configure_logging(module=None):
    # TODO: make this a lot better
    if module:
        format = ("%(asctime)s %(name)s %(levelname)s " + module +
                  " %(message)s")
    else:
        format = "%(asctime)s %(name)s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format, datefmt="%H:%M:%S")


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


def find_bill(query, fields=None):
    bill = db.bills.find_one(query, fields=fields)
    if not bill and 'bill_id' in query:
        bill_id = query.pop('bill_id')
        query['alternate_bill_ids'] = bill_id
        bill = db.bills.find_one(query, fields=fields)
    return bill
