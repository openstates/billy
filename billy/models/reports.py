from .base import db, Document
from .metadata import Metadata


class Report(Document):

    collection = db.reports

    def session_link_data(self):
        '''
        An iterable of tuples like
        ('821', '82nd Legislature, 1st Called Session')
        '''
        session_details = self.metadata['session_details']
        for s in self['bills']['sessions']:
            yield (s, session_details[s]['display_name'])

    @property
    def metadata(self):
        return Metadata.get_object(self['_id'])
