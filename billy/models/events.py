from .base import db, Document, RelatedDocuments
from .metadata import Metadata


class Event(Document):

    collection = db.events
    bills = RelatedDocuments('Bill', model_keys=['related_bills.bill_id'])

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])
