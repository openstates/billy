import itertools

from django.core import urlresolvers

from .base import (db, Document, RelatedDocument, RelatedDocuments,
                   ListManager, DEBUG, logger)
from .metadata import Metadata


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator', instance_key='leg_id')


class CommitteeMemberManager(ListManager):

    keyname = 'members'

    def __iter__(self):
        members = self.committee['members']
        ids = filter(None, [obj['leg_id'] for obj in members])
        spec = {'_id': {'$in': ids}}
        if DEBUG:
            msg = '{0}.{1}({2}, {3}, {4})'.format(
                        'legislators',
                        'find', spec, (), {})
            logger.debug(msg)

        return itertools.izip(members, db.legislators.find(spec))


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

    def get_absolute_url(self):
        args = [self.metadata['abbreviation'],
                self['_id']]
        return urlresolvers.reverse('committee', args=args)

