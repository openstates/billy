from django.conf import settings

from billy.web.public.views import state_not_active_yet


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
            if kw['abbr'] not in settings.ACTIVE_STATES:
                return state_not_active_yet(request, args, kw)
            else:
                return func(request, *args, **kw)
