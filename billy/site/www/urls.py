
from django.conf.urls.defaults import patterns, include, url

from billy.site.www.views import *

urlpatterns = patterns('',
    url(r'^(?P<abbr>[a-z]{2})/$', state, name='state'),
    url(r'^state_selection/$', state_selection, 
        name='state_selection'),

	url(r'^(?P<abbr>[a-z]{2})/legislators', legislators, name='legislators'),
	url(r'^(?P<abbr>[a-z]{2})/bills', bills, name='bills'),
	url(r'^(?P<abbr>[a-z]{2})/committees', committees, name='committees'),
)



