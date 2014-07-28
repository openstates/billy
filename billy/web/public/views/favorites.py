import datetime
import collections
from itertools import groupby
from operator import itemgetter
from urlparse import parse_qs
from StringIO import StringIO

import unicodecsv

from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.template.defaultfilters import truncatewords

from billy.core import user_db, mdb, settings
import billy.utils
from .utils import templatename


class Favorites(dict):
    '''This class wraps the favorites dict and provides convenience
    methods.
    '''

    def favorites_exist(self, type_):
        if type_ not in self:
            return False
        for obj in self[type_]:
            if obj['is_favorite']:
                return True
        return False

    def has_bills(self):
        return self.favorites_exist('bill')

    def has_legislators(self):
        return self.favorites_exist('legislator')

    def has_committees(self):
        return self.favorites_exist('committee')

    def has_searches(self):
        return self.favorites_exist('search')

    def legislator_objects(self):
        return [obj['obj'] for obj in self.get('legislator', [])]

    def committee_objects(self):
        deleted = dict(has_been_deleted=True)
        objs = [obj.get('obj', deleted) for obj in self.get('committee', [])]
        return objs


class FavoritedSearch(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.params = parse_qs(self['search_params'])
        if 'search_text' in self.params:
            self.text = self.params.pop('search_text').pop()
        else:
            self.text = None

    def scope(self):
        '''Return a comma-separated list of human readable equivalents
        for things passed in the query string: California, Session 1...
        '''
        params = self.params
        results = []
        meta = None
        abbr = self['search_abbr']

        if 'search_abbr' in self:
            if abbr == 'all':
                results.append('All states')
            else:
                meta = billy.utils.metadata(abbr)
                results.append(meta['name'])

        if 'session' in params:
            if meta:
                session = params['session'][0]
                session_details = meta['session_details']
                results.append(session_details[session]['display_name'])

        if 'chamber' in params:
            if meta:
                results.append(params['chamber'][0] + ' chamber')

        if 'type' in params:
            results.append('%ss only' % params['type'][0].title())

        if 'sponsor__leg_id' in params:
            # Get the legislator.
            leg = mdb.legislators.find_one(params['sponsor__leg_id'][0])
            tmpl = 'Sponsored by <a href="%s">%s</a>'
            vals = (leg.get_absolute_url(), leg.display_name())
            results.append(tmpl % vals)

        if 'subjects' in params:
            results.append('relating to %s' % ', '.join(params['subjects']))

        return ', '.join(results)


def _get_favorite_object(favorite):
    collection_name = {
        'bill': 'bills',
        'committee': 'committees',
        'legislator': 'legislators',
    }.get(favorite['obj_type'])
    if collection_name is not None:
        return getattr(mdb, collection_name).find_one(favorite['obj_id'])


def get_user_favorites(username):
    faves = list(user_db.favorites.find(dict(username=username)))
    grouped = groupby(faves, itemgetter('obj_type'))

    res = collections.defaultdict(list)
    for (key, iterator) in grouped:
        for fave in iterator:
            # Skip non-faves.
            if fave['is_favorite']:
                res[key].append(fave)

    for key in res:
        for fave in res[key]:
            obj = _get_favorite_object(fave)
            if obj is not None:
                fave['obj'] = obj

    # Wrap search results in helper object.
    if 'search' in res:
        res['search'] = map(FavoritedSearch, res['search'])

    return Favorites(res)


def is_favorite(obj_id, obj_type, user, extra_spec=None):
    '''Query database; return true or false.
    '''
    spec = dict(obj_id=obj_id, obj_type=obj_type, username=user.username)

    # Enable the bill search to pass in search terms.
    if extra_spec is not None:
        spec.update(extra_spec)

    if obj_type == 'search':
        # Records with type 'search' have no obj_id.
        del spec['obj_id']

    doc = user_db.favorites.find_one(spec)

    if doc:
        return doc['is_favorite']

    return False


########## views ##########


@login_required
def favorites(request):
    favorites = get_user_favorites(request.user.username)
    profile = user_db.profiles.find_one(request.user.username)
    return render(request, templatename('user_favorites'),
                  dict(favorites=favorites,
                       profile=profile,
                       legislators=favorites.legislator_objects(),
                       committees=favorites.committee_objects()))


@login_required
@require_http_methods(["POST"])
def set_favorite(request):
    '''Follow/unfollow a bill, committee, legislator.
    '''
    # Complain about bogus requests.
    resp400 = HttpResponse(status=400)
    valid_keys = set(['obj_id', 'obj_type', 'is_favorite',
                      'search_params', 'search_abbr'])
    if not set(request.POST) <= valid_keys:
        return resp400
    valid_types = ['bill', 'legislator', 'committee', 'search']
    if request.POST['obj_type'] not in valid_types:
        return resp400

    # Create the spec.
    spec = dict(
        obj_type=request.POST['obj_type'],
        obj_id=request.POST['obj_id'],
        username=request.user.username
    )

    if request.POST['obj_type'] == 'search':
        # Add the search text into the spec.
        spec.update(search_params=request.POST['search_params'])
        # 'search' docs have no obj_id.
        del spec['obj_id']
        spec.update(search_abbr=request.POST['search_abbr'])

    # Toggle the value of is_favorite.
    if request.POST['is_favorite'] == 'false':
        is_favorite = False
    if request.POST['is_favorite'] == 'true':
        is_favorite = True
    is_favorite = not is_favorite

    # Create the doc.
    doc = dict(
        is_favorite=is_favorite,
        timestamp=datetime.datetime.utcnow(),
    )
    doc.update(spec)
    # Create the doc if missing, else update based on the spec.
    user_db.favorites.update(spec, doc, upsert=True)
    return HttpResponse(content='{}', status=200)


@login_required
@require_http_methods(["POST"])
def set_notification_preference(request):
    '''Turn notification preferences on or off.
    '''
    resp400 = HttpResponse(status=400)

    # Get the obj_type
    obj_type = request.POST.get('obj_type')
    valid_types = ['bill', 'legislator', 'committee', 'search']
    if obj_type not in valid_types:
        return resp400

    # Get the alerts on/off.
    alerts_on = request.POST.get('on_off') == 'on'

    obj_type = 'notifications.' + obj_type

    user_db.profiles.update({'_id': request.user.username},
                            {'$set': {obj_type: alerts_on}}, upsert=True)
    return HttpResponse(status=200)


def favorite_bills_csv(request):
    '''Generate a csv of the user's favorited bills.
    '''
    # Get the faves.
    favorites = get_user_favorites(request.user.username)

    # Create a csv resposne.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="favorite_bills.csv"'

    # Start a CSV writer.
    fields = (settings.LEVEL_FIELD.title(), 'Bill Id', 'Sponsor', 'Title',
             'Session', 'Recent Action Date', 'Recent Action', 'Other Sponsors')
    writer = unicodecsv.DictWriter(response, fields, encoding='utf-8')
    writer.writeheader()

    # Write in each bill.
    for bill in favorites['bill']:
        bill = mdb.bills.find_one(bill['obj_id'])
        sponsors = (sp['name'] for sp in bill.sponsors_manager)

        row = (
            bill.metadata.get('name', ''),
            bill.get('bill_id', ''),
            next(sponsors, ''),
            truncatewords(bill['title'], 25),
            bill.session_details().get('display_name', ''),
            bill.most_recent_action().get('date', ''),
            bill.most_recent_action().get('action', ''),
            truncatewords(', '.join(sponsors), 40))

        writer.writerow(dict(zip(fields, row)))
    return response
