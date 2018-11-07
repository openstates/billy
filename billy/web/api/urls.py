import datetime
from django.conf import settings
from django.conf.urls import url
from django.http import HttpResponse

import piston.resource
from piston.emitters import Emitter

from billy.web.api import handlers
from billy.web.api.emitters import BillyJSONEmitter


class CORSResource(piston.resource.Resource):
    def __call__(self, *args, **kwargs):
        r = super(CORSResource, self).__call__(*args, **kwargs)
        r['Access-Control-Allow-Origin'] = '*'
        return r


authorizer = None
Resource = CORSResource

Emitter.register('json', BillyJSONEmitter, 'application/json; charset=utf-8')
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
legislator_geo_handler = Resource(handlers.LegislatorGeoHandler,
                                  authentication=authorizer)
district_handler = Resource(handlers.DistrictHandler,
                            authentication=authorizer)
boundary_handler = Resource(handlers.BoundaryHandler,
                            authentication=authorizer)

urlpatterns = [
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

    # districts & boundaries
    url(r'v1/districts/(?P<abbr>[a-zA-Z-]+)/$',
        district_handler),
    url(r'v1/districts/(?P<abbr>[a-zA-Z-]+)/(?P<chamber>upper|lower)/$',
        district_handler),
    url(r'v1/districts/boundary/(?P<boundary_id>.+)/$', boundary_handler),
]
