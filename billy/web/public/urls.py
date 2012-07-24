from django.conf.urls.defaults import patterns, url

from billy.web.public.views.misc import VotesList, NewsList
from billy.web.public.views.events import EventsList
from billy.web.public.views.bills import StateBills, AllStateBills
from billy.web.public.views.region import ShowMoreLegislators

from billy.web.public.feeds import (SponsoredBillsFeed,
    BillsPassedLowerFeed, BillsPassedUpperFeed, BillsIntroducedLowerFeed,
    BillsIntroducedUpperFeed, VotesListFeed, NewsListFeed, BillsBySubjectFeed,
    StateEventsFeed, BillsByTypeFeed)

# misc. views
urlpatterns = patterns('billy.web.public.views.misc',
    url(r'^$', 'homepage', name='homepage'),
    url(r'^downloads/$', 'downloads', name='downloads'),
    url(r'^find_your_legislator/$', 'find_your_legislator',
        name='find_your_legislator'),
    url(r'^get_district/(?P<district_id>.+)/$', 'get_district',
        name='get_district'),

    # votes & news
    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/'
        '(?P<slug>[^/]+)/news/$',
        NewsList.as_view(), name='news_list'),
    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/'
        '(?P<slug>[^/]+)/news/rss/$',
        NewsListFeed(), name='news_list_rss'),
    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/votes/$',
        VotesList.as_view(), name='votes_list'),
    url(r'^(?P<abbr>[a-z]{2})/(?P<collection_name>\w+)/(?P<_id>\w+)/'
        'votes/rss/$',
        VotesListFeed(), name='votes_list_rss'),

)

# region/state specific
urlpatterns += patterns('billy.web.public.views.region',
    url(r'^(?P<abbr>[a-z]{,3})/search/$', 'search', name='search'),
    url(r'^(?P<abbr>[a-z]{,3})/search/show_more_legislators/$',
        ShowMoreLegislators.as_view(), name='show_more_legislators'),
    url(r'^(?P<abbr>[a-z]{2})/$', 'state', name='state'),
    url(r'^state_selection/$', 'state_selection', name='state_selection'),
)

# events
urlpatterns += patterns('billy.web.public.views.events',
    url(r'^(?P<abbr>[a-z]{2})/events/$', EventsList.as_view(),
        name='events'),
    url(r'^(?P<abbr>[a-z]{2})/events/rss/$', StateEventsFeed(),
        name='events_rss'),
    url(r'^(?P<abbr>[a-z]{2})/events/(?P<event_id>\w+)/', 'event',
        name='event'),
)

# committees
urlpatterns += patterns('billy.web.public.views.committees',
    url(r'^(?P<abbr>[a-z]{2})/committees/$', 'committees', name='committees'),
    url(r'^(?P<abbr>[a-z]{2})/committees/(?P<committee_id>[A-Z]{3}\d+)/',
        'committee', name='committee'),
)

# legislators
urlpatterns += patterns('billy.web.public.views.legislators',

    url(r'^(?P<abbr>[a-z]{2})/legislators/$', 'legislators',
        name='legislators'),
    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>\w+)/(?P<slug>[^/]*)/$',
        'legislator', name='legislator'),
    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>\w+)/$',
        'legislator', name='legislator_noslug'),
    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<_id>[^/]+)/(?P<slug>[^/]+)/'
        'bills/sponsored/rss/$',
        SponsoredBillsFeed(), name='legislator_sponsored_bills_rss'),
)

urlpatterns += patterns('billy.web.public.views.bills',
    url(r'^(?P<abbr>[a-z]{2})/bills/$', StateBills.as_view(), name='bills'),
    url(r'^(?P<abbr>all)/bills/$', AllStateBills.as_view(), name='bills'),
    url(r'^(?P<abbr>[a-z]{2})/bills/(?P<session>[^/]+)/(?P<bill_id>[^/]+)/$',
        'bill', name='bill'),
    url(r'^(?P<abbr>[a-z]{2})/votes/(?P<vote_id>\w+)/$', 'vote', name='vote'),
    # bill rss views
    url(r'^(?P<abbr>[a-z]{2})/bills/by_subject/(?P<subject>[^/]+)/rss/$',
        BillsBySubjectFeed(), name='bills_by_subject_rss'),
    url(r'^(?P<abbr>[a-z]{2})/bills/by_type/(?P<type>[^/]+)/rss/$',
        BillsByTypeFeed(), name='bills_by_type_rss'),
    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/upper/rss/$',
        BillsIntroducedUpperFeed(), name='bills_introduced_upper_rss'),
    url(r'^(?P<abbr>[a-z]{2})/bills/introduced/lower/rss/$',
        BillsIntroducedLowerFeed(), name='bills_introduced_lower_rss'),
    url(r'^(?P<abbr>[a-z]{2})/bills/passed/upper/rss/$',
        BillsPassedUpperFeed(), name='bills_passed_upper_rss'),
    url(r'^(?P<abbr>[a-z]{2})/bills/passed/lower/rss/$',
        BillsPassedLowerFeed(), name='bills_passed_lower_rss'),
)
