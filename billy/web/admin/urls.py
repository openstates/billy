from django.conf.urls import url

from billy.web.admin import views
from billy.web.admin.views import matching

urlpatterns = [
    url(r'^$', views.browse_index, name='admin_index'),

    # Quality exceptions (need to be above loose-matching bill view rule)
    url(r'^(?P<abbr>[a-z-]+)/exceptions/$', views.quality_exceptions,
        name='quality_exceptions'),
    url(r'^(?P<abbr>[a-z-]+)/add_exception/$', views.quality_exception_commit,
        name='quality_exception_commit'),
    url(r'^(?P<abbr>[a-z-]+)/remove_exception/(?P<obj>.+)/$',
        views.quality_exception_remove, name='quality_exception_remove'),

    # subjects
    url(r'^(?P<abbr>[a-z-]+)/subjects/$', views.subjects,
        name='admin_subjects'),
    url(r'^(?P<abbr>[a-z-]+)/subjects-commit/$', views.subjects_commit,
        name='admin_subjects_commit'),
    url(r'^(?P<abbr>[a-z-]+)/subjects-remove/(?P<id>.+)/$', views.subjects_remove,
        name='admin_subjects_remove'),

    # matching
    url(r'^(?P<abbr>[a-z-]+)/name-matching/$', matching.edit,
        name='admin_matching'),
    url(r'^(?P<abbr>[a-z-]+)/name-matching/debug/$', matching.debug,
        name='admin_matching_debug'),
    url(r'^(?P<abbr>[a-z-]+)/matching-commit/$', matching.commit,
        name='admin_matching_commit'),
    url(r'^(?P<abbr>[a-z-]+)/matching-remove/(?P<id>.+)/$', matching.remove,
        name='admin_matching_remove'),

    # Edit a Legislator
    url(r'^legislators-edit/(?P<id>[\w-]+)/$', views.legislator_edit,
        name='admin_legislator_edit'),
    url(r'^legislators-edit-commit/$', views.legislator_edit_commit,
        name='admin_legislator_edit_commit'),


    # admin overview pages
    url(r'^(?P<abbr>[a-z-]+)/$', views.overview, name='admin_overview'),

    # committees
    url(r'^(?P<abbr>[a-z-]+)/committees/$', views.committees,
        name='admin_committees'),
    url(r'^delete_committees/$', views.delete_committees,
        name='delete_committees'),

    # legislators
    url(r'^(?P<abbr>[a-z-]+)/legislators/$', views.legislators,
        name='admin_legislators'),
    url(r'^legislators/(?P<id>[\w-]+)/retire/$', views.retire_legislator,
        name='retire_legislator'),

    # bills
    url(r'^(?P<abbr>[a-z-]+)/bills/$', views.bills, name='admin_bills'),
    url(r'^(?P<abbr>[a-z-]+)/bills/list/$', views.bill_list, name='bill_list'),

    url(r'^(?P<abbr>[a-z-]+)/bad_vote_list/$', views.bad_vote_list,
        name='bad_vote_list'),
    url(r'^(?P<abbr>[a-z-]+)/events/$', views.events, name='admin_events'),
    url(r'^(?P<abbr>[a-z-]+)/event/(?P<event_id>.*)/$', views.event,
        name='admin_event'),

    # missing data
    url(r'^(?P<abbr>[a-z-]+)/other_actions/$', views.other_actions,
        name='other_actions'),
    url(r'^(?P<abbr>[a-z-]+)/duplicate_versions/$', views.duplicate_versions,
        name='duplicate_versions'),
    url(r'^(?P<abbr>[a-z-]+)/progress_meter_gaps/$', views.progress_meter_gaps,
        name='progress_meter_gaps'),

    # Summary urls.
    url(r'^(?P<abbr>[a-z-]+)/summary/(?P<session>[^/]+)$', views.summary_index,
        name='summary_index'),
    url(r'^(?P<abbr>[a-z-]+)/summary_object_key/$', views.summary_object_key),
    url(r'^(?P<abbr>[a-z-]+)/summary_object_key_vals/$',
        views.summary_object_key_vals),
    url(r'^object_json/(?P<collection>[^/]{,100})/(?P<_id>.{,100})/',
        views.object_json, name='object_json'),

    # runlog URLs.
    url(r'^run-detail-list/(?P<abbr>[a-z-]+)/$', views.run_detail_list,
        name="run_detail_list"),
    url(r'^run-detail/(?P<obj>.*)/$', views.run_detail, name="run_detail"),
    url(r'^run-detail-data/(?P<abbr>[a-z-]+)/$', views.run_detail_graph_data,
        name="run_detail-data"),

    # Merge-o-matic URLs.
    url(r'^(?P<abbr>[a-z-]+)/mom/$', views.mom_index, name="mom_index"),
    url(r'^(?P<abbr>[a-z-]+)/mom/merge/$', views.mom_merge, name="mom_merge"),
    url(r'^(?P<abbr>[a-z-]+)/mom/commit/$', views.mom_commit, name="mom_commit"),
]
