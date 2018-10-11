import json
import datetime

from billy.utils import chamber_name
from billy.core import settings

from django.template import defaultfilters
from piston.emitters import Emitter, JSONEmitter


class DateTimeAwareJSONEncoder(json.JSONEncoder):
    # We wouldn't need this if django's stupid DateTimeAwareJSONEncoder
    # used settings.DATETIME_FORMAT instead of hard coding its own
    # format string.

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return defaultfilters.date(o, 'DATETIME_FORMAT')
        elif isinstance(o, datetime.date):
            return defaultfilters.date(o, 'DATE_FORMAT')
        elif isinstance(o, datetime.time):
            return defaultfilters.date(o, 'TIME_FORMAT')

        return super(DateTimeAwareJSONEncoder, self).default(o)


class BillyJSONEmitter(JSONEmitter):
    """
    Removes private fields (keys preceded by '_') recursively and
    outputs as JSON, with datetimes converted to strings.
    """

    def render(self, request):
        cb = request.GET.get('callback', None)
        seria = json.dumps(self.construct(), cls=DateTimeAwareJSONEncoder,
                           ensure_ascii=False)

        if cb:
            return "%s(%s)" % (cb, seria)

        return seria

    def construct(self):
        return self._clean(super(BillyJSONEmitter, self).construct())

    def _clean(self, obj):
        if isinstance(obj, dict):
            # convert _id to id
            if '_id' in obj:
                obj['id'] = obj['_id']
            if '_all_ids' in obj:
                obj['all_ids'] = obj['_all_ids']

            for key, value in obj.items():
                if key.startswith('_'):
                    del obj[key]
                else:
                    obj[key] = self._clean(value)
        elif isinstance(obj, list):
            obj = [self._clean(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            for key, value in obj.__dict__.items():
                if key.startswith('_'):
                    del obj.__dict__[key]
                else:
                    obj.__dict__[key] = self._clean(value)
        return obj
