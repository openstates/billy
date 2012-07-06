import math
import operator
import collections

from django.core import urlresolvers
from django.template.defaultfilters import slugify
import pyes

from billy.conf import settings
from billy.utils import parse_param_dt

from .base import (db, Document, RelatedDocument, RelatedDocuments,
                   ListManager, AttrManager, take)
from .metadata import Metadata
from .utils import CachedAttribute

elasticsearch = pyes.ES(settings.ELASTICSEARCH_HOST,
                        settings.ELASTICSEARCH_TIMEOUT)


class Sponsor(dict):
    legislator = RelatedDocument('Legislator', instance_key='leg_id')


class SponsorsManager(AttrManager):

    def __iter__(self):
        '''Lazily fetch all legislator objects from the db.
        '''
        sponsors = self.bill['sponsors']
        try:
            legislators = self._legislators
        except AttributeError:
            ids = filter(None, map(operator.itemgetter('leg_id'), sponsors))
            legislators = db.legislators.find({'_id': {'$in': ids}})
            legislators = dict((obj['_id'], obj) for obj in legislators)
            self._legislators = legislators
        for sponsor in sponsors:
            if sponsor['leg_id'] is not None:
                legislator = legislators[sponsor['leg_id']]
                legislator.update(sponsor)
                yield legislator
            else:
                yield sponsor

    def primary_list(self):
        'Return the first primary sponsor on the bill.'
        for sponsor in self:
            if sponsor['type'] == 'primary':
                yield sponsor

    def first_primary(self):
        try:
            return next(self.primary_list())
        except StopIteration:
            return

    def first_fifteen(self):
        'views.bill'
        return take(15, self)

    def first_fifteen_remainder(self):
        len_ = len(self.document['sponsors'])
        if 15 < len_:
            return len_ - 15


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


class BillVote(Document):

    collection = db.votes

    bill = RelatedDocument('Bill')

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

    @CachedAttribute
    def _legislator_objects(self, fields=['first_name', 'last_name',
                                          'party', 'district']):
        '''A cache of dereferenced legislator objects.
        '''
        kwargs = {}
        if fields is not None:
            kwargs['fields'] = fields
        id_getter = operator.itemgetter('leg_id')
        ids = []
        for k in ('yes', 'no', 'other'):
            ids.extend(map(id_getter, self[k + '_votes']))
        objs = db.legislators.find({'_id': {'$in': ids}}, **kwargs)
        objs = dict((obj['_id'], obj) for obj in objs)
        return objs

    @CachedAttribute
    def legislator_vote_value(self):
        '''If this vote was accessed through the legislator.votes_manager,
        return the value of this legislator's vote.
        '''
        if not hasattr(self, 'legislator'):
            msg = ('legislator_vote_value can only be called '
                   'from a vote accessed by legislator.votes_manager.')
            raise ValueError(msg)
        leg_id = self.legislator.id
        for k in ('yes', 'no', 'other'):
            for leg in self[k + '_votes']:
                if leg['leg_id'] == leg_id:
                    return k

    def _vote_legislators(self, yes_no_other):
        '''Return all legislators who votes yes/no/other on this bill.
        '''
        id_getter = operator.itemgetter('leg_id')
        ids = map(id_getter, self['%s_votes' % yes_no_other])
        return map(self._legislator_objects.get, ids)

    def yes_vote_legislators(self):
        return self._vote_legislators('yes')

    def no_vote_legislators(self):
        return self._vote_legislators('no')

    def other_vote_legislators(self):
        return self._vote_legislators('other')

    def get_absolute_url(self):
        bill_id = self['bill_id']
        text = '%s--%s' % (bill_id, self['date'].strftime('%m-%d-%Y'))
        slug = slugify(text)
        url = urlresolvers.reverse(
            'vote', args=[self['state'], self['_id']])
        url = '%s%s/' % (url, slug)
        return url


class Bill(Document):

    collection = db.bills
    instance_key = 'bill_id'

    sponsors_manager = SponsorsManager()
    actions_manager = ActionsManager()
    votes_manager = RelatedDocuments('BillVote', model_keys=['bill_id'])

    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    @property
    def metadata(self):
        return Metadata.get_object(self['state'])

    def get_absolute_url(self):
        url = urlresolvers.reverse('bill', args=[self['state'], self.id])
        slug = slugify(self['bill_id'])
        url = '%s%s/' % (url, slug)
        return url

    def get_admin_url(self):
        return urlresolvers.reverse('bill', args=[self['state'], self.id])

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
        return self['type'][0]

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
        return self['action_dates']['first']

    def date_passed_lower(self):
        return self['action_dates']['passed_lower']

    def date_passed_upper(self):
        return self['action_dates']['passed_upper']

    def date_signed(self):
        return self['action_dates']['signed']

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
               updated_since=None, sponsor_id=None, bill_fields=None,
               status=None, type_=None, session=None):
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

        if status:
            # Status is slightly different: it's a dict like--
            # {'action_dates.signed': {'$ne': None}}
            _filter.update(**status)

        if type_:
            _filter['type'] = type_

        if session:
            _filter['session'] = session

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
