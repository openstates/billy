import os
import re
import time
import json
import copy
import datetime

from bson.son import SON
import pymongo.errors
import name_tools

from billy.core import db, settings
from billy.importers.names import attempt_committee_match


def _get_property_dict(schema):
    """ given a schema object produce a nested dictionary of fields """
    pdict = {}
    for k, v in schema['properties'].iteritems():
        pdict[k] = {}
        if 'items' in v and 'properties' in v['items']:
            pdict[k] = _get_property_dict(v['items'])
    pdict[settings.LEVEL_FIELD] = {}
    return pdict


# load standard fields from schema files
standard_fields = {}
for _type in ('bill', 'person', 'committee', 'metadata', 'vote',
              'event', 'speech'):
    fname = os.path.join(os.path.split(__file__)[0],
                         '../schemas/%s.json' % _type)
    schema = json.load(open(fname))
    standard_fields[_type] = _get_property_dict(schema)


def insert_with_id(obj):
    """
    Generates a unique ID for the supplied legislator/committee/bill
    and inserts it into the appropriate collection.
    """
    if '_id' in obj:
        raise ValueError("object already has '_id' field")

    # add created_at/updated_at on insert
    obj['created_at'] = datetime.datetime.utcnow()
    obj['updated_at'] = obj['created_at']

    if obj['_type'] == 'person' or obj['_type'] == 'legislator':
        collection = db.legislators
        id_type = 'L'
    elif obj['_type'] == 'committee':
        collection = db.committees
        id_type = 'C'
    elif obj['_type'] == 'bill':
        collection = db.bills
        id_type = 'B'
    else:
        raise ValueError("unknown _type for object")

    # get abbr
    abbr = obj[settings.LEVEL_FIELD].upper()

    id_reg = re.compile('^%s%s' % (abbr, id_type))

    # Find the next available _id and insert
    id_prefix = '%s%s' % (abbr, id_type)
    cursor = collection.find({'_id': id_reg}).sort('_id', -1).limit(1)

    try:
        new_id = int(cursor.next()['_id'][len(abbr) + 1:]) + 1
    except StopIteration:
        new_id = 1

    while True:
        if obj['_type'] == 'bill':
            obj['_id'] = '%s%08d' % (id_prefix, new_id)
        else:
            obj['_id'] = '%s%06d' % (id_prefix, new_id)
        obj['_all_ids'] = [obj['_id']]

        if obj['_type'] in ['person', 'legislator']:
            obj['leg_id'] = obj['_id']

        try:
            return collection.insert(obj, safe=True)
        except pymongo.errors.DuplicateKeyError:
            new_id += 1


def _timestamp_to_dt(timestamp):
    tstruct = time.localtime(timestamp)
    dt = datetime.datetime(*tstruct[0:6])
    if tstruct.tm_isdst:
        dt = dt - datetime.timedelta(hours=1)
    return dt


def compare_committee(ctty1, ctty2):
    def _cleanup(obj):
        ctty_junk_words = [
            "(\s+|^)standing(\s+|$)",
            "(\s+|^)committee(\s+|$)",
            "(\s+|^)on(\s+|$)",
            "(\s+|^)joint(\s+|$)",
            "(\s+|^)house(\s+|$)",
            "(\s+|^)senate(\s+|$)",
            "[,\.\!\+\/]"
        ]
        obj = obj.strip().lower()
        for junk in ctty_junk_words:
            obj = re.sub(junk, " ", obj).strip()
        obj = re.sub("\s+", " ", obj)
        obj = re.sub(r'\s+', ' ', re.sub(r'\W+', ' ', obj)).strip()
        return obj
    check_both = [
        ("", ""),
        ("&", "and")
    ]
    for old, new in check_both:
        c1 = ctty1.replace(old, new)
        c2 = ctty2.replace(old, new)
        c1 = _cleanup(c1)
        c2 = _cleanup(c2)
        if c1 == c2:
            return True
    return False


def update(old, new, collection, sneaky_update_filter=None):
    """
        update an existing object with a new one, only saving it and
        setting updated_at if something has changed

        old
            old object
        new
            new object
        collection
            collection to save changed object to
        sneaky_update_filter
            a filter for updates to object that should be ignored
            format is a dict mapping field names to a comparison function
            that returns True iff there is a change
    """
    # need_save = something has changed
    need_save = False

    locked_fields = old.get('_locked_fields', [])

    for key, value in new.items():

        # don't update locked fields
        if key in locked_fields:
            continue

        if old.get(key) != value:
            if sneaky_update_filter and key in sneaky_update_filter:
                if sneaky_update_filter[key](old[key], value):
                    old[key] = value
                    need_save = True
            else:
                old[key] = value
                need_save = True

        # remove old +key field if this field no longer has a +
        plus_key = '+%s' % key
        if plus_key in old:
            del old[plus_key]
            need_save = True

    if need_save:
        old['updated_at'] = datetime.datetime.utcnow()
        collection.save(old, safe=True)

    return need_save


def convert_timestamps(obj):
    """
    Convert unix timestamps in the scraper output to python datetimes
    so that they will be saved properly as Mongo datetimes.
    """
    for key in ('date', 'when', 'end', 'start_date', 'end_date'):
        value = obj.get(key)
        if value:
            try:
                obj[key] = _timestamp_to_dt(value)
            except TypeError:
                raise TypeError("expected float for %s, got %s" % (key, value))

    for key in ('sources', 'actions', 'votes', 'roles'):
        for child in obj.get(key, []):
            convert_timestamps(child)

    return obj


def split_name(obj):
    """
    If the supplied legislator/person object is missing 'first_name'
    or 'last_name' then use name_tools to split.
    """
    if obj['_type'] in ('person', 'legislator'):
        for key in ('first_name', 'last_name'):
            if key not in obj or not obj[key]:
                # Need to split
                (obj['first_name'], obj['last_name'],
                 obj['suffixes']) = name_tools.split(obj['full_name'])[1:]
                break

    return obj


def _make_plus_helper(obj, fields):
    """ add a + prefix to any fields in obj that aren't in fields """
    new_obj = {}

    for key, value in obj.iteritems():
        if key in fields or key.startswith('_'):
            # if there's a subschema apply it to a list or subdict
            if fields.get(key):
                if isinstance(value, list):
                    value = [_make_plus_helper(item, fields[key])
                             for item in value]
            # assign the value (modified potentially) to the new_obj
            new_obj[key] = value
        else:
            # values not in the fields dict get a +
            new_obj['+%s' % key] = value

    return new_obj


def make_plus_fields(obj):
    """
    Add a '+' to the key of non-standard fields.

    dispatch to recursive _make_plus_helper based on _type field
    """
    fields = standard_fields.get(obj['_type'], dict())
    return _make_plus_helper(obj, fields)


def prepare_obj(obj):
    """
    Clean up scraped objects in preparation for MongoDB.
    """
    convert_timestamps(obj)

    if obj['_type'] in ('person', 'legislator'):
        split_name(obj)

    return make_plus_fields(obj)


def next_big_id(abbr, letter, collection):
    query = SON([('_id', abbr)])
    update = SON([('$inc', SON([('seq', 1)]))])
    seq = db.command(SON([('findandmodify', collection),
                          ('query', query),
                          ('update', update),
                          ('new', True),
                          ('upsert', True)]))['value']['seq']
    return "%s%s%08d" % (abbr.upper(), letter, seq)


def merge_legislators(leg1, leg2):
    assert leg1['_id'][:3] == leg2['_id'][:3]
    assert leg1['_id'] != leg2['_id']
    if leg1['_id'] > leg2['_id']:
        leg1, leg2 = leg2, leg1

    # use deep copy for roles
    leg1 = copy.deepcopy(leg1)
    leg2 = copy.deepcopy(leg2)

    roles = 'roles'
    old_roles = 'old_roles'

    no_compare = {'_id', 'leg_id', '_all_ids', '_locked_fields', 'created_at',
                  'updated_at', roles, old_roles}

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

    if len(leg2[roles]) == 0:
        raise AssertionError("The new legislator has no roles. "\
            "This merge should be done by hand.")
    if leg1[roles] != leg2[roles]:
        # OK. Let's dump the current roles into the old roles.
        # WARNING: This code *WILL* drop current ctty appointments.
        #  What this means:
        #      In the case where someone goes from chamber L->U, and is on
        #      joint-ctty A, moves to U, we will *LOSE* joint-ctty from
        #      old_roles & roles!! There's a potenital for data loss, but it's
        #      not that big of a thing.
        #   -- paultag & jamesturk, 02-02-2012
        if len(leg1[roles]) > 0 and leg2[roles][0] != leg1[roles][0]:
            crole = leg1[roles][0]
            try:
                leg1[old_roles][crole['term']].append(crole)
            except KeyError:
                try:
                    leg1[old_roles][crole['term']] = [crole]
                except KeyError:
                    # dear holy god this needs to be fixed.
                    leg1[old_roles] = {crole['term']: [crole]}

        if len(leg2[roles]) > 0:
            # OK. We've migrated the newly old roles to the old_roles entry.
            leg1[roles] = [leg2[roles][0]]

    # copy over old_roles from other terms
    for term in leg2.get('old_roles', {}):
        if term not in leg1['old_roles']:
            leg1['old_roles'][term] = leg2['old_roles'][term]

    return (leg1, leg2['_id'])

__committee_ids = {}


def get_committee_id(abbr, chamber, committee):

    manual = attempt_committee_match(abbr,
                                     chamber,
                                     committee)

    if manual:
        return manual

    key = (abbr, chamber, committee)
    if key in __committee_ids:
        return __committee_ids[key]

    spec = {settings.LEVEL_FIELD: abbr, 'chamber': chamber,
            'committee': committee, 'subcommittee': None}

    comms = db.committees.find(spec)

    if comms.count() != 1:
        flag = 'Committee on'
        if flag not in committee:
            spec['committee'] = 'Committee on ' + committee
        else:
            spec['committee'] = committee.replace(flag, "").strip()
        comms = db.committees.find(spec)

    if comms and comms.count() == 1:
        __committee_ids[key] = comms[0]['_id']
    else:
        # last resort :(
        comm_id = get_committee_id_alt(abbr, committee, chamber)
        __committee_ids[key] = comm_id

    return __committee_ids[key]


def get_committee_id_alt(abbr, name, chamber):
    matched_committee = None
    spec = {settings.LEVEL_FIELD: abbr, "chamber": chamber}
    if chamber is None:
        del(spec['chamber'])
    comms = db.committees.find(spec)
    for committee in comms:
        c = committee['committee']
        if committee['subcommittee'] is not None:
            c += " %s" % (committee['subcommittee'])

        if compare_committee(name, c):
            if not matched_committee is None:
                return None  # In the event we match more then one committee.
            matched_committee = committee['_id']

    if matched_committee is None and not chamber is None:
        matched_committee = get_committee_id_alt(abbr, name, None)

    return matched_committee
