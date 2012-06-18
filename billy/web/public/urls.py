from django.conf.urls.defaults import patterns, url

from billy.web.public.views import (VotesList, NewsList,
    BillsBySubject, SponsoredBillsList, BillsIntroducedUpper,
    BillsIntroducedLower, BillsPassedUpper, BillsPassedLower,
    StateBills, EventsList,)

from billy.web.public.feeds import (SponsoredBillsFeed,
    BillsPassedLowerFeed, BillsPassedUpperFeed, BillsIntroducedLowerFeed,
    BillsIntroducedUpperFeed, VotesListFeed, NewsListFeed, BillsBySubjectFeed,
    StateEventsFeed,)


urlpatterns = patterns('billy.web.public.views',

    url(r'^$', 'homepage', name='homepage'),
    url(r'^(?P<scope>[a-z]{,3})/search/$', 'search', name='search'),
    url(r'^(?P<abbr>[a-z]{2})/$', 'state', name='state'),
    url(r'^state_selection/$', 'state_selection',
        name='state_selection'),
    url(r'^get_district/(?P<district_id>.+)/$',
        'get_district', name='get_district'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>[^/]+)/(?P<slug>[^/]+)/bills/sponsored/$',
        SponsoredBillsList.as_view(), name='legislator_sponsored_bills'),

    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>[^/]+)/(?P<slug>[^/]+)/bills/sponsored/rss/$',
        SponsoredBillsFeed(), name='legislator_sponsored_bills_rss'),

    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/votes/$',
        VotesList.as_view(), name='votes_list'),

    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/votes/rss/$',
        VotesListFeed(), name='votes_list_rss'),

    url(r'^(?P<abbr>[a-z]{2})/legislators/$',
        'legislators', name='legislators'),

    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>\w+)/(?P<slug>[^/]+)/$',
        'legislator', name='legislator'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/committees/$',
        'committees', name='committees'),

    url(r'^(?P<abbr>[a-z]{2})/committees/(?P<committee_id>[A-Z]{3}\d+)/',
        'committee', name='committee'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/bills/by_subject/(?P<subject>[^/]+)/$',
        BillsBySubject.as_view(), name='bills_by_subject'),

    url(r'^(?P<abbr>[a-z]{2})/bills/by_subject/(?P<subject>[^/]+)/rss/$',
        BillsBySubjectFeed(), name='bills_by_subject_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/upper/$',
        BillsIntroducedUpper.as_view(), name='bills_introduced_upper'),

    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/upper/rss/$',
        BillsIntroducedUpperFeed(), name='bills_introduced_upper_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/lower/$',
        BillsIntroducedLower.as_view(), name='bills_introduced_lower'),

    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/lower/rss/$',
        BillsIntroducedLowerFeed(), name='bills_introduced_lower_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills/passed/upper/$',
        BillsPassedUpper.as_view(), name='bills_passed_upper'),

    url(r'^(?P<abbr>[a-z]{2})/bills/passed/upper/rss/$',
        BillsPassedUpperFeed(), name='bills_passed_upper_rss'),

    url(r'^(?P<abbr>[a-z]{2})/bills/passed/lower/$',
        BillsPassedLower.as_view(), name='bills_passed_lower'),

    url(r'^(?P<abbr>[a-z]{2})/bills/passed/lower/rss/$',
        BillsPassedLowerFeed(), name='bills_passed_lower_rss'),


    url(r'^(?P<abbr>[a-z]{2})/bills/(?P<bill_id>\w+)/',
        'bill', name='bill'),


    url(r'^(?P<abbr>[a-z]{2})/events/$',
        EventsList.as_view(), name='events'),

    url(r'^(?P<abbr>[a-z]{2})/events/rss/$', StateEventsFeed(), name='events_rss'),

    url(r'^(?P<abbr>[a-z]{2})/events/(?P<event_id>\w+)/',
        'event', name='event'),

    url(r'^(?P<abbr>[a-z]{2})/bills/$', StateBills.as_view(), name='bills'),

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/votes/(?P<_id>\w+)/',
        'vote', name='vote'),


    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/(?P<slug>[^/]+)/news/$',
        NewsList.as_view(), name='news_list'),

    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/(?P<slug>[^/]+)/news/rss/$',
        NewsListFeed(), name='news_list_rss'),
)

urlpatterns += patterns('',
    # other views
    url(r'^downloads/$', 'billy.web.public.views_other.downloads', name='downloads'),
    url(r'^find_your_legislator/$', 'billy.web.public.views.find_your_legislator',
        name='find_your_legislator'),
)
