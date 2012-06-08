from .base import db, Document, RelatedDocuments, RelatedDocument
from .metadata import Metadata


class Event(Document):

    collection = db.events
    committee_object = RelatedDocument(
        'Committee',
        instance_key='participants.committee_id'
    )

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def bills(self):
        bills = []
        for bill in self['related_bills']:
            if 'bill_id' in bill:
                bills.append(bill['bill_id'])
        return db.bills.find({"_id": { "$in": bills }})

    def committees(self):
        committees = []
        for committee in self['participants']:
            if 'committee_id' in committee:
                committees.append(committee['committee_id'])
        return db.committees.find({"_id": { "$in": committees }})
