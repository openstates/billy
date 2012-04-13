from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('billy.web.admin.views',
    url(r'^$', 'browse_index', name='admin_index'),

    # admin overview pages
    url(r'^(?P<abbr>[a-z]{2})/$', 'overview', name='admin_overview'),
    url(r'^(?P<abbr>[a-z]{2})/metadata$', 'metadata_json', name='metadata_json'),
    url(r'^(?P<abbr>[a-z]{2})/bills/$', 'bills', name='admin_bills'),
    url(r'^(?P<abbr>[a-z]{2})/legislators/$', 'legislators',
        name='admin_legislators'),
    url(r'^(?P<abbr>[a-z]{2})/committees/$', 'committees',
        name='admin_committees'),
    url(r'^legislators/(?P<id>.*)/$', 'legislator', name='legislator'),
    url(r'^(?P<abbr>[a-z]{2})/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='bill'),
    url(r'^(?P<abbr>[a-z]{2})/random_bill/$', 'random_bill',
        name='random_bill'),
    url(r'^(?P<abbr>[a-z]{2})/bill_list/$', 'bill_list', name='bill_list'),


    # missing data
    url(r'^(?P<abbr>[a-z]{2})/uncategorized_subjects/$',
        'uncategorized_subjects', name='uncategorized_subjects'),
    url(r'^(?P<abbr>[a-z]{2})/other_actions/$', 'other_actions',
        name='other_actions'),
    url(r'^(?P<abbr>[a-z]{2})/unmatched_leg_ids/$', 'unmatched_leg_ids',
        name='unmatched_leg_ids'),
    url(r'^(?P<abbr>[a-z]{2})/district_stub/$', 'district_stub',
        name='district_stub'),
    url(r'^(?P<abbr>[a-z]{2})/duplicate_versions/$', 'duplicate_versions',
        name='duplicate_versions'),

    # Summary urls.
    url(r'^(?P<abbr>[a-z]{2})/summary/$', 'summary_index'),
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key/$', 'summary_object_key'),
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key_vals/$',
        'summary_object_key_vals'),
    url(r'^object_json/(?P<collection>.{,100})/(?P<_id>.{,100})/',
        'object_json', name='object_json'),

    # runlog URLs.
    url(r'^state-run-detail/(?P<abbr>[a-z]{2})/$', 'state_run_detail', name="state_run_detail"),
    url(r'^run-detail/(?P<obj>.*)/$', 'run_detail', name="run_detail"),
    url(r'^run-detail-data/(?P<abbr>[a-z]{2})/$','run_detail_graph_data',
        name="run_detail-data"),

    # Merge-o-matic URLs.
    url(r'^mom/$', 'mom_index', name="mom_index" ),
    url(r'^mom/merge/$', 'mom_merge', name="mom_merge" ),
    url(r'^mom/commit/$', 'mom_commit', name="mom_commit" )
)
