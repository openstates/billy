import urlparse
import datetime
from django.core import urlresolvers
from django.template.defaultfilters import slugify, truncatewords

from .base import feeds_db, Document
from .metadata import Metadata


class FeedEntry(Document):
    collection = feeds_db.entries

    def __init__(self, *args, **kw):
        super(FeedEntry, self).__init__(*args, **kw)
        self._process()

    def _process(self):
        '''Mutate the feed entry with hyperlinked entities. Add tagging
        data and other template context values, including source.
        '''
        entity_types = {'L': 'legislator',
                        'C': 'committee',
                        'B': 'bill'}
        entry = self

        summary = truncatewords(entry['summary'], 50)
        entity_strings = entry['entity_strings']
        entity_ids = entry['entity_ids']
        state = entry['state']

        _entity_strings = []
        _entity_ids = []
        _entity_urls = []
        _done = []
        if entity_strings:
            for entity_string, _id in zip(entity_strings, entity_ids):
                if entity_string in _done:
                    continue
                else:
                    _done.append(entity_string)
                    _entity_strings.append(entity_string)
                    _entity_ids.append(_id)
                entity_type = entity_types[_id[2]]
                if entity_type == 'legislator':
                    url = urlresolvers.reverse(
                        entity_type, args=[state, _id, slugify(entity_string)])
                else:
                    url = urlresolvers.reverse(entity_type, args=[state, _id])
                _entity_urls.append(url)
                summary = summary.replace(entity_string,
                    '<a href="%s">%s</a>' % (url, entity_string))
            entity_data = zip(_entity_strings, _entity_ids, _entity_urls)
            entry['summary'] = summary
            entry['entity_data'] = entity_data

        entry['id'] = entry['_id']
        urldata = urlparse.urlparse(entry['link'])
        entry['source'] = urldata.scheme + urldata.netloc
        entry['host'] = urldata.netloc
        del entry['published']

    def published(self):
        return datetime.datetime.fromtimestamp(self['published_parsed'])

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])
