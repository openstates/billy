import itertools
import operator
from collections import defaultdict

import pymongo
from django.core import urlresolvers
from django.template.defaultfilters import slugify

from billy.core import mdb as db, settings
from billy.utils import term_for_session
from .base import Document, RelatedDocuments, ListManager
from .metadata import Metadata
from .bills import BillVote
from .utils import CachedAttribute


class Role(dict):

    def data(self):
        '''This role's term metadata from the metadata['terms'] list.
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

    def type_display(self):
        ignored_role_types = [
            'member',
            'committee member',
        ]
        if self['type'] in ignored_role_types:
            return ''
        else:
            return self['type'].title()


class RolesManager(ListManager):
    wrapper = Role


class OldRole(dict):
    '''The `OldRolesManager` has been taken out behind the barn and
    shot on account of its confusingness. To replace it, this wrapper
    class defines a few helpful methods for templates to use, and
    each Legislator object dynamically gets its own OldRole class
    created as a subclass of this class, with an extra attr `document`
    pointing back to the related legislator object. The method that
    creates the new OldRole class is Legislator._old_role_wrapper.
    '''

    @property
    def termdata(self):
        dict_ = self.document.metadata.terms_manager.dict_
        return dict_[self['term']]

    def chamber_name(self):
        chamber = self['chamber']
        if chamber == 'joint':
            return 'Joint'
        return self.document.metadata['chambers'][chamber]['name']

    def committee_object(self):
        '''If the committee id no longer exists in mongo for some reason,
        this function returns None.
        '''
        if 'committee_id' in self:
            _id = self['committee_id']
            return self.document._old_roles_committees.get(_id)
        else:
            return self


class Legislator(Document):

    collection = db.legislators
    instance_key = 'leg_id'

    committees = RelatedDocuments('Committee', model_keys=['members.leg_id'])
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'],
                                    sort=[('published_parsed', -1)])
    roles_manager = RolesManager()
    votes_manager = RelatedDocuments('BillVote', model_keys=['_voters'])

    @property
    def metadata(self):
        return Metadata.get_object(self[settings.LEVEL_FIELD])

    def slug(self):
        return slugify(self.display_name())

    def get_absolute_url(self):
        kwargs = dict(abbr=self.metadata['abbreviation'],
                      _id=self.id,
                      slug=self.slug())
        return urlresolvers.reverse('legislator', kwargs=kwargs)

    def get_sponsored_bills_url(self):
        kwargs = dict(abbr=self.metadata['abbreviation'])
        return ''.join(urlresolvers.reverse('bills', kwargs=kwargs),
                       '?sponsor__leg_id=', self.id)

    def votes_6_sorted(self):
        _id = self['_id']
        votes = self.votes_manager(
            limit=6, sort=[('date', pymongo.DESCENDING)])
        for vote in votes:
            vote_value = 'other'
            for obj in vote['yes_votes']:
                if _id == obj['leg_id']:
                    vote_value = 'yes'
                    break
            if vote_value == 'other':
                for obj in vote['no_votes']:
                    if _id == obj['leg_id']:
                        vote_value = 'no'
                        break
            yield vote_value, vote

    def sponsored_bills(self, extra_spec=None, *args, **kwargs):
        if extra_spec is None:
            extra_spec = {}
        extra_spec.update({'sponsors.leg_id': self.id})
        if 'sort' not in kwargs:
            kwargs.update(sort=[('updated_at', pymongo.DESCENDING)])
        return self.metadata.bills(extra_spec, *args, **kwargs)

    def primary_sponsored_bills(self, fields=None):
        kwargs = {}
        if fields is not None:
            kwargs['fields'] = fields
        return self.metadata.bills({'sponsors.type': 'primary',
                                    'sponsors.leg_id': self.id}, **kwargs)

    def secondary_sponsored_bills(self):
        return self.metadata.bills({'sponsors.type': {'$ne': 'primary'},
                                    'sponsors.leg_id': self.id})

    def display_name(self):
        return self['full_name']

    def title(self):
        chamber = self.get('chamber')
        if chamber and chamber in self.metadata['chambers']:
            return self.metadata['chambers'][chamber]['title']
        else:
            return ''

    def office_emails(self):
        for office in self['offices']:
            if 'email' in office:
                yield office['email']

    def context_role(self, bill=None, vote=None, session=None, term=None):
        '''Tell this legislator object which session to use when calculating
        the legisator's context_role for a given bill or vote.
        '''
        # If no hints were given about the context, look for a related bill,
        # then for a related vote.
        if not any([bill, vote, session, term]):
            try:
                bill = self.bill
            except AttributeError:
                # A vote?
                try:
                    vote = self.vote
                except AttributeError:
                    # If we're here, this method was called on a
                    # Legislator was that doesn't have a related bill or vote.
                    return ''

        # If we still have to historical point of reference, figuring
        # out the context role is impossible. Return emtpy string.
        if not any([bill, vote, session, term]):
            return ''

        # First figure out the term.
        if bill is not None:
            term = bill['_term']

        elif vote is not None:
            try:
                _bill = vote.bill
            except AttributeError:
                _bill = BillVote(vote).bill
            if callable(_bill):
                _bill = _bill()
            term = _bill['_term']

        if term is None and session is not None:
            term = term_for_session(self[settings.LEVEL_FIELD], session)

        # Use the term to get the related roles. First look in the current
        # roles list, then fail over to the old_roles list.
        roles = [r for r in self['roles']
                 if r.get('type') == 'member' and r.get('term') == term]
        roles = filter(None, roles)

        if not roles:
            roles = [r for r in self['old_roles'].get(term, [])
                     if r.get('type') == 'member']
        roles = filter(None, roles)

        if not roles:
            # Legislator had no roles for this term. If there is a related
            # bill ro vote, this shouldn't happen, but could if the
            # legislator's roles got deleted.
            return ''

        # If there's only one applicable role, we're done.
        if len(roles) == 1:
            role = roles.pop()
            self['context_role'] = role
            return role

        # If only one of term or session is given and there are multiple roles:
        if not filter(None, [bill, vote]):
            if term is not None:
                role = roles[0]
                self['context_role'] = role
                return role

            # Below, use the date of the related bill or vote to determine
            # which (of multiple) roles applies.
            # Get the context date.
            if session is not None:
                # If we're here, we have multiple roles for a single session.
                # Try to find the correct one in self.metadata,
                # else give up.
                session_data = self.metadata['session_details'][session]
                for role in roles:
                    role_start = role.get('start_date')
                    role_end = role.get('end_date')

                    # Return the first role that overlaps at all with the
                    # session.
                    session_start = session_data.get('start_date')
                    session_end = session_data.get('end_date')
                    if session_start and session_end:
                        started_during = (role_start < session_start <
                                          role_end)
                        ended_during = (role_start < session_end < role_end)
                        if started_during or ended_during:
                            self['context_role'] = role
                            return role
                    else:
                        continue

                # Return first role from the session?
                role = roles[0]
                self['context_role'] = role
                return role

        if vote is not None:
            date = vote['date']
        if bill is not None:
            date = bill['action_dates']['first']

        dates_exist = False
        for role in roles:
            start_date = role.get('start_date')
            end_date = role.get('end_date')
            if start_date and end_date:
                dates_exist = True
                if start_date < date < end_date:
                    self['context_role'] = role
                    return role

        if dates_exist:
            # If we're here, the context date didn't fall into any of the
            # legislator's role date ranges.
            return ''

        else:
            # Here the roles didn't have date ranges. Return the last one?
            role = roles.pop()
            self['context_role'] = role
            return role

        return ''

    def all_terms(self):
        terms = set(self.get('old_roles', {}).keys())
        if self['roles']:
            terms.add(self['roles'][0]['term'])
        _term_order = [term['name'] for term in
                       self.metadata['terms']]
        terms = [x[1] for x in
                 sorted([(_term_order.index(term), term) for term in terms])]
        return terms

    @CachedAttribute
    def _old_roles_committees(self):
        ids = []
        for term, roles in self['old_roles'].items():
            _ids = [role.get('committee_id') for role in roles]
            _ids = filter(None, _ids)
            ids.extend(_ids)
        objs = list(db.committees.find({'_id': {'$in': ids}}))
        objs = dict((objs['_id'], objs) for objs in objs)
        return objs

    @CachedAttribute
    def _old_role_wrapper(self):
        cls = type('OldRole', (OldRole,), dict(document=self))
        return cls

    def old_roles_manager(self):
        '''Return old roles, grouped first by term, then by chamber,
        then by type.'''
        wrapper = self._old_role_wrapper
        chamber_getter = operator.methodcaller('get', 'chamber')
        for term, roles in self['old_roles'].items():
            chamber_roles = defaultdict(lambda: defaultdict(list))
            for chamber, roles in itertools.groupby(roles, chamber_getter):
                for role in roles:
                    role = wrapper(role)
                    typeslug = role['type'].lower().replace(' ', '_')
                    chamber_roles[chamber][typeslug].append(role)
            yield term, chamber_roles
