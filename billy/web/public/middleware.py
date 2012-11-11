from django.conf import settings
from django.shortcuts import render
from django.http import Http404
from billy.models import Metadata, DoesNotExist
from billy.web.public.views.utils import templatename


class LimitStatesMiddleware(object):
    '''This middle ware checks state-specific requests to
    ensure the state is in settings.ACTIVE_STATES. If not,
    it routes the user to a page that explains the state isn't
    available yet.
    '''
    def process_view(self, request, func, args, kw):
        # Skip API or admin views.
        for path in ['/admin', '/api']:
            if request.path.startswith(path):
                return func(request, *args, **kw)

        # For public views, make sure the state is active.
        if 'abbr' in kw:
            if kw['abbr'] not in settings.ACTIVE_STATES + ['all']:
                try:
                    metadata = Metadata.get_object(kw['abbr'])
                except DoesNotExist:
                    raise Http404

                return render(request, templatename('state_not_active_yet'),
                              dict(metadata=metadata, nav_active=None))
            else:
                return func(request, *args, **kw)
