import re
import urllib
import urlparse
import logging

from billy import db


# metadata cache
__metadata = {}

# Adapted from NLTK's english stopwords
stop_words = [
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
    'you', 'your', 'yours', 'yourself', 'yourselves',
    'he', 'him', 'his', 'himself', 'she', 'her', 'hers',
    'herself', 'it', 'its', 'itself', 'they',
    'them', 'their', 'theirs', 'themselves', 'what',
    'which',  'who', 'whom', 'this', 'that', 'these', 'those',
    'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does',
    'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
    'because', 'as', 'until', 'while', 'of', 'at', 'by',
    'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after',
    'above', 'below', 'to', 'from', 'up', 'down', 'in',
    'out', 'on', 'off', 'over', 'under', 'again', 'further',
    'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very',
    's', 't', 'can', 'will', 'just', 'don', 'should',
    'now', '']


def tokenize(str):
    return re.split(r"[\s.,!?'\"`()]+", str)


def keywordize(str):
    """
    Splits a string into words, removes common stopwords, stems and removes
    duplicates.
    """
    import jellyfish
    return set([jellyfish.porter_stem(word.lower().encode('ascii',
                                                          'ignore'))
                for word in tokenize(str)
                if (word.isalpha() or word.isdigit()) and
                word.lower() not in stop_words])


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


def term_for_session(abbr, session):
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


def configure_logging(verbosity_count=0, module=None):
    verbosity = {0: logging.WARNING, 1: logging.INFO}.get(verbosity_count,
                                                          logging.DEBUG)
    if module:
        format = ("%(asctime)s %(name)s %(levelname)s " + module +
                  " %(message)s")
    else:
        format = "%(asctime)s %(name)s %(levelname)s %(message)s"
    logging.basicConfig(level=verbosity, format=format, datefmt="%H:%M:%S")

def merge_legislators(leg1, leg2):
    assert leg1['_id'] != leg2['_id']
    if leg1['_id'] > leg2['_id']:
        leg1, leg2 = leg2, leg1

    no_compare = set(('_id', 'leg_id', '_all_ids', '_locked_fields',
        'created_at', 'updated_at', 'roles', 'old_roles' ))

    leg1['_all_ids'] += leg2['_all_ids']

    # get set of keys that appear in both legislators and are not blacklisted
    leg1keys = set(leg1.keys())
    leg2keys = set(leg2.keys())
    compare_keys = (leg1keys & leg2keys) - no_compare
    leg1_locked = leg1.get('_locked_fields', [])
    leg2_locked = leg2.get('_locked_fields', [])

    # if a key is in both, copy 2 to 1 if they differ and key is locked in 2
    # or unlocked in 1
    for key in compare_keys:
        if (leg1[key] != leg2[key] and leg2[key] and (key in leg2_locked or
                                                      key not in leg1_locked)):
            leg1[key] = leg2[key]

    # locked is now union of the two
    leg1['_locked_fields'] = list(set(leg1_locked + leg2_locked))

    # copy new keys over to old legislator
    for key in leg2keys - leg1keys:
        leg1[key] = leg2[key]

    # XXX: Set updated_at

    return leg1
