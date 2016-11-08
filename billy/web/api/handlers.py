import re
import urllib2
import datetime
import json
import itertools
from collections import defaultdict

from django.http import HttpResponse

from billy.core import db, feeds_db
from billy.models import Bill
from billy.core import settings
from billy.utils import find_bill, parse_param_dt, fix_bill_id

import pymongo

from piston.utils import rc
from piston.handler import BaseHandler, HandlerMetaClass

AT_LARGE = ['At-Large', 'Chairman']
ACTIVE_BOUNDARY_SETS = settings.BOUNDARY_SERVICE_SETS.split(",")


_lower_fields = (settings.LEVEL_FIELD, 'chamber')


def _build_mongo_filter(request, keys, icase=True):
    _filter = {}
    keys = set(keys) - set(['fields'])

    for key in keys:
        value = request.GET.get(key)
        if value:
            if key in _lower_fields:
                _filter[key] = value.lower()
            elif key.endswith('__in'):
                values = value.split('|')
                _filter[key[:-4]] = values
            elif key == 'bill_id':
                _filter[key] = fix_bill_id(value.upper())
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
        d['_id'] = d.pop('id', 1)
        d['_type'] = 1
        return d


def _get_vote_fields(fields):
    return [field.replace('votes.', '', 1) for field in fields or [] if
            field.startswith('votes.')] or None


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
                    resp.write("cannot specify fields param if format=%s" % fmt)
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


def _metadata_backwards_shim(metadata):
    if 'chambers' in metadata:
        for chamber_type, chamber in metadata['chambers'].iteritems():
            for field in ('name', 'title', 'term'):
                if field in chamber:
                    metadata[chamber_type + '_chamber_' + field] = \
                        chamber[field]
    return metadata


class AllMetadataHandler(BillyHandler):
    def read(self, request):
        use_shim = bool(request.GET.get('fields'))
        fields = _build_field_list(request, {'abbreviation': 1,
                                             'name': 1,
                                             'feature_flags': 1,
                                             'chambers': 1,
                                             '_id': 0
                                            })
        for f in fields.copy():
            if '_chamber_' in f:
                use_shim = True
                fields['chambers'] = 1
        data = db.metadata.find(fields=fields).sort('name')
        if use_shim:
            return [_metadata_backwards_shim(m) for m in data]
        else:
            return list(data)


class MetadataHandler(BillyHandler):
    def read(self, request, abbr):
        use_shim = bool(request.GET.get('fields'))
        field_list = _build_field_list(request)
        if field_list:
            for f in field_list.copy():
                if '_chamber_' in f:
                    use_shim = True
                    field_list['chambers'] = 1
        data = db.metadata.find_one({'_id': abbr.lower()}, fields=field_list)
        if use_shim:
            return _metadata_backwards_shim(data)
        else:
            return data


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

        fields = _build_field_list(request)
        bill = find_bill(query, fields=fields)
        vote_fields = _get_vote_fields(fields)
        # include votes if no fields are specified, if it is specified, or
        # if subfields are specified
        if bill and (not fields or 'votes' in fields or vote_fields):
            bill['votes'] = list(db.votes.find({'bill_id': bill['_id']},
                                               fields=vote_fields))
        return bill


class BillSearchHandler(BillyHandler):
    def read(self, request):
        bill_fields = {'title': 1, 'created_at': 1, 'updated_at': 1,
                       'bill_id': 1, 'type': 1, settings.LEVEL_FIELD: 1,
                       'session': 1, 'chamber': 1, 'subjects': 1, '_type': 1,
                       'id': 1}
        # replace with request's fields if they exist
        bill_fields = _build_field_list(request, bill_fields)

        # normal mongo search logic
        base_fields = _build_mongo_filter(request, ('chamber', 'bill_id',
                                                    'bill_id__in'))

        # process extra attributes
        query = request.GET.get('q')
        abbr = request.GET.get(settings.LEVEL_FIELD)
        if abbr:
            abbr = abbr.lower()
        search_window = request.GET.get('search_window', 'all')
        since = request.GET.get('updated_since', None)
        last_action_since = request.GET.get('last_action_since', None)
        sponsor_id = request.GET.get('sponsor_id')
        subjects = request.GET.getlist('subject')
        type_ = request.GET.get('type')
        status = request.GET.getlist('status')

        # sorting
        sort = request.GET.get('sort', 'last')
        if sort == 'last_action':
            sort = 'last'

        try:
            query = Bill.search(query,
                                abbr=abbr,
                                search_window=search_window,
                                updated_since=since,
                                last_action_since=last_action_since,
                                sponsor_id=sponsor_id,
                                subjects=subjects, type_=type_, status=status,
                                sort=sort, bill_fields=bill_fields,
                                **base_fields)
        except ValueError as e:
            resp = rc.BAD_REQUEST
            resp.write('%s' % e)
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
            start = per_page * (page - 1)
            end = start + per_page
            bills = query[start:end]
        else:
            # limit response size
            if len(query) > 10000:
                resp = rc.BAD_REQUEST
                resp.write('request too large, try narrowing your search by '
                           'adding more filters.')
                return resp
            bills = query[:]

        bills = list(bills)
        # attach votes if necessary
        bill_ids = [bill['_id'] for bill in bills]
        vote_fields = _get_vote_fields(bill_fields) or []
        if 'votes' in bill_fields or vote_fields:
            # add bill_id to vote_fields for relating back
            votes = list(db.votes.find({'bill_id': {'$in': bill_ids}},
                                       fields=vote_fields + ['bill_id']))
            votes_by_bill = defaultdict(list)
            for vote in votes:
                votes_by_bill[vote['bill_id']].append(vote)
                # remove bill_id unless they really requested it
                if 'bill_id' not in vote_fields:
                    vote.pop('bill_id')
            for bill in bills:
                bill['votes'] = votes_by_bill[bill['_id']]

        return bills


class LegislatorHandler(BillyHandler):
    def read(self, request, id):
        return db.legislators.find_one({'_all_ids': id}, _build_field_list(request))


class LegislatorSearchHandler(BillyHandler):
    def read(self, request):
        legislator_fields = {'sources': 0, 'roles': 0, 'old_roles': 0}
        # replace with request's fields if they exist
        legislator_fields = _build_field_list(request, legislator_fields)

        _filter = _build_mongo_filter(request, (settings.LEVEL_FIELD, 'first_name', 'last_name',
                                                'full_name'))
        elemMatch = _build_mongo_filter(request, ('chamber', 'term', 'district', 'party'))
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
                                                'chamber',
                                                settings.LEVEL_FIELD))
        return list(db.committees.find(_filter, committee_fields))


class EventsHandler(BillyHandler):
    def read(self, request, id=None, events=[]):
        if events:
            return events

        if id:
            return db.events.find_one({'_id': id})

        spec = {}

        for key in (settings.LEVEL_FIELD, 'type'):
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
            resp.write("invalid updated_since parameter."
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
            spec['chamber'] = chamber.lower()
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
            resp.write('Need lat and long parameters')
            return resp

        url = "%sdivisions/?fields=id&lat=%s&lon=%s&apikey=%s" % (
            self.base_url, latitude, longitude, settings.API_KEY
        )

        resp = json.load(urllib2.urlopen(url, timeout=0.5))

        filters = []
        boundary_mapping = {}
        jurisdiction = None

        for dist in resp['results']:
            ocdid = dist['id']
            # ocd-division/country:us/state:oh/cd:11
            _, localpart = ocdid.rsplit("/", 1)
            set_, series = localpart.split(":", 1)
            if set_ not in ['sldl', 'sldu', 'ward']:
                # Place, CD, County, ...
                continue

            districts = db.districts.find({'division_id': ocdid})
            count = districts.count()

            if count == 1:
                district = districts[0]
                boundary_id = district['division_id']

                filters.append({'district': district['name'],
                                'chamber': district['chamber'],
                                settings.LEVEL_FIELD: district['abbr']})

                boundary_mapping[(district['abbr'],
                                  district['name'],
                                  district['chamber'])] = boundary_id

                jurisdiction = district['abbr']
            elif count != 0:
                raise ValueError('multiple districts with boundary_id: %s' %
                                 boundary_id)

        if not filters:
            return []

        if jurisdiction:
            # append at-large legislators from this jurisdiction
            filters.append({'district': {'$in': AT_LARGE},
                            settings.LEVEL_FIELD: jurisdiction})

        fields = _build_field_list(request)
        if fields is not None:
            fields['state'] = fields['district'] = fields['chamber'] = 1
        legislators = list(db.legislators.find({'$or': filters}, fields))
        for leg in legislators:
            if leg['district'] not in AT_LARGE:
                leg['boundary_id'] = boundary_mapping[(
                    leg[settings.LEVEL_FIELD], leg['district'], leg['chamber']
                )]
        return legislators


class DistrictHandler(BillyHandler):

    def read(self, request, abbr, chamber=None):
        filter = {'abbr': abbr}
        if not chamber:
            chamber = {'$exists': True}
        filter['chamber'] = chamber
        districts = list(db.districts.find(filter))

        # change leg filter
        filter[settings.LEVEL_FIELD] = filter.pop('abbr')
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

    def _ocd_id_to_shape_url(self, ocd_id):
        # url = "%sboundaries/%s/simple_shape" % (self.base_url, boundary_id)
        url = "{}{}?apikey={}".format(
            settings.BOUNDARY_SERVICE_URL,
            ocd_id,
            settings.API_KEY,
        )
        data = json.load(urllib2.urlopen(url, timeout=0.5))
        geometries = filter(
            lambda x: x['boundary_set']['name'] in ACTIVE_BOUNDARY_SETS,
            data['geometries']
        )
        if len(geometries) == 1:
            geom, = geometries
            return "{}{}".format(settings.BOUNDARY_SERVICE_URL,
                                 geom['related']['simple_shape_url'])
        return

    def read(self, request, boundary_id):
        try:
            url = self._ocd_id_to_shape_url(boundary_id)
            data = json.load(urllib2.urlopen(url, timeout=0.5))
        except urllib2.HTTPError as e:
            if e.code >= 400:
                resp = rc.NOT_FOUND
                return resp
            else:
                raise e

        all_lon = []
        all_lat = []
        for shape in data['coordinates']:
            for coord_set in shape:
                all_lon.extend(c[0] for c in coord_set)
                all_lat.extend(c[1] for c in coord_set)

        min_lat = min(all_lat)
        min_lon = min(all_lon)
        max_lat = max(all_lat)
        max_lon = max(all_lon)

        lon_delta = abs(max_lon - min_lon)
        lat_delta = abs(max_lat - min_lat)

        region = {'center_lon': (max_lon + min_lon) / 2,
                  'center_lat': (max_lat + min_lat) / 2,
                  'lon_delta': lon_delta, 'lat_delta': lat_delta,
                 }
        bbox = [[min_lat, min_lon], [max_lat, max_lon]]

        district = db.districts.find_one({'division_id': boundary_id})
        if not district:
            resp = rc.NOT_FOUND
            return resp

        district['shape'] = data['coordinates']
        district['region'] = region
        district['bbox'] = bbox

        return district


class NewsHandler(BillyHandler):

    def read(self, request, id):
        fields = ['entity_ids', 'entity_strings', 'link']
        entries = feeds_db.entries.find({'entity_ids': id}, fields=fields)
        return dict(count=entries.count(), entries=list(entries))
