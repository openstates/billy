import re
import pdb
import json
import types
import urllib
import random
import pymongo
import decimal
import functools
import unicodecsv
from operator import itemgetter
from itertools import chain, imap
from collections import defaultdict

from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.shortcuts import render, render_to_response

from billy import db
from billy.utils import metadata
from billy.scrape import JSONDateEncoder
from billy.importers.utils import merge_legislators


def keyfunc(obj):
    try:
        return int(obj['district'])
    except ValueError:
        return obj['district']

def _csv_response(request, template, data):
    if 'csv' in request.REQUEST:
        resp = HttpResponse(mimetype="text/plain")
        out = unicodecsv.writer(resp)
        for item in data:
            out.writerow(item)
        return resp
    else:
        return render(request, template, {'data':data})



def browse_index(request, template='billy/index.html'):
    rows = []

    for report in db.reports.find():
        report['id'] = report['_id']
        meta = db.metadata.find_one({'_id': report['_id']})
        report['name'] = meta['name']
        report['bills']['typed_actions'] = (100 -
                                report['bills']['actions_per_type'].get('other', 100))
        rows.append(report)

    rows.sort(key=lambda x: x['name'])

    return render(request, template, {'rows': rows, 'nocontainer' : True})


def overview(request, abbr):
    meta = metadata(abbr)
    report = db.reports.find_one({'_id': abbr})
    if not meta or not report:
        raise Http404

    context = {}
    context['metadata'] = meta
    context['report'] = report

    return render(request, 'billy/state_index.html', context)


@never_cache
def bills(request, abbr):

    meta = metadata(abbr)

    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404

    sessions = report['bills']['sessions']


    # ------------------------------------------------------------------------
    # Get data for the tables for counts, types, etc. 
    tablespecs = [
        ('Bill Counts',      {'rownames': ['upper_count','lower_count',
                                      'version_count', 'versionless_count']}),
        ('Bill Types',       {'keypath': ['bill_types']}),
        ('Actions by Type',  {'keypath': ['actions_per_type']}),
        ('Actions by Actor', {'keypath': ['actions_per_actor']}),
    ]

    tables = []

    for name, spec in tablespecs:

        column_names = []
        rows = defaultdict(list)
        tabledata = {'title': name,
                     'column_names': column_names,
                     'rows': rows}
        for session, context in sessions.items():
            if 'keypath' in spec:
                for k in spec['keypath']:
                    context = context[k]
            column_names.append(session)
            rownames = spec.get('rownames', context)
            for r in rownames:
                rows[r].append(context[r])
        tabledata['rows'] = dict(rows)
        tables.append(tabledata)

    # ------------------------------------------------------------------------
    # Render the tables.
    render = functools.partial(render_to_string, 'billy/bills_table.html')
    tables = map(render, tables)

    return render_to_response( "billy/bills.html",
                              dict(tables=tables, metadata=meta,
                                   sessions=sessions))

def summary_index(request, abbr):

    meta = metadata(abbr)
    session = request.GET['session']

    object_types = 'votes actions versions sponsors documents sources'.split()

    def build(context_set):
        summary = defaultdict(int)
        for c in context_set:
            for k, v in c.items():
                summary[k] += 1
        return dict(summary)

    def build_state(abbr):

        bills = list(db.bills.find({'state': abbr, 'session': session}))
        res = {}
        for k in object_types:
            res[k] = build(chain.from_iterable(map(itemgetter(k), bills)))

        res.update(bills=build(bills))

        return res
    summary = build_state(abbr)
    return render(request, 'billy/summary_index.html', locals())


def summary_object_key(request, abbr, urlencode=urllib.urlencode,
                       collections=("bills", "legislators", "committees"),
                       dumps=json.dumps, Decimal=decimal.Decimal):
    meta = metadata(abbr)
    session = request.GET['session']
    object_type = request.GET['object_type']
    key = request.GET['key']
    spec = {'state': abbr, 'session': session}

    if object_type in collections:
        collection = getattr(db, object_type)
        fields_key = key
        objs = collection.find(spec, {fields_key: 1})
        objs = imap(itemgetter(key), objs)
    else:
        collection = db.bills
        fields_key = '%s.%s' % (object_type, key)
        objs = collection.find(spec, {fields_key: 1})
        objs = imap(itemgetter(object_type), objs)
        def get_objects(objs):
            for _list in objs:
                for _obj in _list:
                    try:
                        yield _obj[key]
                    except KeyError:
                        pass
        objs = get_objects(objs)

    objs = (dumps(obj, cls=JSONDateEncoder) for obj in objs)
    counter = defaultdict(Decimal)
    for obj in objs:
        counter[obj] += 1

    params = lambda val: urlencode(dict(object_type=object_type,
                                        key=key, val=val, session=session))

    total = len(counter)
    objs = sorted(counter, key=counter.get, reverse=True)
    objs = ((obj, counter[obj], counter[obj]/total, params(obj)) for obj in objs)
    return rendert(request, 'billy/summary_object_key.html', locals())

def summary_object_key_vals(request, abbr, urlencode=urllib.urlencode,
                            collections=("bills", "legislators", "committees")):
    meta = metadata(abbr)
    session = request.GET['session']
    object_type = request.GET['object_type']
    key = request.GET['key']
    val = json.loads(request.GET['val'])
    spec = {'state': abbr, 'session': session}
    fields = {'_id': 1}

    if object_type in collections:
        spec.update({key: val})
        objects = getattr(db, object_type).find(spec, fields)
        objects = ((object_type, obj['_id']) for obj in objects)
    else:
        spec.update({'.'.join([object_type, key]): val})
        objects = db.bills.find(spec, fields)
        objects = (('bills', obj['_id']) for obj in objects)

    spec = json.dumps(spec, cls=JSONDateEncoder, indent=4)

    return render(request, 'billy/summary_object_keyvals.html', locals())

def object_json(request, collection, _id,
                re_attr=re.compile(r'^    "(.{1,100})":', re.M)):

    obj = getattr(db, collection).find_one(_id)
    obj_isbill = (obj['_type'] == 'bill')
    if obj_isbill:
        try:
            obj_url = obj['sources'][0]['url']
        except:
            pass

    obj_id = obj['_id']
    obj_json = json.dumps(obj, cls=JSONDateEncoder, indent=4)
    keys = sorted(obj)

    def subfunc(m, tmpl='    <a name="%s">%s:</a>'):
        val = m.group(1)
        return tmpl % (val, val)

    for k in obj:
        obj_json = re_attr.sub(subfunc, obj_json)

    tmpl = '<a href="{0}">{0}</a>'
    obj_json = re.sub('"(http://.+?)"',
                      lambda m: tmpl.format(*m.groups()), obj_json)

    return render(request, 'billy/object_json.html', locals())

def other_actions(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    return _csv_response(request, 'billy/other_actions.html',
                         sorted(report['bills']['other_actions']))


def unmatched_leg_ids(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    bill_unmatched = set(tuple(i) for i in
                         report['bills']['unmatched_leg_ids'])
    com_unmatched = set(tuple(i) for i in
                         report['committees']['unmatched_leg_ids'])
    combined_sets = bill_unmatched | com_unmatched
    return _csv_response(request, 'billy/unmatched_leg_ids.html',
                         sorted(combined_sets))

def uncategorized_subjects(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    subjects = sorted(report['bills']['uncategorized_subjects'],
                      key=lambda t: (t[1],t[0]), reverse=True)
    return _csv_response(request, 'billy/uncategorized_subjects.html',
                         subjects)

@never_cache
def random_bill(request, abbr):
    meta = metadata(abbr)
    if not meta:
        raise Http404

    level = meta['level']
    latest_session = meta['terms'][-1]['sessions'][-1]

    random_flag = "limit"

    modi_flag = ""
    if random_flag in request.GET:
        modi_flag = request.GET[random_flag]

    basic_specs = {
        "no_versions" : { 'versions' : [] },
        "no_sponsors" : { 'sponsors' : [] },
        "no_actions"  : { 'actions'  : [] }
    }

    default = True
    spec = {
        'level' : level,
        level   : abbr.lower(),
        'session': latest_session
    }

    if modi_flag == 'bad_vote_counts':
        bad_vote_counts = db.reports.find_one({'_id': abbr})['bills']['bad_vote_counts']
        spec = {'_id': {'$in': bad_vote_counts}}
        default = False

    if modi_flag in basic_specs:
        default = False
        spec.update( basic_specs[modi_flag] )

    count = db.bills.find(spec).count()
    if count:
        bill = db.bills.find(spec)[random.randint(0, count - 1)]
        warning = None
    else:
        bill = None
        warning = 'No bills matching the criteria were found.'


    context = {
        'bill'   : bill,
        'random' : True,
        'state' : abbr.lower(),
        'warning': warning,
    }

    if default and modi_flag != "":
        context["warning"] = \
"""
 It looks like you've set a limit flag, but the flag was not processed by
 billy. Sorry about that. This might be due to a programming error, or a
 bad guess of the URL flag. Rather then making a big fuss over this, i've just
 got a list of all random bills. Better luck next time!
"""

    return render(request, 'billy/bill.html', context)


def bill(request, abbr, session, id):
    level = metadata(abbr)['level']
    bill = db.bills.find_one({'level': level, level: abbr,
                              'session':session, 'bill_id':id.upper()})
    if not bill:
        raise Http404

    return render(request, 'billy/bill.html', {'bill': bill})


def bill_json(request, abbr, session, id):
    level = metadata(abbr)['level']
    bill = db.bills.find_one({'level': level, level: abbr,
                              'session':session, 'bill_id':id.upper()})
    if not bill:
        raise Http404

    _json = json.dumps(bill, cls=JSONDateEncoder, indent=4)

    return render(request, 'billy/bill_json.html', {'json': _json})


def legislators(request, abbr):
    meta = metadata(abbr)
    level = metadata(abbr)['level']

    upper_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                      'active': True, 'chamber': 'upper'})
    lower_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                      'active': True, 'chamber': 'lower'})
    inactive_legs = db.legislators.find({'level': level, level: abbr.lower(),
                                         'active': False})
    upper_legs = sorted(upper_legs, key=keyfunc)
    lower_legs = sorted(lower_legs, key=keyfunc)
    inactive_legs = sorted(inactive_legs, key=lambda x: x['last_name'])

    return render(request, 'billy/legislators.html', {
        'upper_legs': upper_legs,
        'lower_legs': lower_legs,
        'inactive_legs': inactive_legs,
        'metadata': meta,
    })


def legislator(request, id):
    leg = db.legislators.find_one({'_all_ids': id})
    if not leg:
        raise Http404

    meta = metadata(leg[leg['level']])

    return render(request, 'billy/legislator.html', {'leg': leg,
                                                        'metadata': meta})


def committees(request, abbr):
    meta = metadata(abbr)
    level = metadata(abbr)['level']

    upper_coms = db.committees.find({'level': level, level: abbr.lower(),
                                     'chamber': 'upper'})
    lower_coms = db.committees.find({'level': level, level: abbr.lower(),
                                      'chamber': 'lower'})
    joint_coms = db.committees.find({'level': level, level: abbr.lower(),
                                      'chamber': 'joint'})
    upper_coms = sorted(upper_coms)
    lower_coms = sorted(lower_coms)
    joint_coms = sorted(joint_coms)

    return render( request, 'billy/committees.html', {
        'upper_coms': upper_coms,
        'lower_coms': lower_coms,
        'joint_coms': joint_coms,
        'metadata': meta,
    })

def mom_index(request):
    return render(request, 'billy/mom_index.html' )

def mom_commit(request):
    actions = []

    leg1 = request.POST['leg1']
    leg2 = request.POST['leg2']

    leg1 = db.legislators.find_one({'_id' : leg1 })
    actions.append( "Loaded Legislator '%s as `leg1''" % leg1['leg_id'] )
    leg2 = db.legislators.find_one({'_id' : leg2 })
    actions.append( "Loaded Legislator '%s as `leg2''" % leg2['leg_id'] )

    # XXX: Re-direct on None

    merged, remove = merge_legislators( leg1, leg2 )
    actions.append( "Merged Legislators as '%s'" % merged['leg_id'] )

    db.legislators.remove({ '_id' : remove }, safe=True)
    actions.append( "Deleted Legislator (which had the ID of %s)" %
        remove )

    db.legislators.save( merged, safe=True )
    actions.append( "Saved Legislator %s with merged data" % merged['leg_id'] )

    for attr in merged:
        merged[attr] = _mom_mangle( merged[attr] )

    return render( request, 'billy/mom_commit.html', {
            "merged"  : merged,
            "actions" : actions
        })

def _mom_attr_diff( merge, leg1, leg2 ):
    mv_info = {
        "1" : "Root Legislator",
        "2" : "Duplicate Legislator",
        "U" : "Unchanged",
        "N" : "New Information"
    }

    mv = {}
    for key in merge:
        if key in leg1 and key in leg2:
            if leg1[key] == leg2[key]:
                mv[key] = "U"
            elif key == leg1[key]:
                mv[key] = "1"
            else:
                mv[key] = "2"
        elif key in leg1:
            mv[key] = "1"
        elif key in leg2:
            mv[key] = "2"
        else:
            mv[key] = "N"
    return ( mv, mv_info )

def _mom_mangle( attr ):
    jsonify = json.dumps
    args    = {
        "sort_keys" : True,
        "indent"    : 4
    }
    if isinstance( attr, types.ListType ):
        return json.dumps( attr, **args )
    if isinstance( attr, types.DictType ):
        return json.dumps( attr, **args )
    return attr

def mom_merge(request):
    leg1 = "leg1"
    leg2 = "leg2"

    leg1 = request.GET[leg1]
    leg2 = request.GET[leg2]

    leg1_db  = db.legislators.find_one({'_id' : leg1})
    leg2_db  = db.legislators.find_one({'_id' : leg2})

    if leg1_db == None or leg2_db == None: # XXX: Break this out into it's own
        #                                         error page.
        nonNull = leg1_db if leg1_db != None else leg2_db
        if nonNull != None:
            nonID   = leg1    if nonNull['_id'] == leg1 else leg2
        else:
            nonID   = None

        return render(request, 'billy/mom_error.html', {
            "leg1"    : leg1,
            "leg2"    : leg2,
            "leg1_db" : leg1_db,
            "leg2_db" : leg2_db,
            "same"    : nonNull,
            "sameid"  : nonID
        })

    leg1, leg2 = leg1_db, leg2_db
    merge, toRemove = merge_legislators( leg1, leg2 )
    mv, mv_info = _mom_attr_diff( merge, leg1, leg2 )

    for foo in [ leg1, leg2, merge ]:
        for attr in foo:
            foo[attr] = _mom_mangle( foo[attr] )

    return render(request, 'billy/mom_merge.html', {
       'leg1'   : leg1,
       'leg2'   : leg2,
       'merge'  : merge,
       'merge_view'      : mv,
       'remove'          : toRemove,
       'merge_view_info' : mv_info })

