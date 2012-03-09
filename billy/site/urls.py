from django.conf import settings
from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    (r'^api/', include('billy.site.api.urls')),
    (r'^browse/', include('billy.site.browse.urls')),
    (r'^www/', include('billy.site.www.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.contrib.staticfiles.views',
                            url(r'^static/(?P<path>.*)$', 'serve'),
)
