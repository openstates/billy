import csv
import random
from collections import defaultdict

from billy import db
from billy.utils import metadata

from django.http import Http404, HttpResponse
from django.views.decorators.cache import never_cache
from django.shortcuts import render_to_response

def keyfunc(obj):
    try:
        return int(obj['district'])
    except ValueError:
        return obj['district']

def _csv_response(request, template, data):
    if 'csv' in request.REQUEST:
        resp = HttpResponse(mimetype="text/plain")
        out = csv.writer(resp)
        for item in data:
            out.writerow(item)
        return resp
    else:
        return render_to_response(template, {'data':data})



def browse_index(request, template='billy/index.html'):
    rows = []

    for report in db.reports.find():
        report['id'] = report['_id']
        meta = db.metadata.find_one({'_id': report['_id']})
        report['name'] = meta['name']
        report['bills']['typed_actions'] = (100 -
                                report['bills']['actions_per_type'].get('other', 100))
        # districts
        #districts = list(db.districts.find({'abbr': report['id']}))
        #report['upper_districts'] = sum(d['num_seats'] for d in districts
        #                             if d['chamber'] == 'upper')
        #report['lower_districts'] = sum(d['num_seats'] for d in districts
        #                             if d['chamber'] == 'lower')
        rows.append(report)

    rows.sort(key=lambda x: x['id'])

    return render_to_response(template, {'rows': rows})


def overview(request, abbr):
    meta = metadata(abbr)
    report = db.reports.find_one({'_id': abbr})
    if not meta or not report:
        raise Http404

    context = {}
    context['metadata'] = meta
    context['report'] = report

    return render_to_response('billy/state_index.html', context)


def bills(request, abbr):
    meta = metadata(abbr)
    level = meta['level']
    if not meta:
        raise Http404

    sessions = []
    for term in meta['terms']:
        for session in term['sessions']:
            stats = _bill_stats_for_session(level, abbr, session)
            stats['session'] = session
            sessions.append(stats)

    return render_to_response('billy/bills.html',
                              {'sessions': sessions, 'metadata': meta})


def other_actions(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    return _csv_response(request, 'billy/other_actions.html',
                         sorted(report['bills']['other_actions'].items()))

def unmatched_leg_ids(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    combined_sets = (set(report['bills']['unmatched_leg_ids']) |
                     set(report['bills']['unmatched_leg_ids']))
    return _csv_response(request, 'billy/unmatched_leg_ids.html',
                         sorted(combined_sets))

def uncategorized_subjects(request, abbr):
    report = db.reports.find_one({'_id': abbr})
    if not report:
        raise Http404
    subjects = sorted(report['bills']['uncategorized_subjects'].items(),
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

    spec = {'level': level, level: abbr.lower(), 'session': latest_session}

    count = db.bills.find(spec).count()
    bill = db.bills.find(spec)[random.randint(0, count - 1)]

    return render_to_response('billy/bill.html', {'bill': bill})


def bill(request, abbr, session, id):
    level = metadata(abbr)['level']
    bill = db.bills.find_one({'level': level, level: abbr,
                              'session':session, 'bill_id':id.upper()})
    if not bill:
        raise Http404

    return render_to_response('billy/bill.html', {'bill': bill})


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

    return render_to_response('billy/legislators.html', {
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

    return render_to_response('billy/legislator.html', {'leg': leg,
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

    return render_to_response('billy/committees.html', {
        'upper_coms': upper_coms,
        'lower_coms': lower_coms,
        'joint_coms': joint_coms,
        'metadata': meta,
    })
