
from django.conf.urls.defaults import patterns, url

from billy.web.public.views import (VotesList, FeedsList,
    BillsBySubject, SponsoredBillsList, BillsIntroducedUpper,
    BillsIntroducedLower, BillsPassedUpper, BillsPassedLower,
    StateBills, FilterBills)

from billy.web.public.feeds import (SponsoredBillsFeed,
    BillsPassedLowerFeed, BillsPassedUpperFeed, BillsIntroducedLowerFeed,
    BillsIntroducedUpperFeed, VotesListFeed, NewsListFeed, BillsBySubjectFeed)


urlpatterns = patterns('billy.web.public.views',

    url(r'^$', 'homepage', name='homepage'),
    url(r'^(?P<scope>[a-z]{,3})/search/$', 'search', name='search'),
    url(r'^(?P<abbr>[a-z]{2})/$', 'state', name='state'),
    url(r'^state_selection/$', 'state_selection',
        name='state_selection'),
    url(r'^pick_a_state/$', 'pick_a_state',
        name='pick_a_state'),
    url(r'^chamber_select/(?P<collection_name>\w+)$', 'chamber_select',
        name='chamber_select'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/legislators/$',
        'legislators', name='legislators'),

    url(r'^(?P<abbr>[a-z]{2})/legislator/(?P<leg_id>\w+)/$',
        'legislator', name='legislator'),

    url(r'^(?P<abbr>[a-z]{2})/legislator_inactive/(?P<leg_id>\w+)/$',
        'legislator_inactive', name='legislator_inactive'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/committees/$',
        'committees', name='committees'),

    url(r'^(?P<abbr>[a-z]{2})/committees/(?P<chamber>\w+)/$',
        'committees_chamber', name='committees_chamber'),

    url(r'^(?P<abbr>[a-z]{2})/committee/(?P<committee_id>\w+)/$',
        'committee', name='committee'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/bills_by_subject/(?P<subject>[^/]+)/$',
        BillsBySubject.as_view(), name='bills_by_subject'),

    url(r'^(?P<abbr>[a-z]{2})/bills_by_subject/(?P<subject>[^/]+)/rss/$',
        BillsBySubjectFeed(), name='bills_by_subject_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills_introduced_upper/$',
        BillsIntroducedUpper.as_view(), name='bills_introduced_upper'),

    url(r'^(?P<abbr>[a-z]{2})/bills_introduced_upper/rss/$',
        BillsIntroducedUpperFeed(), name='bills_introduced_upper_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills_introduced_lower/$',
        BillsIntroducedLower.as_view(), name='bills_introduced_lower'),

    url(r'^(?P<abbr>[a-z]{2})/bills_introduced_lower/rss/$',
        BillsIntroducedLowerFeed(), name='bills_introduced_lower_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills_passed_upper/$',
        BillsPassedUpper.as_view(), name='bills_passed_upper'),

    url(r'^(?P<abbr>[a-z]{2})/bills_passed_upper/rss/$',
        BillsPassedUpperFeed(), name='bills_passed_upper_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills_passed_lower/$',
        BillsPassedLower.as_view(), name='bills_passed_lower'),

    url(r'^(?P<abbr>[a-z]{2})/bills_passed_lower/rss/$',
        BillsPassedLowerFeed(), name='bills_passed_lower_rss/'),

    url(r'^(?P<abbr>[a-z]{2})/sponsored_bills/(?P<collection_name>[^/]+)/(?P<id>[^/]+)/$',
        SponsoredBillsList.as_view(), name='sponsored_bills'),

    url(r'^(?P<abbr>[a-z]{2})/sponsored_bills/(?P<collection_name>[^/]+)/(?P<id>[^/]+)/rss/$',
        SponsoredBillsFeed(), name='sponsored_bills_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bill/(?P<bill_id>\w+)/$',
        'bill', name='bill'),

    url(r'^(?P<abbr>[a-z]{2})/event/(?P<event_id>\w+)/$',
        'event', name='event'),

    url(r'^(?P<abbr>[a-z]{2})/events/$',
        'events', name='events'),

    url(r'^(?P<abbr>[a-z]{2})/bills', StateBills.as_view(), name='bills'),

    url(r'^(?P<abbr>[a-z]{2})/filter_bills', FilterBills.as_view(), name='filter_bills'),
    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/vote/(?P<bill_id>\w+)/(?P<vote_index>\w+)/$',
        'vote', name='vote'),

    url(r'^(?P<abbr>[a-z]{2})/votes_list/(?P<collection_name>\w+)/(?P<id>\w+)/$',
        VotesList.as_view(), name='votes_list'),

    url(r'^(?P<abbr>[a-z]{2})/votes_list/(?P<collection_name>\w+)/(?P<id>\w+)/rss/$',
        VotesListFeed(), name='votes_list_rss'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/feeds_list/(?P<collection_name>\w+)/(?P<id>\w+)/$',
        FeedsList.as_view(), name='feeds_list'),

    url(r'^(?P<abbr>[a-z]{2})/feeds_list/(?P<collection_name>\w+)/(?P<id>\w+)/rss/$',
        NewsListFeed(), name='feeds_list_rss'),
)

urlpatterns += patterns('',
    # other views
    url(r'^downloads/$', 'billy.web.public.views_other.downloads', name='downloads'),
    url(r'^find_your_legislator/$', 'billy.web.public.views.find_your_legislator',
        name='find_your_legislator'),
)
