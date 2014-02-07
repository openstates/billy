import operator
import itertools

from django.core import urlresolvers

from billy.core import mdb as db, settings
from .base import (Document, RelatedDocument, RelatedDocuments, ListManager,
                   DictManager, AttrManager, DoesNotExist)
from ..utils import metadata as get_metadata

_distinct_subjects = {}
_distinct_types = {}
_distinct_action_types = {}

class Term(DictManager):
    methods_only = True

    def session_info(self):
        details = self.metadata['session_details']
        for session_name in self['sessions']:
            yield dict(details[session_name], name=session_name)

    def session_names(self):
        '''The display names of sessions occuring in this term.
        '''
        details = self.metadata['session_details']
        for sess in self['sessions']:
            yield details[sess]['display_name']


class TermsManager(ListManager):
    wrapper = Term

    @property
    def dict_(self):
        wrapper = self._wrapper
        grouped = itertools.groupby(self.metadata['terms'],
                                    operator.itemgetter('name'))
        data = []
        for term, termdata in grouped:
            termdata = list(termdata)
            assert len(termdata) is 1
            data.append((term, wrapper(termdata[0])))

        return dict(data)


class MetadataVotesManager(AttrManager):
    def __iter__(self):
        for bill in self.document.bills():
            for vote in bill.votes_manager:
                    yield vote


class Metadata(Document):
    '''
    The metadata can also be thought as the jurisdiction (i.e., Montana, Texas)
    when it's an attribute of another object. For example, if you have a
    bill, you can do this:

    >>> bill.metadata.abbr
    'de'
    '''
    instance_key = settings.LEVEL_FIELD

    collection = db.metadata

    legislators = RelatedDocuments('Legislator',
                                   model_keys=[settings.LEVEL_FIELD],
                                   instance_key='abbreviation')

    committees = RelatedDocuments('Committee',
                                  model_keys=[settings.LEVEL_FIELD],
                                  instance_key='abbreviation')

    bills = RelatedDocuments('Bill', model_keys=[settings.LEVEL_FIELD],
                             instance_key='abbreviation')

    feed_entries = RelatedDocuments('FeedEntry',
                                    model_keys=[settings.LEVEL_FIELD],
                                    instance_key='abbreviation')

    events = RelatedDocuments('Event', model_keys=[settings.LEVEL_FIELD],
                              instance_key='abbreviation')

    report = RelatedDocument('Report', instance_key='_id')

    votes_manager = MetadataVotesManager()
    terms_manager = TermsManager()

    @classmethod
    def get_object(cls, abbr):
        '''
        This particular model needs its own constructor in order to take
        advantage of the metadata cache in billy.util, which would otherwise
        return unwrapped objects.
        '''
        obj = get_metadata(abbr)
        if obj is None:
            msg = 'No metadata found for abbreviation %r' % abbr
            raise DoesNotExist(msg)
        return cls(obj)

    @property
    def abbr(self):
        '''Return the two letter abbreviation.'''
        return self['_id']

    @property
    def most_recent_session(self):
        'Get the most recent session.'
        session = self['terms'][-1]['sessions'][-1]
        return session

    def sessions(self):
        sessions = []
        for t in self['terms']:
            for s in t['sessions']:
                sobj = {'id': s,
                        'name': self['session_details'][s]['display_name']}
                sessions.append(sobj)
        return sessions

    def display_name(self):
        return self['name']

    def get_absolute_url(self):
        return urlresolvers.reverse('region', args=[self['abbreviation']])

    def _bills_by_chamber_action(self, chamber, action, *args, **kwargs):
        bills = self.bills({'session': self.most_recent_session,
                            'chamber': chamber,
                            'actions.type': action,
                            'type': 'bill'}, *args, **kwargs)
        # Not worrying about date sorting until later.
        return bills

    def bills_introduced_upper(self, *args, **kwargs):
        return self._bills_by_chamber_action('upper', 'bill:introduced')

    def bills_introduced_lower(self, *args, **kwargs):
        return self._bills_by_chamber_action('lower', 'bill:introduced')

    def bills_passed_upper(self, *args, **kwargs):
        return self._bills_by_chamber_action('upper', 'bill:passed')

    def bills_passed_lower(self, *args, **kwargs):
        return self._bills_by_chamber_action('lower', 'bill:passed')

    @property
    def term_dict(self):
        try:
            return self._term_dict
        except AttributeError:
            term_dict = itertools.groupby(self['terms'],
                                          operator.itemgetter('name'))
            term_dict = dict((name, list(data)) for (name, data) in term_dict)
            self._term_dict = term_dict
            return term_dict

    def distinct_bill_subjects(self):
        if self.abbr not in _distinct_subjects:
            _distinct_subjects[self.abbr] = sorted(self.bills().distinct('subjects'))
        return _distinct_subjects[self.abbr]

    def distinct_action_types(self):
        if self.abbr not in _distinct_action_types:
            _distinct_action_types[self.abbr] = sorted(self.bills().distinct('actions.type'))
        return _distinct_action_types[self.abbr]

    def distinct_bill_types(self):
        if self.abbr not in _distinct_types:
            _distinct_types[self.abbr] = sorted(self.bills().distinct('type'))
        return _distinct_types[self.abbr]

    def committees_legislators(self, *args, **kwargs):
        '''Return an iterable of committees with all the
        legislators cached for reference in the Committee model.
        So do a "select_related" operation on committee members.
        '''
        committees = list(self.committees(*args, **kwargs))
        legislators = self.legislators({'active': True},
                                       fields=['full_name',
                                               settings.LEVEL_FIELD])
        _legislators = {}

        # This will be a cache of legislator objects used in
        # the committees.html template. Includes ids in each
        # legislator's _all_ids field (if it exists.)
        for obj in legislators:
            if 'all_ids' in obj:
                for _id in obj['_all_ids']:
                    _legislators[_id] = obj
            else:
                _legislators[obj['_id']] = obj
        del legislators
        for com in committees:
            com._legislators = _legislators
        return committees
