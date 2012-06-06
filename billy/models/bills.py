import math
import operator
import collections

from django.core import urlresolvers

from .base import (db, Document, RelatedDocument, RelatedDocuments,
                   ListManager, DictManager, AttrManager, take, DEBUG, logger)
from .metadata import Metadata


class Sponsor(dict):
    legislator = RelatedDocument('Legislator', instance_key='leg_id')


class SponsorsManager(AttrManager):

    def __iter__(self):
        '''Another unoptimized method that ultimately hits
        mongo once for each sponsor.'''
        for spons in self.document['sponsors']:
            yield Sponsor(spons)

    def primary_list(self):
        'Return the first primary sponsor on the bill.'
        for sponsor in self.document['sponsors']:
            if sponsor['type'] == 'primary':
                yield Sponsor(sponsor)

    def first_primary(self):
        try:
            return next(self.primary_list())
        except StopIteration:
            return

    def first_five(self):
        'views.bill'
        return take(5, self)

    def first_five_remainder(self):
        len_ = len(self.document['sponsors'])
        if 5 < len_:
            return len_ - 5


class Action(dict):

    def actor_name(self):
        actor = self['actor']
        meta = self.bill.metadata
        for s in ('upper', 'lower'):
            if s in actor:
                chamber_name = meta['%s_chamber_name' % s]
                return actor.replace(s, chamber_name)
        return actor.title()

    @property
    def bill(self):
        return self.manager.document


class ActionsManager(ListManager):
    wrapper = Action

    def __iter__(self):
        for action in reversed(self.bill['actions']):
            yield self._wrapper(action)

    def _bytype(self, action_type, action_spec=None):
        '''Return the most recent date on which action_type occurred.
        Action spec is a dictionary of key-value attrs to match.'''
        for action in reversed(self.bill['actions']):
            if action_type in action['type']:
                for k, v in action_spec.items():
                    if action[k] == v:
                        yield action

    def _bytype_latest(self, action_type, action_spec=None):
        actions = self._bytype(action_type, action_spec)
        try:
            return next(actions)
        except StopIteration:
            return

    def latest_passed_upper(self):
        return self._bytype_latest('bill:passed', {'actor': 'upper'})

    def latest_passed_lower(self):
        return self._bytype_latest('bill:passed', {'actor': 'lower'})

    def latest_introduced_upper(self):
        return self._bytype_latest('bill:introduced', {'actor': 'upper'})

    def latest_introduced_lower(self):
        return self._bytype_latest('bill:introduced', {'actor': 'lower'})


class BillVote(DictManager):

    def _total_votes(self):
        return self['yes_count'] + self['no_count'] + self['other_count']

    def _ratio(self, key):
        '''Return the yes/total ratio as a percetage string
        suitable for use as as css attribute.'''
        total = float(self._total_votes())
        return math.floor(self[key] / total * 100)

    def yes_ratio(self):
        return self._ratio('yes_count')

    def no_ratio(self):
        return self._ratio('no_count')

    def other_ratio(self):
        return self._ratio('other_count')

    def _vote_legislators(self, yes_no_other):
        '''This function will hit the database individually
        to get each legislator object. Good if the number of
        voters is small (i.e., committee vote), but possibly
        bad if it's high (full roll call vote).'''
        id_getter = operator.itemgetter('leg_id')
        for _id in map(id_getter, self['%s_votes' % yes_no_other]):
            if DEBUG:
                msg = '{0}.{1}({2}, {3}, {4})'.format(
                    'legislators', 'find_one', {'_id': _id}, (), {})
                logger.debug(msg)
            obj = db.legislators.find_one({'_id': _id})
            if obj is None:
                msg = 'No legislator found with id %r' % _id
                continue
                #raise DoesNotExist(msg)
            yield obj

    def yes_vote_legislators(self):
        return self._vote_legislators('yes')

    def no_vote_legislators(self):
        return self._vote_legislators('no')

    def other_vote_legislators(self):
        return self._vote_legislators('other')

    def index(self):
        return self.bill['votes'].index(self)


class BillVotesManager(ListManager):
        wrapper = BillVote
        keyname = 'votes'

        def has_votes(self):
            return bool(self.bill['votes'])


class Bill(Document):

    collection = db.bills

    sponsors_manager = SponsorsManager()
    actions_manager = ActionsManager()
    votes_manager = BillVotesManager()

    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def get_absolute_url(self):
        return urlresolvers.reverse('bill', args=[self['abbreviation',
                                                       self.id]])

    def session_details(self):
        metadata = self.metadata
        return metadata['session_details'][self['session']]

    def most_recent_action(self):
        return self['actions'][-1]

    @property
    def chamber_name(self):
        '''"lower" --> "House of Representatives"'''
        return self.metadata['%s_chamber_name' % self['chamber']]

    @property
    def other_chamber(self):
        return {'upper': 'lower',
                'lower': 'upper'}[self['chamber']]

    @property
    def other_chamber_name(self):
        return self.metadata['%s_chamber_name' % self.other_chamber]

    def type_string(self):
        return self['_type']

    # Bill progress properties
    @property
    def actions_type_dict(self):
        typedict = getattr(self, '_actions_type_dict', None)
        if typedict is None:
            typedict = collections.defaultdict(list)
            for action in self['actions']:
                for type_ in action['type']:
                    typedict[type_].append(action)
            setattr(self, '_actions_type_dict', typedict)
        return dict(typedict)

    def date_introduced(self):
        '''Currently returns the earliest date the bill was introduced
        in either chamber.
        '''
        actions = self.actions_type_dict.get('bill:introduced', [])
        actions = sorted(actions, key=operator.itemgetter('date'))
        if actions:
            for action in actions:
                return action['date']

    def date_passed_lower(self):
        chamber = 'lower'
        actions = self.actions_type_dict.get('bill:passed')
        if actions:
            for action in actions:
                if chamber in action['actor']:
                    return action['date']

    def date_passed_upper(self):
        chamber = 'upper'
        actions = self.actions_type_dict.get('bill:passed')
        if actions:
            for action in actions:
                if chamber in action['actor']:
                    return action['date']

    def date_signed(self):
        actions = self.actions_type_dict.get('governor:signed')
        if actions:
            return actions[-1]['date']

    def progress_data(self):

        data = [
            ('stage1', 'Introduced', 'date_introduced'),

            ('stage2',
             'Passed ' + self.chamber_name,
             'date_passed_' + self['chamber']),

            ('stage3',
             'Passed ' + self.other_chamber_name,
             'date_passed_' + self.other_chamber),

            ('stage4', 'Governor Signs', 'date_signed'),
            ]
        for stage, text, method in data:
            yield stage, text, getattr(self, method)()
