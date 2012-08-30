from billy.core import mdb as db
from .base import Document
from .metadata import Metadata


class Report(Document):

    collection = db.reports

    @property
    def metadata(self):
        return Metadata.get_object(self['_id'])
