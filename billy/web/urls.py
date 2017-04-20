from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.views import serve

urlpatterns = [
    url(r'^api/', include('billy.web.api.urls')),
    url(r'^admin/', include('billy.web.admin.urls')),
    url(r'^public/', include('billy.web.public.urls')),
]

if settings.DEBUG:
    urlpatterns += [url(r'^static/(?P<path>.*)$', serve)],
