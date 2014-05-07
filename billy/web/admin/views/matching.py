from collections import defaultdict, OrderedDict

from bson import ObjectId

from django.shortcuts import render, redirect
from django.http import Http404
from django.views.decorators.http import require_http_methods

from billy.core import db, settings
from billy.utils import metadata
from billy.web.admin.decorators import is_superuser


@is_superuser
def edit(request, abbr):
    meta = metadata(abbr)
    report = db.reports.find_one({'_id': abbr})
    legs = list(db.legislators.find({settings.LEVEL_FIELD: abbr}))
    committees = list(db.committees.find({settings.LEVEL_FIELD: abbr}))

    matchers = db.manual.name_matchers.find({"abbr": abbr})
    sorted_ids = {}
    known_objs = {}
    seen_names = set()

    for leg in legs:
        known_objs[leg['_id']] = leg
    for com in committees:
        known_objs[com['_id']] = com

    for item in matchers:
        sorted_ids[item['_id']] = item
        seen_names.add((item['term'], item['chamber'], item['name']))

    if not report:
        raise Http404('No reports found for abbreviation %r.' % abbr)
    bill_unmatched = set(tuple(i + ['sponsor']) for i in
                         report['bills']['unmatched_sponsors'])
    vote_unmatched = set(tuple(i + ['vote']) for i in
                         report['votes']['unmatched_voters'])
    com_unmatched = set(tuple(i + ['committee']) for i in
                        report['committees']['unmatched_leg_ids'])
    combined_sets = bill_unmatched | vote_unmatched | com_unmatched
    unmatched_ids = []

    for term, chamber, name, id_type in combined_sets:
        if (term, chamber, name) in seen_names:
            continue

        unmatched_ids.append((term, chamber, name, id_type))

    LEG_OPTIONS = u'<option value="Unknown" >Unknown</option>'
    for leg in legs:
        kwargs = leg.copy()
        if 'chamber' not in kwargs:
            kwargs['chamber'] = None

        LEG_OPTIONS += u"""
        <option value="{leg_id}" >
             {first_name} {last_name}
             {chamber}
             ({leg_id})
         </option>""".format(**kwargs)


    COM_OPTIONS = u'<option value="Unknown" >Unknown</option>'
    for committee in committees:
        kwargs = committee.copy()
        COM_OPTIONS += u"""
        <option value="{_id}" >
            {chamber}/{committee}
            {subcommittee}
            ({_id})
        </option>
        """.format(**kwargs)

    return render(request, 'billy/matching.html', {
        "metadata": meta,
        "unmatched_ids": unmatched_ids,
        "all_ids": sorted_ids,
        "committees": committees,
        "known_objs": known_objs,
        "legs": legs,
        "leg_options": LEG_OPTIONS,
        "com_options": COM_OPTIONS,
    })


@is_superuser
def remove(request, abbr=None, id=None):
    db.manual.name_matchers.remove({"_id": ObjectId(id)}, safe=True)
    return redirect('admin_matching', abbr)


@is_superuser
@require_http_methods(["POST"])
def commit(request, abbr):
    ids = dict(request.POST)
    for eyedee in ids:
        if eyedee == 'csrfmiddlewaretoken':
            continue
        typ, term, chamber, name = eyedee.split(",", 3)
        value = ids[eyedee][0]
        if value == "Unknown":
            continue

        db.manual.name_matchers.update({"name": name, "term": term,
                                        "abbr": abbr, "chamber": chamber},
                                       {"name": name, "term": term,
                                        "abbr": abbr, "obj_id": value,
                                        "chamber": chamber, "type": typ},
                                       upsert=True, safe=True)

    return redirect('admin_matching', abbr)


def debug(request, abbr):
    '''This view lets you view all names that would show up
    in name matching sorted by length, but also click through
    to the object in which they were found, to aid in debugging
    scrapers.
    '''
    names = defaultdict(set)
    spec = {settings.LEVEL_FIELD: abbr}

    for bill in db.bills.find(spec):
        _id = bill['_id']
        for sponsor in bill['sponsors']:
            names[sponsor['name']].add(('bills', _id))

    for committee in db.committees.find(spec):
        _id = committee['_id']
        for member in committee['members']:
            names[member['name']].add(('committees', _id))

    for legislator in db.legislators.find(spec):
        names[legislator['full_name']].add(('legislators', legislator['_id']))

    for vote in db.votes.find(spec):
        _id = vote['_id']
        for vote_val in 'yes', 'no', 'other':
            votes = vote[vote_val + '_votes']
            for voter in votes:
                names[voter['name']].add(('votes', _id))

    # Order them by name length.
    ordered_names = OrderedDict()
    for name, value in sorted(names.items(), key=lambda item: len(item[0])):
        # And make the set sliceable.
        ordered_names[name] = list(value)

    return render(request, 'billy/matching_debug.html', {
        "abbr": abbr,
        "names": ordered_names,
    })
