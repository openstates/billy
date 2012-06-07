import operator
import itertools
import collections

from django.core import urlresolvers
from billy.web.public.viewdata import blurbs

from .base import (db, Document, RelatedDocuments, ListManager, DictManager,
                   AttrManager, take)
from .metadata import Metadata


class Role(dict):

    def data(self):
        '''This roles term metadata from the metadata['terms'] list.
        '''
        metadata = self.manager.document
        return metadata.term_dict[self['term']]

    def is_committee(self):
        return ('committee' in self)

    def committee_name(self):
        name = self['committee']
        if 'subcommittee' in self:
            sub = self['subcommittee']
            if sub:
                name = '%s - %s' % (name, sub)
        return name


class RolesManager(ListManager):
    wrapper = Role


class OldRole(DictManager):
    methods_only = True

    @property
    def termdata(self):
        dict_ = self.document.metadata.terms_manager.dict_
        return dict_[self['term']]


class OldRolesManager(DictManager):
    keyname = 'old_roles'
    wrapper = OldRole

    def __iter__(self):
        wrapper = self._wrapper
        for role in itertools.chain.from_iterable(self.values()):
            inst = wrapper(role)
            yield inst

    def sessions_served(self):
        sessions = collections.defaultdict(set)
        for role in self:
            sessions[role['term']] |= set(list(role.termdata.session_names()))
        return dict(sessions)


class LegislatorVotesManager(AttrManager):
    methods_only = True

    def __iter__(self):
        _id = self.document['_id']
        for bill in self.document.metadata.bills(
            {'$or': [{'votes.yes_votes.leg_id': _id},
                     {'votes.no_votes.leg_id': _id},
                     {'votes.other_votes.leg_id': _id}]}
        ):
            for vote in bill.votes_manager:
                for k in ['yes_votes', 'no_votes', 'other_votes']:
                    for voter in vote[k]:
                        if voter['leg_id'] == _id:
                            yield vote


class Legislator(Document):

    collection = db.legislators
    istance_key = 'leg_id'

    committees = RelatedDocuments('Committee', model_keys=['members.leg_id'])
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])
    roles_manager = RolesManager()
    old_roles_manager = OldRolesManager()
    votes_manager = LegislatorVotesManager()

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def get_absolute_url(self):
        args = (self.metadata['state'], self.id)
        return urlresolvers.reverse('legislator', args=args)

    def votes_3_sorted(self):
        _id = self['_id']
        votes = self.votes_manager
        votes = take(3, sorted(votes, key=operator.itemgetter('date')))
        for i, vote in enumerate(votes):
            for vote_value in ['yes', 'no', 'other']:
                id_getter = operator.itemgetter('leg_id')
                ids = map(id_getter, vote['%s_votes' % vote_value])
                if _id in ids:
                    break
            yield i, vote_value, vote

    def bio_blurb(self):
        return blurbs.bio_blurb(self)

    def sponsored_bills(self, extra_spec=None, *args, **kwargs):
        if extra_spec is None:
            extra_spec = {}
        extra_spec.update({'sponsors.leg_id': self.id})
        return self.metadata.bills(extra_spec, *args, **kwargs)

    def primary_sponsored_bills(self):
        return self.metadata.bills({'sponsors.type': 'primary',
                                    'sponsors.leg_id': self.id})

    def secondary_sponsored_bills(self):
        return self.metadata.bills({'sponsors.type': {'$ne': 'primary'},
                                    'sponsors.leg_id': self.id})

    def display_name(self):
        return '%s %s' % (self['first_name'], self['last_name'])

    def sessions_served(self):
        session_details = self.metadata['session_details']
        terms = self.metadata['terms']
        for role in self['roles']:
            if role['type'] == 'member':
                term_name = role['term']

                try:
                    details = session_details[term_name]
                except KeyError:
                    for term in terms:
                        if term['name'] == term_name:
                            for session in term['sessions']:
                                details = session_details[session]
                                yield details['display_name']
                else:
                    details['display_name']
