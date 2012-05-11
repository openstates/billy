import re
import json
import time
import types
import urllib
import random
import pymongo
import decimal
import functools
import unicodecsv
import urlparse
from operator import itemgetter
from itertools import chain, imap
from collections import defaultdict, OrderedDict

from bson.objectid import ObjectId

from django.http import Http404, HttpResponse
from django.core import urlresolvers
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.shortcuts import render

from billy import db
from billy.utils import metadata, find_bill
from billy.scrape import JSONDateEncoder
from billy.importers.utils import merge_legislators


def _meta_and_report(abbr):
    meta = metadata(abbr)
    report = db.reports.find_one({'_id': abbr})
    if not meta or not report:
        raise Http404
    return meta, report


def keyfunc(obj):
    try:
        return int(obj['district'])
    except ValueError:
        return obj['district']


def _csv_response(request, csv_name, columns, data, abbr):
    if 'csv' in request.REQUEST:
        resp = HttpResponse(mimetype="text/plain")
        resp['Content-Disposition'] = 'attachment; filename=%s_%s.csv' % (
            abbr, csv_name)
        out = unicodecsv.writer(resp)
        for item in data:
            out.writerow(item)
        return resp
    else:
        return render(request, 'billy/generic_table.html',
                      {'columns': columns,
                       'data':data, 'metadata': metadata(abbr)})


def browse_index(request, template='billy/index.html'):
    rows = []

    spec = {}
    only = request.GET.get('only', [])
    if only:
        spec = {'_id': {'$in': only.split(',')}}

    for report in db.reports.find(spec):
        report['id'] = report['_id']
        meta = db.metadata.find_one({'_id': report['_id']})
        report['name'] = meta['name']
        report['unicameral'] = ('lower_chamber_name' not in meta)
        report['bills']['typed_actions'] = (100 -
            report['bills']['actions_per_type'].get('other', 100))
        rows.append(report)

    rows.sort(key=lambda x: x['name'])

    return render(request, template, {'rows': rows})


def overview(request, abbr):
    meta, report = _meta_and_report(abbr)
    context = {}
    context['metadata'] = meta
    context['report'] = report
    context['sessions'] = db.bills.find({'state': abbr}).distinct('session')

    try:
        runlog = db.billy_runs.find({
            "scraped.state" : abbr
        }).sort( "scraped.started", direction=pymongo.DESCENDING )[0]
        # This hack brought to you by Django's inability to do subtraction
        # in the template :)
        runlog['scraped']['time_delta'] = (runlog['scraped']['ended'] -
                                           runlog['scraped']['started'])
        context['runlog'] = runlog
        if "failure" in runlog:
            context['warning_title'] = "This build is currently broken!"
            context['warning'] = """
The last scrape was a failure. Check in the run log section for more details,
or check out the scrape run report page for this state.
"""
    except IndexError:
        runlog = False

    return render(request, 'billy/state_index.html', context)


def metadata_json(request, abbr):
    re_attr = re.compile(r'^    "(.{1,100})":', re.M)
    obj = metadata(abbr)
    obj_json = json.dumps(obj, indent=4, cls=JSONDateEncoder)
    def subfunc(m, tmpl='    <a name="%s">%s:</a>'):
        val = m.group(1)
        return tmpl % (val, val)

    for k in obj:
        obj_json = re_attr.sub(subfunc, obj_json)

    tmpl = '<a href="{0}">{0}</a>'
    obj_json = re.sub('"(http://.+?)"',
                      lambda m: tmpl.format(*m.groups()), obj_json)
    context = {'metadata': obj,
               'keys': sorted(obj),
               'metadata_json': obj_json}
    return render(request, 'billy/metadata_json.html', context)


def run_detail_graph_data(request, abbr):

    def rolling_average( oldAverage, newItem, oldAverageCount ):
        """
        Simple, unweighted rolling average. If you don't get why we have
        to factor the oldAverageCount back in, it's because new values will
        have as much weight as the last sum combined if you put it over 2.
        """
        return float(
            ( newItem +  ( oldAverageCount * ( oldAverage ) ) ) /
                        ( oldAverageCount + 1 )
            )

    def _do_pie( runs ):
        excs = {}
        for run in runs:
            if "failure" in run:
                for r in run['scraped']['run_record']:
                    if "exception" in r:
                        ex = r['exception']
                        try:
                            excs[ex['type']] += 1
                        except KeyError:
                            excs[ex['type']] = 1
        ret = []
        for l in excs:
            ret.append([ l, excs[l] ])
        return ret

    def _do_stacked( runs ):
        fields = [ "legislators", "bills", "votes", "committees" ]
        ret = {}
        for field in fields:
            ret[field] = []

        for run in runs:
            guy = run['scraped']['run_record']
            for field in fields:
                try:
                    g = None
                    for x in guy:
                        if x['type'] == field:
                            g = x
                    if not g:
                        raise KeyError("Missing kruft")

                    delt = ( g['end_time'] - g['start_time'] ).total_seconds()
                    ret[field].append(delt)
                except KeyError: # XXX: THIS MESSES STUFF UP. REVISE.
                    ret[field].append(0)
        l = []
        for line in fields:
            l.append(ret[line])
        return l

    def _do_digest( runs ):
        oldAverage      = 0
        oldAverageCount = 0
        data = { "runs" : [], "avgs" : [], "stat" : [] }
        for run in runs:
            timeDelta = (
                run['scraped']['ended'] - run['scraped']['started']
            ).total_seconds()
            oldAverage = rolling_average( oldAverage, timeDelta, oldAverageCount )
            oldAverageCount += 1
            stat = "Failure" if "failure" in run else ""

            s = time.mktime(run['scraped']['started'].timetuple())

            data['runs'].append([ s, timeDelta,  stat ])
            data['avgs'].append([ s, oldAverage, '' ])
            data['stat'].append( stat )
        return data
    history_count = 50

    default_spec = { "scraped.state" : abbr }
    data = {
        "lines"   : {},
        "pies"    : {},
        "stacked" : {},
        "title"   : {}
    }

    speck = {
        "default-stacked" : { "run" : _do_stacked,
            "title" : "Last %s runs" % ( history_count ),
            "type" : "stacked",
            "spec" : {}
        },
        #"default" : { "run" : _do_digest,
        #    "title" : "Last %s runs" % ( history_count ),
        #    "type" : "lines",
        #    "spec" : {}
        #},
        #"clean"   : { "run" : _do_digest,
        #    "title" : "Last %s non-failed runs" % ( history_count ),
        #    "type" : "lines",
        #    "spec" : {
        #        "failure" : { "$exists" : False }
        #    }
        #},
        #"failure"   : { "run" : _do_digest,
        #    "title" : "Last %s failed runs" % ( history_count ),
        #    "type" : "lines",
        #    "spec" : {
        #        "failure" : { "$exists" : True  }
        #    }
        #},
        "falure-pie": { "run" : _do_pie,
            "title" : "Digest of what exceptions have been thrown",
            "type" : "pies",
            "spec" : {
                "failure" : { "$exists" : True  }
            }
        },
    }

    for line in speck:
        query = speck[line]["spec"].copy()
        query.update( default_spec )
        runs = db.billy_runs.find(query).sort(
            "scrape.start", direction=pymongo.ASCENDING )[:history_count]
        data[speck[line]['type']][line] = speck[line]["run"](runs)
        data['title'][line] = speck[line]['title']

    return HttpResponse(
        json.dumps( data ),
        #content_type="text/json"
        content_type="text/plain"
    )


def run_detail(request, obj=None):
    try:
        run = db.billy_runs.find({
            "_id" : ObjectId(obj)
        })[0]
    except IndexError as e:
        return render(request, 'billy/run_empty.html', {
            "warning" : "No records exist. Fetch returned a(n) %s" % (
                    e.__class__.__name__
            )
        })
    return render(request, 'billy/run_detail.html', {
        "run" : run,
        "metadata" : {
            "abbreviation" : run['state'],
            "name"         : run['state']
        }
    })


def state_run_detail(request, abbr):
    try:
        allruns = db.billy_runs.find({
            "scraped.state" : abbr
        }).sort( "scraped.started", direction=pymongo.DESCENDING )[:25]
        runlog = allruns[0]
    except IndexError as e:
        return render(request, 'billy/run_empty.html', {
            "warning" : "No records exist. Fetch returned a(n) %s" % (
                    e.__class__.__name__
            )
        })

    # pre-process goodies for the template
    runlog['scraped']['t_delta'] = (
        runlog['scraped']['ended'] - runlog['scraped']['started']
    )
    for entry in runlog['scraped']['run_record']:
        if not "exception" in entry:
            entry['t_delta'] = (
                entry['end_time'] - entry['start_time']
            )

    context = {
        "runlog"   : runlog,
        "allruns"  : allruns,
        "state"    : abbr,
        "metadata" : metadata(abbr),
    }

    if "failure" in runlog:
        context['warning_title'] = "Exception during Execution"
        context['warning'] = \
"""
This build had an exception during it's execution. Please check below
for the exception and error message.
"""

    return render(request, 'billy/state_run_detail.html', context)


@never_cache
def bills(request, abbr):
    meta, report = _meta_and_report(abbr)    

    terms = list(chain.from_iterable(map(itemgetter('sessions'), 
                                         meta['terms'])))
    def sorter(item, index=terms.index, len_=len(terms)):
        '''Sort session strings in order described in state's metadata.'''
        session, data = item
        return index(session)

    # Convert sessions into an ordered dict.
    sessions = report['bills']['sessions']
    sessions = sorted(sessions.items(), key=sorter)
    sessions = OrderedDict(sessions)

    def decimal_format(value, TWOPLACES=decimal.Decimal(100) ** -1):
        '''Format a float like 2.2345123 as a decimal like 2.23'''
        n = decimal.Decimal(str(value))
        n = n.quantize(TWOPLACES)
        return unicode(n)

    # Define data for the tables for counts, types, etc.
    tablespecs = [
        ('Bill Counts', {'rownames': ['upper_count', 'lower_count',
                                      'version_count']}),

        ('Bill Types', {
            'keypath': ['bill_types'],
                'summary': {
                'object_type': 'bills',
                'key': 'type',
                },
            }),

        ('Actions by Type', {
            'keypath': ['actions_per_type'],
            'summary': {
                'object_type': 'actions',
                'key': 'type',
                },
            }),

        ('Actions by Actor', {
            'keypath': ['actions_per_actor'],
            'summary': {
                'object_type': 'actions',
                'key': 'actor',
                },
            }),
        ('Quality Issues',   {'rownames': [
                                 'sourceless_count', 'sponsorless_count',
                                 'actionless_count', 'actions_unsorted',
                                 'bad_vote_counts', 'version_count',
                                 'versionless_count',

                                 'sponsors_with_leg_id',
                                 'rollcalls_with_leg_id',
                                 'have_subjects',
                                 'updated_this_year',
                                 'updated_this_month',
                                 'updated_today',
                                 'vote_passed']}),
        ]

    format_as_percent = [
        'sponsors_with_leg_id',
        'rollcalls_with_leg_id',
        'have_subjects',
        'updated_this_year',
        'updated_this_month',
        'updated_today',
        'actions_per_actor',
        'actions_per_type']

    # Create the data for each table.
    tables = []
    for name, spec in tablespecs:
        column_names = []
        rows = defaultdict(list)
        href_params = {}
        tabledata = {'abbr': abbr,
                     'title': name,
                     'column_names': column_names,
                     'rows': rows}
        contexts = []

        for session, context in sessions.items():
            column_names.append(session)
            if 'keypath' in spec:
                for k in spec['keypath']:
                    context = context[k]
            contexts.append(context)

        try:
            rownames = spec['rownames']
        except KeyError:
            rownames = reduce(lambda x, y: set(x) | set(y), contexts)

        for context in contexts:
            for r in rownames:

                val = context.get(r, 0)
                if not isinstance(val, (int, float, decimal.Decimal)):
                    val = len(val)

                use_percent = any([
                    r in format_as_percent,
                    name in ['Actions by Actor', 'Actions by Type'],
                    ])

                if use_percent and (val != 0):
                    val = decimal_format(val)
                    val += ' %'
                rows[r].append(val)

                # Link to summary/distint views.
                if 'summary' in spec:
                    try:
                        spec_key = '.'.join(spec['keypath'])
                    except KeyError:
                        spec_key = r

                    try:
                        spec_val = spec['spec'](r)
                    except KeyError:
                        spec_val = r
                    else:
                        spec_val = json.dumps(spec_val)

                    params = dict(spec['summary'], session=session,
                                  val=spec_val)

                    params = urllib.urlencode(params)
                    href_params[r] = params

        # Add the final "total" column.
        tabledata['column_names'].append('Total')
        for k, v in rows.items():
            try:
                sum_ = sum(v)
            except TypeError:
                sum_ = 'n/a'
            v.append(sum_)

        rowdata = [((r, href_params.get(r)), cells) for (r, cells) in rows.items()]
        tabledata['rowdata'] = rowdata

        tables.append(tabledata)

    # ------------------------------------------------------------------------
    # Render the tables.
    _render = functools.partial(render_to_string, 'billy/bills_table.html')
    tables = map(_render, tables)

    return render(request, "billy/bills.html",
                  dict(tables=tables, metadata=meta, sessions=sessions,
                       tablespecs=tablespecs))


def summary_index(request, abbr, session):

    meta = metadata(abbr)

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
    return render(request, 'billy/summary_object_key.html', locals())


def summary_object_key_vals(request, abbr, urlencode=urllib.urlencode,
                            collections=("bills", "legislators", "committees")):
    meta = metadata(abbr)
    session = request.GET['session']
    object_type = request.GET['object_type']
    key = request.GET['key']

    val = request.GET['val']
    try:
        val = json.loads(val)
    except ValueError:
        pass

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
    return _csv_response(request, 'other_actions', ('action', '#'),
                         sorted(report['bills']['other_actions']), abbr)


def unmatched_leg_ids(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    bill_unmatched = set(tuple(i) for i in
                         report['bills']['unmatched_leg_ids'])
    com_unmatched = set(tuple(i) for i in
                         report['committees']['unmatched_leg_ids'])
    combined_sets = bill_unmatched | com_unmatched
    return _csv_response(request, 'leg_ids', ('term', 'chamber', 'name'),
                         sorted(combined_sets), abbr)


def uncategorized_subjects(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    subjects = sorted(report['bills']['uncategorized_subjects'],
                      key=lambda t: (t[1], t[0]), reverse=True)
    return _csv_response(request, 'uncategorized_subjects', ('subject', '#'),
                         subjects, abbr)


def district_stub(request, abbr):
    def keyfunc(x):
        try:
            district = int(x[2])
        except ValueError:
            district = x[2]
        return x[1], district

    fields = ('abbr', 'chamber', 'name', 'num_seats', 'boundary_id')

    counts = defaultdict(int)
    for leg in db.legislators.find({'state': abbr, 'active': True}):
        if 'chamber' in leg:
            counts[(leg['chamber'], leg['district'])] += 1

    data = []
    for key, count in counts.iteritems():
        chamber, district =  key
        data.append((abbr, chamber, district, count, ''))

    data.sort(key=keyfunc)

    return _csv_response(request, "districts",
                         ('abbr', 'chamber', 'district', 'count', ''),
                         data, abbr)


def duplicate_versions(request, abbr):
    meta, report = _meta_and_report(abbr)

    data = report['bills']['duplicate_versions']

    return render(request, "billy/duplicate_versions.html",
                  {'metadata': meta, 'report': report})


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
        bad_vote_counts = db.reports.find_one({'_id': abbr}
                                             )['bills']['bad_vote_counts']
        spec = {'_id': {'$in': bad_vote_counts}}
        default = False

    if modi_flag in basic_specs:
        default = False
        spec.update( basic_specs[modi_flag] )
        spec.pop('session') # all sessions

    if modi_flag == 'current_term':
        default = False
        curTerms = meta['terms'][-1]['sessions']
        spec['session'] = {
            "$in" : curTerms
        }

    count = db.bills.find(spec).count()
    if count:
        bill = db.bills.find(spec)[random.randint(0, count - 1)]
        warning = None
    else:
        bill = None
        warning = 'No bills matching the criteria were found.'

    try:
        bill_id = bill['_id']
    except TypeError:
        # Bill was none (see above).
        bill_id = None

    context = {
        'bill'   : bill,
        'id': bill_id,
        'random' : True,
        'state' : abbr.lower(),
        'warning': warning,
        'metadata': meta,
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


def bill_list(request, abbr):
    meta = metadata(abbr)
    if not meta:
        raise Http404

    level = meta['level']
    spec = {'level': level, level: abbr}

    if 'version_url' in request.GET:
        version_url = request.GET.get('version_url')
        spec['versions.url'] = version_url

    bills = db.bills.find(spec)
    query_text = repr(spec)

    context = {'metadata': meta,
               'query_text': query_text,
               'bills': bills}

    return render(request, 'billy/bill_list.html', context)


def bill(request, abbr, session, id):
    meta = metadata(abbr)
    level = meta['level']
    bill = find_bill({'level': level, level: abbr,
                      'session':session, 'bill_id':id.upper()})
    if not bill:
        raise Http404

    return render(request, 'billy/bill.html',
                  {'bill': bill, 'metadata': meta, 'id': bill['_id']})


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


def events(request, abbr):
    meta = metadata(abbr)
    level = metadata(abbr)['level']

    events = db.events.find({
        'level': level,
        level: abbr.lower()
    })

    # sort and get rid of old events.

    return render(request, 'billy/events.html', {
        'events': events,
        'metadata': meta
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


def newsblogs(request):
    '''
    Demo view for news/blog aggregation.
    ''' 
    
    # Pagination insanity.
    total_count = db.feed_entries.count()
    limit = int(request.GET.get('limit', 6))
    page = int(request.GET.get('page', 1))
    if page < 1:
        page = 1
    skip = limit * (page - 1)

    # Whether display is limited to entries tagged with legislator
    # committee or bill object.
    entities = request.GET.get('entities', True)

    tab_range = range(1, int(float(total_count) / limit) + 1)
    tab = skip / limit + 1
    try:
        tab_index = tab_range.index(tab)
    except ValueError:
        tab_index = 1

    tab_range_len = len(tab_range)
    pagination_truncated = False
    if tab_range_len > 8:
        i = tab_index - 4
        if i < 0:
            i = 1
        j = tab_index
        k = j + 5
        previous = tab_range[i: j]
        current = j
        next_ = tab_range[j + 1: k]
        pagination_truncated = True
    elif tab_range_len == 8:
        previous = tab_range[:4]
        next_ = tab_range[4:]
    else:
        div, mod = divmod(tab_range_len, 2)
        if mod == 2:
            i = tab_range_len / 2
        else:
            i = (tab_range_len - 1)/ 2
        previous = tab_range[:i]
        next_ = tab_range[i:]

    # Get the data.
    state = request.GET.get('state')

    if entities is True:
        spec = {'entity_ids': {'$ne': None}}
    else:
        spec = {}
    if state:
        spec.update(state=state)

    entries = db.feed_entries.find(spec, skip=skip, limit=limit,
        sort=[('published_parsed', pymongo.DESCENDING)])
    _entries = []
    entity_types = {'L': 'legislators',
                    'C': 'committees',
                    'B': 'bills'}

    print tab_range_len, tab, previous, next_, tab_index - 4

    for entry in entries:
        summary = entry['summary']
        entity_strings = entry['entity_strings']
        entity_ids = entry['entity_ids']
        _entity_strings = []
        _entity_ids = []
        _entity_urls = []
        
        _done = []
        if entity_strings:
            for entity_string, _id in zip(entity_strings, entity_ids):
                if entity_string in _done:
                    continue
                else:
                    _done.append(entity_string)
                    _entity_strings.append(entity_string)
                    _entity_ids.append(_id)
                entity_type = entity_types[_id[2]]
                url = urlresolvers.reverse('object_json', args=[entity_type, _id])
                _entity_urls.append(url)
                summary = summary.replace(entity_string, 
                                '<b><a href="%s">%s</a></b>' % (url, entity_string))
            entity_data = zip(_entity_strings, _entity_ids, _entity_urls)
            entry['summary'] = summary
            entry['entity_data'] = entity_data
        entry['id'] = entry['_id']
        entry['host'] = urlparse.urlparse(entry['link']).netloc

        # Now hyperlink the inbox data.
        # if '_inbox_data' in entry:
        #     inbox_data = entry['_inbox_data']
        #     for entity in inbox_data['entities']:
        #         entity_data = entity['entity_data']
        #         if entity_data['type'] == 'organization':
        #             ie_url = 'http://influenceexplorer.com/organization/%s/%s'
        #             ie_url = ie_url % (entity_data['slug'], entity_data['id'])
        #             print 'found one!'
        #         else:
        #             continue
        #         summary = entry['summary']
        #         tmpl = '<a href="%s">%s</a>'
        #         for string in entity['matched_text']:
        #             summary = summary.replace(string, tmpl % (ie_url, string))
        #     entry['summary'] = summary
        
        _entries.append(entry)



    return render(request, 'billy/newsblogs.html', {
        'entries': _entries,
        'entry_count': entries.count(),
        'states': db.feed_entries.distinct('state'),
        'state': state,
        'tab_range': tab_range,
        'previous': previous,
        'next_': next_,
        'pagination_truncated': pagination_truncated,
        'page': page,
        })
