from django.core import urlresolvers
from django.template.defaultfilters import slugify

from billy.core import mdb as db
from billy.core import settings
from .base import Document, RelatedDocument, RelatedDocuments, ListManager
from .metadata import Metadata


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator', instance_key='leg_id')


class CommitteeMemberManager(ListManager):

    keyname = 'members'

    def __iter__(self):
        members = self.committee['members']

        # First check whether legislators are cached
        # in this instance.
        try:
            objs = self._legislators
        except AttributeError:
            # If this was a metadata.committees_legislators,
            # all the legislators will be accessible
            # from the committee instance.
            try:
                objs = self.committee._legislators
            except AttributeError:
                ids = filter(None, [obj['leg_id'] for obj in members])
                spec = {'_id': {'$in': ids}}
                objs = dict((obj['_id'], obj) for obj in
                            db.legislators.find(spec))
                self._legislators = objs
        for member in members:
            _id = member['leg_id']
            if _id is not None and _id in objs:
                yield (member, objs[_id])
            else:
                yield (member, None)


class Committee(Document):

    collection = db.committees
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    members_objects = CommitteeMemberManager()

    def display_name(self):
        name = self['committee']
        sub = self['subcommittee']
        if sub is not None:
            name = '%s: %s' % (name, sub)
        return name

    def events(self):
        return db.events.find({"participants.committee_id": self['_id']})

    @property
    def metadata(self):
        return Metadata.get_object(self[settings.LEVEL_FIELD])

    def get_absolute_url(self):
        args = [self.metadata['abbreviation'],
                self['_id']]
        url = urlresolvers.reverse('committee', args=args)
        slug = slugify(self.display_name())
        return '%s%s/' % (url, slug)
