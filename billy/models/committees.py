import itertools

from django.core import urlresolvers
from django.template.defaultfilters import slugify

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

        objs = dict((obj['_id'], obj) for obj in db.legislators.find(spec))
        for member in members:
            _id = member['leg_id']
            if _id is not None:
                yield (member, objs[_id])
            else:
                yield (member, None)


class Committee(Document):

    collection = db.committees
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    members_objects = CommitteeMemberManager()

    def display_name(self):
        try:
            name = self['committee']
        except KeyError:
            return self['subcommittee']
        else:
            sub = self['subcommittee']
            if sub is not None:
                name = '%s: %s' % (name, sub)
        return name

    def events(self):
        return db.events.find({"participants.committee_id": self['_id']})

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def get_absolute_url(self):
        args = [self.metadata['abbreviation'],
                self['_id']]
        url = urlresolvers.reverse('committee', args=args)
        slug = slugify(self.display_name())
        return '%s%s/' % (url, slug)

