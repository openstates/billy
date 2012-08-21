import re
import urllib2
import datetime
import json
import itertools
from collections import defaultdict

from django.http import HttpResponse

from billy import db
from billy.models import Bill
from billy.conf import settings
from billy.utils import find_bill, parse_param_dt

import pymongo

from piston.utils import rc
from piston.handler import BaseHandler, HandlerMetaClass


_chamber_aliases = {
    'assembly': 'lower',
    'house': 'lower',
    'senate': 'upper',
}


_lower_fields = ('state',)


def _build_mongo_filter(request, keys, icase=True):
    _filter = {}
    keys = set(keys) - set(['fields'])

    try:
        keys.remove('subjects')
        if 'subject' in request.GET:
            _filter['subjects'] = {'$all': request.GET.getlist('subject')}
    except KeyError:
        pass

    for key in keys:
        value = request.GET.get(key)
        if value:
            if key == 'chamber':
                value = value.lower()
                _filter[key] = _chamber_aliases.get(value, value)
            elif key in _lower_fields:
                _filter[key] = value.lower()
            elif key.endswith('__in'):
                values = value.split('|')
                _filter[key[:-4]] = {'$in': values}
            else:
                # We use regex queries to get case insensitive search - this
                # means they won't use any indexes for now. Real case
                # insensitive queries are coming eventually:
                # http://jira.mongodb.org/browse/SERVER-90
                _filter[key] = re.compile('^%s$' % value, re.IGNORECASE)

    return _filter


def _build_field_list(request, default_fields=None):
    # if 'fields' key is specified in request split it on comma
    # and use only those fields instead of default_fields
    fields = request.GET.get('fields')

    if not fields:
        return default_fields
    else:
        d = dict(zip(fields.split(','), itertools.repeat(1)))
        d['_id'] = d.pop('id', 0)
        d['_type'] = 1
        return d


class BillyHandlerMetaClass(HandlerMetaClass):
    """
    Returns 404 if Handler result is None.
    """
    def __new__(cls, name, bases, attrs):
        new_cls = super(BillyHandlerMetaClass, cls).__new__(
            cls, name, bases, attrs)

        if hasattr(new_cls, 'read'):
            old_read = new_cls.read

            def new_read(*args, **kwargs):
                request = args[1]
                fmt = request.GET.get('format')
                if fmt == 'ics' and 'fields' in request.GET:
                    resp = rc.BAD_REQUEST
                    resp.write(": cannot specify fields param if format=%s" %
                               fmt)
                    return resp
                obj = old_read(*args, **kwargs)
                if isinstance(obj, HttpResponse):
                    return obj

                if obj is None:
                    return rc.NOT_FOUND

                return obj

            new_cls.read = new_read

        return new_cls


class BillyHandler(BaseHandler):
    """
    Base handler for the Billy API.
    """
    __metaclass__ = BillyHandlerMetaClass
    allowed_methods = ('GET',)


class AllMetadataHandler(BillyHandler):
    def read(self, request):
        fields = _build_field_list(request, {'abbreviation': 1,
                                             'name': 1,
                                             'feature_flags': 1,
                                             '_id': 0
                                            })
        data = db.metadata.find(fields=fields).sort('name')
        return list(data)


class MetadataHandler(BillyHandler):
    def read(self, request, abbr):
        """
        Get metadata about a legislature.
        """
        return db.metadata.find_one({'_id': abbr.lower()},
                                    fields=_build_field_list(request))


class BillHandler(BillyHandler):
    def read(self, request, abbr=None, session=None, bill_id=None,
             chamber=None, billy_bill_id=None):
        if billy_bill_id:
            query = {'_id': billy_bill_id}
        else:
            abbr = abbr.lower()
            query = {settings.LEVEL_FIELD: abbr, 'session': session,
                     'bill_id': bill_id}
            if chamber:
                query['chamber'] = chamber.lower()
        return find_bill(query, fields=_build_field_list(request))


class BillSearchHandler(BillyHandler):
    def read(self, request):

        bill_fields = {'title': 1, 'created_at': 1, 'updated_at': 1,
                       'bill_id': 1, 'type': 1, settings.LEVEL_FIELD: 1,
                       'session': 1, 'chamber': 1, 'subjects': 1, '_type': 1,
                       'id': 1}
        # replace with request's fields if they exist
        bill_fields = _build_field_list(request, bill_fields)

        # normal mongo search logic
        base_fields = _build_mongo_filter(request, ('state', 'chamber',
                                                    'subjects', 'bill_id',
                                                    'bill_id__in'))

        # process extra attributes
        query = request.GET.get('q')
        search_window = request.GET.get('search_window', 'all')
        since = request.GET.get('updated_since', None)
        sponsor_id = request.GET.get('sponsor_id')

        try:
            query = Bill.search(query,
                                search_window=search_window,
                                updated_since=since, sponsor_id=sponsor_id,
                                bill_fields=bill_fields,
                                **base_fields)
        except ValueError as e:
            resp = rc.BAD_REQUEST
            resp.write(': %s' % e)
            return resp

        # add pagination
        page = request.GET.get('page')
        per_page = request.GET.get('per_page')
        if page and not per_page:
            per_page = 50
        if per_page and not page:
            page = 1

        if page:
            page = int(page)
            per_page = int(per_page)
            query = query.limit(per_page).skip(per_page * (page - 1))
        else:
            # limit response size
            if query.count() > 10000:
                resp = rc.BAD_REQUEST
                resp.write(': request too large, try narrowing your search by '
                           'adding more filters.')
                return resp

        # sorting
        sort = request.GET.get('sort')
        if sort == 'updated_at':
            query = query.sort([('updated_at', -1)])
        elif sort == 'created_at':
            query = query.sort([('created_at', -1)])
        elif sort == 'last_action':
            query = query.sort([('action_dates.last', -1)])

        return list(query)


class LegislatorHandler(BillyHandler):
    def read(self, request, id):
        return db.legislators.find_one({'_all_ids': id},
                                       _build_field_list(request))


class LegislatorSearchHandler(BillyHandler):
    def read(self, request):
        legislator_fields = {'sources': 0, 'roles': 0, 'old_roles': 0}
        # replace with request's fields if they exist
        legislator_fields = _build_field_list(request, legislator_fields)

        _filter = _build_mongo_filter(request, ('state', 'first_name',
                                                'last_name'))
        elemMatch = _build_mongo_filter(request, ('chamber', 'term',
                                                  'district', 'party'))
        if elemMatch:
            _filter['roles'] = {'$elemMatch': elemMatch}

        active = request.GET.get('active')
        if not active and 'term' not in request.GET:
            # Default to only searching active legislators if no term
            # is supplied
            _filter['active'] = True
        elif active and active.lower() == 'true':
            _filter['active'] = True

        return list(db.legislators.find(_filter, legislator_fields))


class CommitteeHandler(BillyHandler):
    def read(self, request, id):
        return db.committees.find_one({'_all_ids': id},
                                      _build_field_list(request))


class CommitteeSearchHandler(BillyHandler):
    def read(self, request):
        committee_fields = {'members': 0, 'sources': 0}
        # replace with request's fields if they exist
        committee_fields = _build_field_list(request, committee_fields)

        _filter = _build_mongo_filter(request, ('committee', 'subcommittee',
                                                'chamber', 'state'))
        return list(db.committees.find(_filter, committee_fields))


class EventsHandler(BillyHandler):
    def read(self, request, id=None, events=[]):
        if events:
            return events

        if id:
            return db.events.find_one({'_id': id})

        spec = {}

        for key in ('state', 'type'):
            value = request.GET.get(key)
            if not value:
                continue

            split = value.split(',')

            if len(split) == 1:
                spec[key] = value
            else:
                spec[key] = {'$in': split}

        invalid_date = False

        if 'dtstart' in request.GET:
            try:
                spec['when'] = {'$gte': parse_param_dt(request.GET['dtstart'])}
            except ValueError:
                invalid_date = True
        else:
            # By default, go back 7 days
            now = datetime.datetime.now()
            before = now - datetime.timedelta(7)
            spec['when'] = {'$gte': before}

        if 'dtend' in request.GET:
            try:
                spec['when']['$lte'] = parse_param_dt(request.GET['dtend'])
            except ValueError:
                invalid_date = True

        if invalid_date:
            resp = rc.BAD_REQUEST
            resp.write(": invalid updated_since parameter."
                       " Please supply a date in YYYY-MM-DD format.")
            return resp

        return list(db.events.find(spec, fields=_build_field_list(request)
                                  ).sort('when', pymongo.ASCENDING).limit(1000)
                   )


class SubjectListHandler(BillyHandler):
    def read(self, request, abbr, session=None, chamber=None):
        abbr = abbr.lower()
        spec = {settings.LEVEL_FIELD: abbr}
        if session:
            spec['session'] = session
        if chamber:
            chamber = chamber.lower()
            spec['chamber'] = _chamber_aliases.get(chamber, chamber)
        result = {}
        for subject in settings.BILLY_SUBJECTS:
            count = db.bills.find(dict(spec, subjects=subject)).count()
            result[subject] = count
        return result


class LegislatorGeoHandler(BillyHandler):
    base_url = settings.BOUNDARY_SERVICE_URL

    def read(self, request):
        latitude, longitude = request.GET.get('lat'), request.GET.get('long')

        if not latitude or not longitude:
            resp = rc.BAD_REQUEST
            resp.write(': Need lat and long parameters')
            return resp

        url = ("%sboundary/?shape_type=none&contains=%s,%s&sets=sldl,sldu"
               "&limit=0" % (self.base_url, latitude, longitude))

        resp = json.load(urllib2.urlopen(url))

        filters = []
        boundary_mapping = {}

        for dist in resp['objects']:
            state = dist['name'][0:2].lower()
            chamber = {'/1.0/boundary-set/sldu/': 'upper',
                       '/1.0/boundary-set/sldl/': 'lower'}[dist['set']]
            census_name = dist['slug']

            # look up district slug
            districts = db.districts.find({'chamber': chamber,
                                           'boundary_id': census_name})
            count = districts.count()
            if count:
                filters.append({'state': state,
                                'district': districts[0]['name'],
                                'chamber': chamber})
                boundary_mapping[(state, districts[0]['name'],
                                  chamber)] = census_name

        if not filters:
            return []

        legislators = list(db.legislators.find({'$or': filters},
                                               _build_field_list(request)))
        for leg in legislators:
            leg['boundary_id'] = boundary_mapping[(leg['state'],
                                                   leg['district'],
                                                   leg['chamber'])]
        return legislators


class DistrictHandler(BillyHandler):

    def read(self, request, abbr, chamber=None):
        filter = {'abbr': abbr}
        if not chamber:
            chamber = {'$exists': True}
        filter['chamber'] = chamber
        districts = list(db.districts.find(filter))

        # change leg filter
        filter['state'] = filter.pop('abbr')
        filter['active'] = True
        legislators = db.legislators.find(filter, fields={'_id': 0,
                                                          'leg_id': 1,
                                                          'chamber': 1,
                                                          'district': 1,
                                                          'full_name': 1})

        leg_dict = defaultdict(list)
        for leg in legislators:
            leg_dict[(leg['chamber'], leg['district'])].append(leg)
            leg.pop('chamber')
            leg.pop('district')
        for dist in districts:
            dist['legislators'] = leg_dict[(dist['chamber'], dist['name'])]

        return districts


class BoundaryHandler(BillyHandler):
    base_url = settings.BOUNDARY_SERVICE_URL

    def read(self, request, boundary_id):
        url = "%sboundary/%s/?shape_type=simple" % (self.base_url, boundary_id)
        try:
            data = json.load(urllib2.urlopen(url))
        except urllib2.HTTPError, e:
            if 400 <= e.code < 500:
                resp = rc.NOT_FOUND
                return resp
            else:
                raise e

        centroid = data['centroid']['coordinates']

        all_lon = []
        all_lat = []
        for shape in data['simple_shape']['coordinates']:
            for coord_set in shape:
                all_lon.extend(c[0] for c in coord_set)
                all_lat.extend(c[1] for c in coord_set)
        lon_delta = abs(max(all_lon) - min(all_lon))
        lat_delta = abs(max(all_lat) - min(all_lat))

        region = {'center_lon': centroid[0], 'center_lat': centroid[1],
                  'lon_delta': lon_delta, 'lat_delta': lat_delta,
                 }

        district = db.districts.find_one({'boundary_id': boundary_id})
        district['shape'] = data['simple_shape']['coordinates']
        district['region'] = region

        return district
