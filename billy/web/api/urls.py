import datetime
from django.conf import settings
from django.conf.urls import patterns, url
from django.http import HttpResponse

import piston.resource
from piston.emitters import Emitter

from billy.web.api import handlers
from billy.web.api.emitters import BillyJSONEmitter
from billy.web.api.emitters import ICalendarEmitter


class CORSResource(piston.resource.Resource):
    def __call__(self, *args, **kwargs):
        r = super(CORSResource, self).__call__(*args, **kwargs)
        r['Access-Control-Allow-Origin'] = '*'
        return r


if getattr(settings, 'USE_LOCKSMITH', False):
    from locksmith.mongoauth.authentication import PistonKeyAuthentication
    from locksmith.mongoauth.db import db

    class Authorizer(PistonKeyAuthentication):
        def challenge(self, *args):
            response = 'Authorization Required'
            locksmith_url = getattr(settings, 'LOCKSMITH_REGISTRATION_URL',
                                    None)
            if locksmith_url:
                response = '{0}:\n obtain a key at {1}'.format(response,
                                                               locksmith_url)
            resp = HttpResponse(response)
            resp.status_code = 401
            return resp

    authorizer = Authorizer()

    class Resource(CORSResource):
        def __call__(self, request, *args, **kwargs):
            resp = super(Resource, self).__call__(request, *args, **kwargs)

            try:
                db.logs.insert({'key': request.apikey['_id'],
                                'method': self.handler.__class__.__name__,
                                'query_string': request.META['QUERY_STRING'],
                                'timestamp': datetime.datetime.utcnow()})
            except AttributeError:
                pass

            return resp
else:
    authorizer = None
    Resource = CORSResource

Emitter.register('json', BillyJSONEmitter, 'application/json; charset=utf-8')

Emitter.register('ics', ICalendarEmitter, 'text/calendar')

Emitter.unregister('yaml')
Emitter.unregister('xml')
Emitter.unregister('django')
Emitter.unregister('pickle')

all_metadata_handler = Resource(handlers.AllMetadataHandler,
                                authentication=authorizer)
metadata_handler = Resource(handlers.MetadataHandler,
                            authentication=authorizer)
bill_handler = Resource(handlers.BillHandler,
                        authentication=authorizer)
bill_search_handler = Resource(handlers.BillSearchHandler,
                               authentication=authorizer)
legislator_handler = Resource(handlers.LegislatorHandler,
                              authentication=authorizer)
legsearch_handler = Resource(handlers.LegislatorSearchHandler,
                             authentication=authorizer)
committee_handler = Resource(handlers.CommitteeHandler,
                             authentication=authorizer)
committee_search_handler = Resource(handlers.CommitteeSearchHandler,
                                    authentication=authorizer)
events_handler = Resource(handlers.EventsHandler,
                          authentication=authorizer)
subject_list_handler = Resource(handlers.SubjectListHandler,
                                authentication=authorizer)
legislator_geo_handler = Resource(handlers.LegislatorGeoHandler,
                                  authentication=authorizer)
district_handler = Resource(handlers.DistrictHandler,
                            authentication=authorizer)
boundary_handler = Resource(handlers.BoundaryHandler,
                            authentication=authorizer)
news_handler = Resource(handlers.NewsHandler,
                        authentication=authorizer)

urlpatterns = patterns(
    '',
    # metadata
    url(r'^v1/metadata/$', all_metadata_handler),
    url(r'^v1/metadata/(?P<abbr>[a-zA-Z-]+)/$', metadata_handler),

    # bills, including three urls for bill handler
    url(r'^v1/bills/(?P<abbr>[a-zA-Z-]+)/(?P<session>.+)/'
        r'(?P<chamber>upper|lower)/(?P<bill_id>.+)/$', bill_handler),
    url(r'^v1/bills/(?P<abbr>[a-zA-Z-]+)/(?P<session>.+)/'
        r'(?P<bill_id>.+)/$', bill_handler),
    url(r'^v1/bills/(?P<billy_bill_id>[A-Z-]+B\d{8})/', bill_handler),
    url(r'^v1/bills/$', bill_search_handler),

    url(r'^v1/legislators/(?P<id>[A-Z-]+L\d{6})/$', legislator_handler),
    url(r'^v1/legislators/$', legsearch_handler),
    url(r'v1/legislators/geo/$', legislator_geo_handler),

    url(r'^v1/committees/(?P<id>[A-Z-]+C\d{6})/$', committee_handler),
    url(r'^v1/committees/$', committee_search_handler),

    url(r'^v1/events/$', events_handler),
    url(r'^v1/events/(?P<id>[A-Z-]+E\d{8})/$', events_handler),

    # districts & boundaries
    url(r'v1/districts/(?P<abbr>[a-zA-Z-]+)/$',
        district_handler),
    url(r'v1/districts/(?P<abbr>[a-zA-Z-]+)/(?P<chamber>upper|lower)/$',
        district_handler),
    url(r'v1/districts/boundary/(?P<boundary_id>.+)/$', boundary_handler),

    # experimental - undocumented methods
    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z-]+)/(?P<session>.+)/'
        '(?P<chamber>upper|lower)/', subject_list_handler),
    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z-]+)/(?P<session>.+)/',
        subject_list_handler),
    url(r'v1/subject_counts/(?P<abbr>[a-zA-Z-]+)/', subject_list_handler),

    url(r'^v1/news/(?P<id>[A-Z]{3}\d{,10})/$', news_handler),
)
