from bson import ObjectId

from django.shortcuts import render, redirect
from django.conf import settings as django_settings
from django.http import Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from billy.core import db, settings
from billy.utils import metadata


if django_settings.DEBUG:
    def login_required(f):      # NOQA
        return f


@login_required
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

    return render(request, 'billy/matching.html', {
        "metadata": meta,
        "unmatched_ids": unmatched_ids,
        "all_ids": sorted_ids,
        "committees": committees,
        "known_objs": known_objs,
        "legs": legs
    })


@login_required
def remove(request, abbr=None, id=None):
    db.manual.name_matchers.remove({"_id": ObjectId(id)}, safe=True)
    return redirect('admin_matching', abbr)


@login_required
@require_http_methods(["POST"])
def commit(request, abbr):
    ids = dict(request.POST)
    for eyedee in ids:
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
