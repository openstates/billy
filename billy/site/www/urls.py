
from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^(?P<abbr>[a-z]{2})/$', 'billy.site.web.views.state', name='state'),
)



