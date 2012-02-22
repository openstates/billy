
from django.conf.urls.defaults import patterns, include, url

from billy.site.www.views import legislators, legislators_chamber, \
    legislator, committees_chamber, committees, committee, bill, \
    bills, vote, state, state_selection


urlpatterns = patterns('',
    url(r'^(?P<abbr>[a-z]{2})/$', state, name='state'),
    url(r'^state_selection/$', state_selection, 
        name='state_selection'),


    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/legislators/$', 
        legislators, name='legislators'),
            
    url(r'^(?P<abbr>[a-z]{2})/legislators/(?P<chamber>\w+)/$', 
        legislators_chamber, name='legislators_chamber'),              

    url(r'^(?P<abbr>[a-z]{2})/legislator/(?P<leg_id>\w+)/$', 
        legislator, name='legislator'),            

    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/committees/$', 
        committees, name='committees'),

    url(r'^(?P<abbr>[a-z]{2})/committees/(?P<chamber>\w+)/$', 
        committees_chamber, name='committees_chamber'),      

    url(r'^(?P<abbr>[a-z]{2})/committee/(?P<committee_id>\w+)/$', 
        committee, name='committee'),       
        
    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/bills', bills, name='bills'),
    
    url(r'^(?P<abbr>[a-z]{2})/(?P<bill_id>\w+)/$', 
        bill, name='bill'),      


    #------------------------------------------------------------------------
    url(r'^(?P<abbr>[a-z]{2})/(?P<bill_id>\w+)/(?P<vote_index>\w+)/$', 
        vote, name='vote'),      
)



