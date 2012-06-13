import math
import operator
import collections

from django.core import urlresolvers
from django.template.defaultfilters import slugify
import pyes

from billy.conf import settings
from billy.utils import parse_param_dt

from .base import (db, Document, RelatedDocument, RelatedDocuments,
                   ListManager, DictManager, AttrManager, take, DEBUG, logger)
from .metadata import Metadata

elasticsearch = pyes.ES(settings.ELASTICSEARCH_HOST,
                        settings.ELASTICSEARCH_TIMEOUT)


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

    def action_display(self):
        '''The action text, with any hyperlinked related entities.'''
        if '+actor_collection' in self:
            collection = getattr(db, self['+actor_collection'])
            actor = collection.find_one(self['+actor_id'])
            actor_url = actor.get_absolute_url()
            actor_text = self['+actor_text']
            action = self['action'].replace(actor_text,
                '<a href=%s>%s</a>' % (actor_url, actor_text))
            return action
        else:
            return self['action']


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
        try:
            return math.floor(self[key] / total * 100)
        except ZeroDivisionError:
            return float(0)

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

    def get_absolute_url(self):
        text = '%s--%s' % (self.bill['bill_id'],
                               self['date'].strftime('%m-%d-%Y'))
        slug = slugify(text)
        url = urlresolvers.reverse('vote',
            args=[self.bill['state'], self.bill['_id'], self.index()])
        return '%s%s/' % (url, slug)


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
        url = urlresolvers.reverse('bill', args=[self['state'], self.id])
        slug = slugify(self['bill_id'])
        return '%s%s/' % (url, slug)

    def session_details(self):
        metadata = self.metadata
        return metadata['session_details'][self['session']]

    def most_recent_action(self):
        if self['actions']:
            return self['actions'][-1]
        else:
            return {}

    def events(self):
        return db.events.find({"related_bills.bill_id": self['_id']})

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

    @staticmethod
    def search(query=None, state=None, chamber=None, subjects=None,
               bill_id=None, bill_id__in=None, search_window=None,
               updated_since=None, sponsor_id=None, bill_fields=None):

        _filter = {}
        for key, value in [('state', state),
                            ('chamber', chamber),
                            ('subjects', subjects)]:
            if value is not None:
                _filter[key] = value

        if search_window:
            if search_window == 'session':
                _filter['_current_session'] = True
            elif search_window == 'term':
                _filter['_current_term'] = True
            elif search_window.startswith('session:'):
                _filter['session'] = search_window.split('session:')[1]
            elif search_window.startswith('term:'):
                _filter['_term'] = search_window.split('term:')[1]
            elif search_window == 'all':
                pass
            else:
                raise ValueError('invalid search_window. valid choices are '
                                 ' "term", "session", "all"')
        if updated_since:
            try:
                _filter['updated_at'] = {'$gte': parse_param_dt(updated_since)}
            except ValueError:
                raise ValueError('invalid updated_since parameter. '
                                 'please supply date in YYYY-MM-DD format')
        if sponsor_id:
            _filter['sponsors.leg_id'] = sponsor_id

        # process full-text query
        if query:
            query = {"query_string": {"fields": ["text", "title"],
                                      "default_operator": "AND",
                                      "query": query}}
            search = pyes.Search(query, fields=[])

            # take terms from mongo query
            es_terms = []
            if 'state' in _filter:
                es_terms.append(pyes.TermFilter('state',
                                                _filter.pop('state')))
            if 'session' in _filter:
                es_terms.append(pyes.TermFilter('session',
                                                _filter.pop('session')))
            if 'chamber' in _filter:
                es_terms.append(pyes.TermFilter('chamber',
                                                _filter.pop('chamber')))
            if 'subjects' in _filter:
                es_terms.append(pyes.TermFilter('subjects',
                                           _filter.pop('subjects')['$all']))
            if 'sponsors.leg_id' in _filter:
                es_terms.append(pyes.TermFilter('sponsors',
                                                _filter.pop('sponsors.leg_id')))

            # add terms
            if es_terms:
                search.filter = pyes.ANDFilter(es_terms)

            # page size is a guess, could use tweaks
            es_result = elasticsearch.search(search, search_type='scan',
                                             scroll='3m', size=250)
            doc_ids = [r.get_id() for r in es_result]
            _filter['versions.doc_id'] = {'$in': doc_ids}

        # return query
        return db.bills.find(_filter, bill_fields)
