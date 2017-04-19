from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.views import serve

urlpatterns = [
    (r'^api/', include('billy.web.api.urls')),
    (r'^admin/', include('billy.web.admin.urls')),
    (r'^public/', include('billy.web.public.urls')),
]

if settings.DEBUG:
    urlpatterns += [url(r'^static/(?P<path>.*)$', serve)],
