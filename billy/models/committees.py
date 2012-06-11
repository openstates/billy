from .base import (db, Document, RelatedDocument, RelatedDocuments,
                   ListManager, DEBUG, logger)
from .metadata import Metadata


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator', instance_key='leg_id')


class CommitteeMemberManager(ListManager):

    keyname = 'members'

    def __iter__(self):
        for obj in self.document['members']:
            # This would be better as an '_id': {$or: [id1, id2,...]}
            if 'leg_id' in obj:
                if DEBUG:
                    msg = '{0}.{1}({2}, {3}, {4})'.format(
                                'legislators',
                                'find_one', {'_id': obj['leg_id']}, (), {})
                    logger.debug(msg)
                legislator = db.legislators.find_one({'_id': obj['leg_id']})
                yield obj, legislator


class Committee(Document):

    collection = db.committees
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    members_objects = CommitteeMemberManager()

    def display_name(self):
        try:
            return self['committee']
        except KeyError:
            try:
                return self['subcommittee']
            except KeyError:
                raise

    def events(self):
        return db.events.find({"participants.committee_id": self['_id']})

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])
