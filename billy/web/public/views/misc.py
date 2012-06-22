"""
    views that are not state/object specific
"""
import json
import random
import urllib2

import pymongo

from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse

from billy.models import db, Metadata, Legislator
from billy.models.pagination import CursorPaginator
from billy.conf import settings as billy_settings
from .utils import templatename, RelatedObjectsList


def homepage(request):
    return render(request, templatename('homepage'),
                  dict(
              active_states=map(Metadata.get_object, settings.ACTIVE_STATES)))


def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x: x['name'])
    return render(request, 'billy/web/public/downloads.html',
                  {'states': states})


def find_your_legislator(request):
    # check if lat/lon are set
    # if leg_search is set, they most likely don't have ECMAScript enabled.
    # XXX: fallback behavior here for alpha.

    get = request.GET
    context = {}
    template = 'find_your_legislator'

    addrs = [
        "50 Rice Street, Wellesley, MA",
        "20700 North Park Blvd. University Heights, Ohio",
        "1818 N Street NW, Washington, DC"
    ]

    context['address'] = random.choice(addrs)

    context['request'] = ""
    if "q" in get:
        context['request'] = get['q']

    if "lat" in get and "lon" in get:
        # We've got a passed lat/lon. Let's build off it.
        lat = get['lat']
        lon = get['lon']

        context['lat'] = lat
        context['lon'] = lon
        context['located'] = True

        qurl = "%slegislators/geo/?long=%s&lat=%s&apikey=%s" % (
            billy_settings.API_BASE_URL,
            lon,
            lat,
            billy_settings.SUNLIGHT_API_KEY
        )
        f = urllib2.urlopen(qurl)

        if "boundary" in get:
            legs = json.load(f)
            to_search = []
            for leg in legs:
                to_search.append(leg['boundary_id'])
            borders = set(to_search)
            ret = {}
            for border in borders:
                qurl = "%sdistricts/boundary/%s/?apikey=%s" % (
                    billy_settings.API_BASE_URL,
                    border,
                    billy_settings.SUNLIGHT_API_KEY
                )
                f = urllib2.urlopen(qurl)
                resp = json.load(f)
                ret[border] = resp
            return HttpResponse(json.dumps(ret))

        context['legislators'] = map(Legislator, json.load(f))
        template = 'find_your_legislator_table'

    return render(request, templatename(template), context)


def get_district(request, district_id):
    qurl = "%sdistricts/boundary/%s/?apikey=%s" % (
        billy_settings.API_BASE_URL,
        district_id,
        billy_settings.SUNLIGHT_API_KEY
    )
    f = urllib2.urlopen(qurl)
    return HttpResponse(f)


### Votes & News don't really fit here or anywhere


class VotesList(RelatedObjectsList):

    list_item_context_name = 'vote'
    mongo_sort = [('date', pymongo.DESCENDING)]
    paginator = CursorPaginator
    query_attr = 'votes_manager'
    use_table = True
    rowtemplate_name = templatename('votes_list_row')
    column_headers = ('Bill', 'Date', 'Outcome', 'Yes',
                      'No', 'Other', 'Motion')
    statenav_active = 'bills'
    description_template = templatename('list_descriptions/votes')


class NewsList(RelatedObjectsList):

    list_item_context_name = 'entry'
    mongo_sort = [('published_parsed', pymongo.DESCENDING)]
    paginator = CursorPaginator
    query_attr = 'feed_entries'
    rowtemplate_name = templatename('feed_entry')
    column_headers = ('feeds',)
    statenav_active = 'bills'
    description_template = templatename('list_descriptions/news')
