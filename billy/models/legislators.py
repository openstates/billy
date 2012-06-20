import operator
import itertools
import collections

import pymongo
from django.core import urlresolvers
from django.template.defaultfilters import slugify

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


class Legislator(Document):

    collection = db.legislators
    instance_key = 'leg_id'

    committees = RelatedDocuments('Committee', model_keys=['members.leg_id'])
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])
    roles_manager = RolesManager()
    old_roles_manager = OldRolesManager()
    votes_manager = RelatedDocuments('BillVote', model_keys=[
        'yes_votes.leg_id',
        'no_votes.leg_id',
        'other_votes.leg_id'])

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def slug(self):
        return slugify(self.display_name())

    def get_absolute_url(self):
        kwargs = dict(abbr=self.metadata['abbreviation'],
                      _id=self.id,
                      slug=self.slug())
        return urlresolvers.reverse('legislator', kwargs=kwargs)

    def get_sponsored_bills_url(self):
        kwargs = dict(abbr=self.metadata['abbreviation'],
                      _id=self.id,
                      slug=self.slug(),
                      collection_name='legislators')
        return urlresolvers.reverse(
            'legislator_sponsored_bills', kwargs=kwargs)

    def votes_5_sorted(self):
        _id = self['_id']
        votes = self.votes_manager(limit=5,
            sort=[('date', pymongo.DESCENDING)])
        vote_value = 'other'
        for i, vote in enumerate(votes):
            if _id in vote['yes_votes']:
                vote_value = 'yes'
            if _id in vote['no_votes']:
                vote_value = 'no'
            yield i, vote_value, vote

    def sponsored_bills(self, extra_spec=None, *args, **kwargs):
        if extra_spec is None:
            extra_spec = {}
        extra_spec.update({'sponsors.leg_id': self.id})
        if 'sort' not in kwargs:
            kwargs.update(sort=[('updated_at', pymongo.DESCENDING)])
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
