from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('billy.web.admin.views',
    url(r'^$', 'browse_index', name='admin_index'),

    # Quality exceptions (need to be above loose-matching bill view rule)
    url(r'^(?P<abbr>[a-z]{2})/exceptions/$', 'quality_exceptions',
        name='quality_exceptions'),
    url(r'^(?P<abbr>[a-z]{2})/add_exception/$', 'quality_exception_commit',
        name='quality_exception_commit'),
    url(r'^(?P<abbr>[a-z]{2})/remove_exception/(?P<obj>.+)/$',
        'quality_exception_remove', name='quality_exception_remove'),

    # Subject stuff
    url(r'^(?P<abbr>[a-z]{2})/subjects/$', 'subjects',
        name='admin_subjects'),
    url(r'^(?P<abbr>[a-z]{2})/subjects-commit/$', 'subjects_commit',
        name='admin_subjects_commit'),
    url(r'^(?P<abbr>[a-z]{2})/subjects-remove/(?P<id>.+)/$', 'subjects_remove',
        name='admin_subjects_remove'),

    # Leg ID stuff
    url(r'^(?P<abbr>[a-z]{2})/leg_ids/$', 'leg_ids',
        name='admin_leg_ids'),
    url(r'^(?P<abbr>[a-z]{2})/leg_ids-commit/$', 'leg_ids_commit',
        name='admin_leg_ids_commit'),
    url(r'^(?P<abbr>[a-z]{2})/leg_ids-remove/(?P<id>.+)/$', 'leg_ids_remove',
        name='admin_leg_ids_remove'),


    # admin overview pages
    url(r'^(?P<abbr>[a-z]{2})/$', 'overview', name='admin_overview'),
    url(r'^(?P<abbr>[a-z]{2})/metadata/$', 'metadata_json',
        name='metadata_json'),

    # committees
    url(r'^(?P<abbr>[a-z]{2})/committees/$', 'committees',
        name='admin_committees'),
    url(r'^delete_committees/$', 'delete_committees',
        name='delete_committees'),

    # legislator list
    url(r'^(?P<abbr>[a-z]{2})/legislators/$', 'legislators',
        name='admin_legislators'),
    url(r'^legislators/(?P<id>\w+)/$', 'legislator', name='admin_legislator'),
    url(r'^legislators/(?P<id>\w+)/retire/$', 'retire_legislator',
        name='retire_legislator'),

    # Edit stuff
    url(r'^legislators-edit/(?P<id>\w+)/$', 'legislator_edit',
            name='admin_legislator_edit'),
    url(r'^legislators-edit-commit/$', 'legislator_edit_commit',
            name='admin_legislator_edit_commit'),


    # bills
    url(r'^(?P<abbr>[a-z]{2})/bills/$', 'bills', name='admin_bills'),
    url(r'^(?P<abbr>[a-z]{2})/bills/random/$', 'random_bill',
        name='random_bill'),
    url(r'^(?P<abbr>[a-z]{2})/bills/list/$', 'bill_list', name='bill_list'),
    url(r'^(?P<abbr>[a-z]{2})/bills/(?P<billy_id>\w+)/$', 'bill',
        name='admin_bill_by_id'),
    url(r'^(?P<abbr>[a-z]{2})/bills/(?P<session>.+)/(?P<id>.*)/$', 'bill',
        name='admin_bill'),

    url(r'^(?P<abbr>[a-z]{2})/bad_vote_list/$', 'bad_vote_list',
        name='bad_vote_list'),
    url(r'^(?P<abbr>[a-z]{2})/events/$', 'events', name='admin_events'),
    url(r'^(?P<abbr>[a-z]{2})/event/(?P<event_id>.*)/$', 'event',
        name='admin_event'),

    # missing data
    url(r'^(?P<abbr>[a-z]{2})/other_actions/$', 'other_actions',
        name='other_actions'),
    url(r'^(?P<abbr>[a-z]{2})/duplicate_versions/$', 'duplicate_versions',
        name='duplicate_versions'),

    # Summary urls.
    url(r'^(?P<abbr>[a-z]{2})/summary/(?P<session>[^/]+)$', 'summary_index',
        name='summary_index'),
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key/$', 'summary_object_key'),
    url(r'^(?P<abbr>[a-z]{2})/summary_object_key_vals/$',
        'summary_object_key_vals'),
    url(r'^object_json/(?P<collection>[^/]{,100})/(?P<_id>.{,100})/',
        'object_json', name='object_json'),

    # runlog URLs.
    url(r'^state-run-detail/(?P<abbr>[a-z]{2})/$', 'state_run_detail',
        name="state_run_detail"),
    url(r'^run-detail/(?P<obj>.*)/$', 'run_detail', name="run_detail"),
    url(r'^run-detail-data/(?P<abbr>[a-z]{2})/$', 'run_detail_graph_data',
        name="run_detail-data"),

    # Merge-o-matic URLs.
    url(r'^(?P<abbr>[a-z]{2})/mom/$', 'mom_index', name="mom_index"),
    url(r'^(?P<abbr>[a-z]{2})/mom/merge/$', 'mom_merge', name="mom_merge"),
    url(r'^(?P<abbr>[a-z]{2})/mom/commit/$', 'mom_commit', name="mom_commit"),

    # New feed URLs.
    url(r'^newsblogs/$', 'newsblogs', name='newsblogs'),

)
