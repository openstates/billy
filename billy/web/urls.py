from django.conf import settings
from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    (r'^api/', include('billy.web.api.urls')),
    (r'^admin/', include('billy.web.admin.urls')),
    (r'^public/', include('billy.web.public.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.contrib.staticfiles.views',
                            url(r'^static/(?P<path>.*)$', 'serve'),
)
