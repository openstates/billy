from django.conf.urls.defaults import *

urlpatterns = patterns('billy.site.browse.views',
    url(r'^$', 'browse_index'),
    url(r'^(?P<abbr>[a-z]{2})/$', 'overview'),
    url(r'^(?P<abbr>[a-z]{2})/bills/$', 'bills'),
    url(r'^(?P<abbr>[a-z]{2})/uncategorized_subjects/$', 'uncategorized_subjects'),
    url(r'^(?P<abbr>[a-z]{2})/other_actions/$', 'other_actions'),
    url(r'^(?P<abbr>[a-z]{2})/unmatched_leg_ids/$', 'unmatched_leg_ids'),
    url(r'^(?P<abbr>[a-z]{2})/random_bill/$', 'random_bill'),
    url(r'^(?P<abbr>[a-z]{2})/(?P<session>.+)/(?P<id>.*)/json/$', 'bill_json', name='bill_json'),                       
    url(r'^(?P<abbr>[a-z]{2})/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='bill'),

    # Summary urls.
    url(r'^(?P<abbr>[a-z]{2})/summary$', 'summary_index'),                       
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key$', 'summary_object_key'),
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key_vals$', 'summary_object_key_vals'),
    url(r'^object_json/(?P<collection>.{,100})/(?P<_id>.{,100})/', 'object_json'),                   
                       
    url(r'^(?P<abbr>[a-z]{2})/legislators/$', 'legislators'),
    url(r'^(?P<abbr>[a-z]{2})/committees/$', 'committees'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator'),
)
