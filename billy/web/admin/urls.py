from django.conf.urls import patterns, url

urlpatterns = patterns(
    'billy.web.admin.views',

    url(r'^$', 'browse_index', name='admin_index'),

    # Quality exceptions (need to be above loose-matching bill view rule)
    url(r'^(?P<abbr>[a-z-]+)/exceptions/$', 'quality_exceptions',
        name='quality_exceptions'),
    url(r'^(?P<abbr>[a-z-]+)/add_exception/$', 'quality_exception_commit',
        name='quality_exception_commit'),
    url(r'^(?P<abbr>[a-z-]+)/remove_exception/(?P<obj>.+)/$',
        'quality_exception_remove', name='quality_exception_remove'),

    # subjects
    url(r'^(?P<abbr>[a-z-]+)/subjects/$', 'subjects',
        name='admin_subjects'),
    url(r'^(?P<abbr>[a-z-]+)/subjects-commit/$', 'subjects_commit',
        name='admin_subjects_commit'),
    url(r'^(?P<abbr>[a-z-]+)/subjects-remove/(?P<id>.+)/$', 'subjects_remove',
        name='admin_subjects_remove'),

    # matching
    url(r'^(?P<abbr>[a-z-]+)/name-matching/$', 'matching.edit',
        name='admin_matching'),
    url(r'^(?P<abbr>[a-z-]+)/name-matching/debug/$', 'matching.debug',
        name='admin_matching_debug'),
    url(r'^(?P<abbr>[a-z-]+)/matching-commit/$', 'matching.commit',
        name='admin_matching_commit'),
    url(r'^(?P<abbr>[a-z-]+)/matching-remove/(?P<id>.+)/$', 'matching.remove',
        name='admin_matching_remove'),

    # Edit a Legislator
    url(r'^legislators-edit/(?P<id>[\w-]+)/$', 'legislator_edit',
        name='admin_legislator_edit'),
    url(r'^legislators-edit-commit/$', 'legislator_edit_commit',
        name='admin_legislator_edit_commit'),


    # admin overview pages
    url(r'^(?P<abbr>[a-z-]+)/$', 'overview', name='admin_overview'),

    # committees
    url(r'^(?P<abbr>[a-z-]+)/committees/$', 'committees',
        name='admin_committees'),
    url(r'^delete_committees/$', 'delete_committees',
        name='delete_committees'),

    # legislators
    url(r'^(?P<abbr>[a-z-]+)/legislators/$', 'legislators',
        name='admin_legislators'),
    url(r'^legislators/(?P<id>[\w-]+)/retire/$', 'retire_legislator',
        name='retire_legislator'),

    # bills
    url(r'^(?P<abbr>[a-z-]+)/bills/$', 'bills', name='admin_bills'),
    url(r'^(?P<abbr>[a-z-]+)/bills/list/$', 'bill_list', name='bill_list'),

    url(r'^(?P<abbr>[a-z-]+)/bad_vote_list/$', 'bad_vote_list',
        name='bad_vote_list'),
    url(r'^(?P<abbr>[a-z-]+)/events/$', 'events', name='admin_events'),
    url(r'^(?P<abbr>[a-z-]+)/event/(?P<event_id>.*)/$', 'event',
        name='admin_event'),

    # missing data
    url(r'^(?P<abbr>[a-z-]+)/other_actions/$', 'other_actions',
        name='other_actions'),
    url(r'^(?P<abbr>[a-z-]+)/duplicate_versions/$', 'duplicate_versions',
        name='duplicate_versions'),
    url(r'^(?P<abbr>[a-z-]+)/progress_meter_gaps/$', 'progress_meter_gaps',
        name='progress_meter_gaps'),

    # Summary urls.
    url(r'^(?P<abbr>[a-z-]+)/summary/(?P<session>[^/]+)$', 'summary_index',
        name='summary_index'),
    url(r'^(?P<abbr>[a-z-]+)/summary_object_key/$', 'summary_object_key'),
    url(r'^(?P<abbr>[a-z-]+)/summary_object_key_vals/$',
        'summary_object_key_vals'),
    url(r'^object_json/(?P<collection>[^/]{,100})/(?P<_id>.{,100})/',
        'object_json', name='object_json'),

    # runlog URLs.
    url(r'^run-detail-list/(?P<abbr>[a-z-]+)/$', 'run_detail_list',
        name="run_detail_list"),
    url(r'^run-detail/(?P<obj>.*)/$', 'run_detail', name="run_detail"),
    url(r'^run-detail-data/(?P<abbr>[a-z-]+)/$', 'run_detail_graph_data',
        name="run_detail-data"),

    # Merge-o-matic URLs.
    url(r'^(?P<abbr>[a-z-]+)/mom/$', 'mom_index', name="mom_index"),
    url(r'^(?P<abbr>[a-z-]+)/mom/merge/$', 'mom_merge', name="mom_merge"),
    url(r'^(?P<abbr>[a-z-]+)/mom/commit/$', 'mom_commit', name="mom_commit"),

    # New feed URLs.
    url(r'^newsblogs/$', 'newsblogs', name='newsblogs'),

)
