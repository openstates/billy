from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'robots.txt', 'django.views.generic.simple.direct_to_template',
     {'template': 'robots.txt'}),
    (r'^api/', include('billy.site.api.urls')),
    (r'^browse/', include('billy.site.browse.urls')),
)
