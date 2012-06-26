"""
    views specific to legislators
"""
import re
import json
import operator
import urllib2

from django.shortcuts import render
from django.http import Http404

import pymongo

from billy.models import db, Metadata, DoesNotExist
from billy.conf import settings as billy_settings

from .utils import templatename, mongo_fields
from ..forms import ChamberSelectForm


def legislators(request, abbr):
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    spec = {'active': True}

    chamber = request.GET.get('chamber', 'both')
    if chamber in ('upper', 'lower'):
        spec['chamber'] = chamber
    else:
        chamber = 'both'

    fields = mongo_fields('leg_id', 'full_name', 'photo_url', 'district',
                          'party', 'first_name', 'last_name', 'chamber',
                          'state', 'last_name')

    sort_key = 'district'
    sort_order = 1

    if request.GET:
        sort_key = request.GET.get('key', sort_key)
        sort_order = int(request.GET.get('order', sort_order))

    legislators = meta.legislators(extra_spec=spec, fields=fields)

    def sort_by_district(obj):
        matchobj = re.search(r'\d+', obj['district'])
        if matchobj:
            return int(matchobj.group())
        else:
            return obj['district']

    legislators = sorted(legislators, key=sort_by_district)

    if sort_key != 'district':
        legislators = sorted(legislators, key=operator.itemgetter(sort_key),
                             reverse=(sort_order == -1))
    else:
        legislators = sorted(legislators, key=sort_by_district,
                             reverse=bool(0 > sort_order))

    sort_order = {1: -1, -1: 1}[sort_order]
    legislators = list(legislators)
    initial = {'key': 'district', 'chamber': chamber}
    chamber_select_form = ChamberSelectForm.unbound(meta, initial=initial)

    return render(request, templatename('legislators'),
                  dict(metadata=meta,
                   chamber=chamber,
                   chamber_select_form=chamber_select_form,
                   chamber_select_template=templatename('chamber_select_form'),
                   chamber_select_collection='legislators',
                   show_chamber_column=True,
                   abbr=abbr,
                   legislators=legislators,
                   sort_order=sort_order,
                   sort_key=sort_key,
                   legislator_table=templatename('legislator_table'),
                   statenav_active='legislators'))


def legislator(request, abbr, _id, slug):
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404
    legislator = db.legislators.find_one({'_id': _id})
    if legislator is None:
        raise Http404('No legislator was found with led_id = %r' % _id)

    if not legislator['active']:
        return legislator_inactive(request, abbr, legislator)

    qurl = "%sdistricts/%s/?apikey=%s" % (
        billy_settings.API_BASE_URL,
        abbr,
        billy_settings.API_KEY
    )
    f = urllib2.urlopen(qurl)
    districts = json.load(f)
    district_id = None
    for district in districts:
        legs = [x['leg_id'] for x in district['legislators']]
        if legislator['leg_id'] in legs:
            district_id = district['boundary_id']
            break

    sponsored_bills = legislator.sponsored_bills(
        limit=5, sort=[('action_dates.first', pymongo.DESCENDING)])

    # Note to self: Another slow query
    legislator_votes = legislator.votes_5_sorted()
    has_votes = bool(legislator_votes)
    return render(request, templatename('legislator'),
        dict(
            feed_entry_template=templatename('feed_entry'),
            vote_preview_row_template=templatename('vote_preview_row'),
            roles=legislator.roles_manager,
            abbr=abbr,
            district_id=district_id,
            metadata=meta,
            legislator=legislator,
            sources=legislator['sources'],
            sponsored_bills=sponsored_bills,
            legislator_votes=legislator_votes,
            feed_entries=legislator.feed_entries().limit(5),
            has_votes=has_votes,
            statenav_active='legislators'))


def legislator_inactive(request, abbr, legislator):
    sponsored_bills = legislator.sponsored_bills(
        limit=5, sort=[('action_dates.first', pymongo.DESCENDING)])

    legislator_votes = legislator.votes_5_sorted()
    has_votes = bool(legislator_votes)

    return render(request, templatename('legislator_inactive'),
        dict(feed_entry_template=templatename('feed_entry'),
            vote_preview_row_template=templatename('vote_preview_row'),
            old_roles=legislator.old_roles_manager,
            abbr=abbr,
            metadata=legislator.metadata,
            legislator=legislator,
            sources=legislator['sources'],
            sponsored_bills=sponsored_bills,
            legislator_votes=legislator_votes,
            has_votes=has_votes,
            statenav_active='legislators'))
