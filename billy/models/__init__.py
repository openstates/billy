'''
Notes:
This ORM approach has worked reasonably well, but because the query
interface it exposes returns raw mongo cursors, they can't be easily used with
certain parts of django's internals, like the 'queryset' class attribute on
generic view subclasses. More tinkering neeeded.
'''
import pdb
import sys
import itertools
import operator
import math
import urlparse
import datetime
import logging
import collections

from pymongo import Connection
from pymongo.son_manipulator import SONManipulator

from django.core import urlresolvers
from billy.conf import settings as billy_settings
from billy.utils import metadata as get_metadata

from billy.web.public.viewdata import blurbs


db = Connection(host=billy_settings.MONGO_HOST, port=billy_settings.MONGO_PORT)
db = getattr(db, billy_settings.MONGO_DATABASE)

DEBUG = 1  # django_settings.DEBUG
logger = logging.getLogger('billy.models')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
formatter = logging.Formatter('[%(name)s] %(asctime)s - %(message)s',
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)
query_log_template = 'Query: db.{0}.{1}({2}, {3}, {4})'


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(itertools.islice(iterable, n))


def get_model(classname, this_module=sys.modules[__name__]):
    '''
    Helper to enable RelatedDocuments to reference models by name (string)
    rather than passing the actual class, which may be defined later in
    the module.
    '''
    return getattr(this_module, classname)

# ---------------------------------------------------------------------------
# Base classes and errors for model objects.


class ReadOnlyAttribute(object):
    def __set__(self, instance, value):
        raise AttributeError


class ModelDefinitionError(Exception):
    '''Raised if there's a problem with a model definition.'''
    pass


class DoesNotExist(Exception):
    pass


class Document(dict):
    '''
    This base class represents a MongoDB document.

    Methods that return related documents from other collections,
    like `state.legislators` or `bill.sponsors` should return a cursor
    object that can be limited, sorted, counted, etc.

    Methods that dereference embedded objects into list of objects from
    other collections, such as a list of bill sponsors deferenced into actual
    legislator documents, should have a name like "legislator_objects" to
    document what's happening and avoid naming clashes.
    '''

    # Each subclass represents a document from a specific collection.
    collection = None

    @property
    def id(self):
        '''
        Alias '_id' to avoid django template complaints about names
        with leading underscores.
        '''
        return self['_id']

    @property
    def metadata(self):
        '''
        For collections like reports and bills that have a 'state' key.
        '''
        try:
            return Metadata.get_object(self['state'])
        except KeyError:
            # This is the special case of Reports, where the _id
            # is the state abbreviation.
            return Metadata.get_object(self['_id'])

    @property
    def state(self):
        '''Sometimes calling metadata "state" is clearer, BUT if the
        document also has a key named 'state', django's templating
        engine will use that instead, so using 'metadata' is safer.'''
        return self.metadata

    def chamber_name(self):
        chamber = self['chamber']
        if chamber == 'joint':
            return 'Joint'
        return self.metadata['%s_chamber_name' % self['chamber']]

    @property
    def subdocument(self):
        '''This property enables enables this:

        class Bill(Document):

            def version_objects(self):
                for data in self['versions']:
                    yield self.subdocument(data)

        bill = db.bills.find_one()
        version = next(bill.version_objects())
        assert version.bill is bill
        '''
        selfname = self.__class__.__name__.lower()

        class Subdocument(dict):

            def __repr__(subdoc):
                args = (selfname, dict.__repr__(subdoc))
                return '%s.Subdocument(%r)' % args

        setattr(Subdocument, selfname, self)

        return Subdocument


class RelatedDocument(ReadOnlyAttribute):
    '''
    Set an instance of this discriptor as a class attribute on a
    Document subclass, and when accessed from a document it will deference
    the related document's _id and return the related object.

    You can pass additional find_one arguments and limit the returned
    field, for example.
    '''
    def __init__(self, model, instance_key=None):
        self.model = model
        self.instance_key = instance_key

    def __get__(self, instance, type_=None):

        self.instance = instance

        model = self.model
        if isinstance(model, basestring):
            model = self.model = get_model(model)

        instance_key = getattr(self, 'instance_key', None)
        if instance_key is None:
            try:
                instance_key = model.instance_key
            except KeyError:
                msg = ("Can't dereference: model %r has no instance_key "
                       "defined.")
                raise ModelDefinitionError(msg % model)
            else:
                self.instance_key = instance_key

        try:
            self.model_id = instance[self.instance_key]
        except KeyError:
            msg = "Can't dereference: instance %r has no key %r."
            raise ModelDefinitionError(msg % (instance, instance_key))

        return self

    def __call__(self, extra_spec={}, *args, **kwargs):
        spec = {'_id': self.model_id}
        spec.update(extra_spec)
        if DEBUG:
            msg = '{0}.{1}({2}, {3}, {4})'.format(self.model.collection.name,
                                            'find_one', spec, args, kwargs)
            logger.debug(msg)

        obj = self.model.collection.find_one(spec, *args, **kwargs)
        if obj is None:
            msg = 'No %s found for %r' % (self.model.collection.name,
                                          (spec, args, kwargs))

            raise DoesNotExist(msg)
        return obj


class RelatedDocuments(ReadOnlyAttribute):
    '''
    Set an instance of this descriptor as class attribute on a Document
    subclass, and when accessed on an instance, it will return
    a cursor of all objects that reference this instance's id using
    the key `model_key`. For example, this could be used to get all
    "legislator" documents for a given state's metadata.
    '''
    def __init__(self, model, model_keys, instance_key='_id',
                 sort=None, model_keys_operator='$or',
                 default_spec_instance_keys=None,
                 extra_spec=None):
        '''
        :param mode: model class of the related document
        :param model_keys: keys to use in generating mongo query spec from
            model data
        :param instance_key: instance key that model[model_key] is mapped to
            in the default mongo query spec
        :param sort: default mongo query sort spec, like [("field", direction)]
        :param model_keys_operator: if multiple model_keys are given, the
            boolean mongo query to relate them, like $and, $or, etc.
        :param default_spec_instance_keys: extra instance keys used to populate
            the default mongo query spec with, like 'state' and 'session'.
            Useful in constraining potentially brutal queries.
        '''
        self.model = model
        self.instance_key = instance_key
        self.model_keys = model_keys
        self.sort = sort
        self.model_keys_operator = model_keys_operator

    def __get__(self, instance, type_=None, *args, **kwargs):

        model = self.model
        if isinstance(model, basestring):
            model = self.model = get_model(model)

        self.instance_val = instance[self.instance_key]

        return self

    def __call__(self, extra_spec={}, *args, **kwargs):

        # Create the default spec.
        spec = dict(zip(self.model_keys,
                        itertools.repeat(self.instance_val)))

        # If multiple model keys were defined, apply boolean mongo query syntax.
        if 1 < len(spec):
            spec = [{k: v} for (k, v) in spec.items()]
            spec = {self.model_keys_operator: spec}

        # Add any extra spec.
        spec.update(extra_spec)

        # Add any default sorting behaviour.
        if 'sort' not in kwargs:
            _sort = self.sort
            if _sort is not None:
                kwargs.update(sort=_sort)

        if DEBUG:
            msg = '{0}.{1}({2}, {3}, {4})'.format(self.model.collection.name,
                                                 'find', spec, args, kwargs)
            logger.debug(msg)
        return self.model.collection.find(spec, *args, **kwargs)


class Subdocument(dict):

    @classmethod
    def fromdict(cls, dict_, parent_doc, parent_name):
        '''
        :param dict: the dictionary subdocument, like the `votes` dict
            on a bill object.
        :param parent_doc: the document/dict in which the subdoc is a value, like
            the bill document in the case of a votes list.
        "param parent_name:
        '''
        subdoc = cls(dict_)
        subdoc.parent = parent_doc
        setattr(subdoc, parent_name, parent_doc)
        return subdoc


class AttrManager(object):
    '''A class providing ways to associate methods with a particular attribute
    of an object.

    class SomeDoc(Document):
        sponsors = SponsorsManager()

    class SponsorsManager(AttrManager):
        def prime(self):
            for sponsor in self:
                if sponsor['type'] == 'primary:
                    return sponsor
    '''

    @property
    def _keyname(self):
        keyname = self.__class__.__name__
        return keyname.lower().replace('manager', '')

    def __iter__(self):
        try:
            wrapper = self.wrapper
        except AttributeError:
            msg = 'AttrManager %r must define a wrapper class.'
            raise ModelDefinitionError(msg)

        for obj in self.inst[self._keyname]:
            yield wrapper(obj)

    def __get__(self, instance, type_=None, *args, **kwargs):
        self.inst = instance
        return self


# ---------------------------------------------------------------------------
# Model definitions.
class FeedEntry(Document):
    collection = db.feed_entries

    def __init__(self, *args, **kw):
        super(FeedEntry, self).__init__(*args, **kw)
        self._process()

    def _process(self):
        '''Mutate the feed entry with hyperlinked entities. Add tagging
        data and other template context values, including source.
        '''
        entity_types = {'L': 'legislator',
                        'C': 'committee',
                        'B': 'bill'}
        entry = self

        summary = entry['summary']
        entity_strings = entry['entity_strings']
        entity_ids = entry['entity_ids']
        state = entry['state']

        _entity_strings = []
        _entity_ids = []
        _entity_urls = []
        _done = []
        if entity_strings:
            for entity_string, _id in zip(entity_strings, entity_ids):
                if entity_string in _done:
                    continue
                else:
                    _done.append(entity_string)
                    _entity_strings.append(entity_string)
                    _entity_ids.append(_id)
                entity_type = entity_types[_id[2]]
                url = urlresolvers.reverse(entity_type, args=[state, _id])
                _entity_urls.append(url)
                summary = summary.replace(entity_string,
                                '<b><a href="%s">%s</a></b>' % (url, entity_string))
            entity_data = zip(_entity_strings, _entity_ids, _entity_urls)
            entry['summary'] = summary
            entry['entity_data'] = entity_data

        entry['id'] = entry['_id']
        urldata = urlparse.urlparse(entry['link'])
        entry['source'] = urldata.scheme + urldata.netloc
        entry['host'] = urldata.netloc
        del entry['published']

    def published(self):
        return datetime.datetime.fromtimestamp(self['published_parsed'])


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator', instance_key='leg_id')


class CommitteeMemberManager(AttrManager):

    def __iter__(self):
        for obj in self.inst['members']:
            if 'leg_id' in obj:
                if DEBUG:
                    msg = '{0}.{1}({2}, {3}, {4})'.format(
                                'legislators',
                                'find_one', {'_id': obj['leg_id']}, (), {})
                    logger.debug(msg)
                legislator = db.legislators.find_one({'_id': obj['leg_id']})
                yield obj, legislator


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


class Role(dict):

    def is_committee(self):
        return ('committee' in self)

    def committee_name(self):
        name = self['committee']
        if 'subcommittee' in self:
            sub = self['subcommittee']
            if sub:
                name = '%s - %s' % (name, sub)
        return name


class RolesManager(AttrManager):
    wrapper = Role


class Legislator(Document):

    collection = db.legislators
    istance_key = 'leg_id'

    committees = RelatedDocuments('Committee', model_keys=['members.leg_id'])
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])
    roles_manager = RolesManager()

    class VotesManager(object):
        def __iter__(self):
            inst = self.inst
            _id = inst['_id']
            for bill in inst.state.bills():
                for vote in bill.votes_manager:
                    for k in ['yes_votes', 'no_votes', 'other_votes']:
                        for voter in vote[k]:
                            if voter['leg_id'] == _id:
                                yield vote

        def __get__(self, instance, type_=None, *args, **kwargs):
            self.inst = instance
            return self
    votes_manager = VotesManager()
    # def votes_manager(self):
    #     _id = self['_id']
    #     for bill in self.state.bills():
    #         for vote in bill.votes_manager:
    #             for k in ['yes_votes', 'no_votes', 'other_votes']:
    #                 for voter in vote[k]:
    #                     if voter['leg_id'] == _id:
    #                         yield vote

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


class Sponsor(dict):
    legislator = RelatedDocument('Legislator', instance_key='leg_id')


class SponsorsManager(AttrManager):

    def __iter__(self):
        '''Another unoptimized method that ultimately hits
        mongo once for each sponsor.'''
        for spons in self.inst['sponsors']:
            yield Sponsor(spons)

    def primary_list(self):
        'Return the first primary sponsor on the bill.'
        for sponsor in self.inst['sponsors']:
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


class Action(Subdocument):

    def chamber_name(self):
        chamber = self.bill['chamber']
        meta = self.bill.state
        return meta['%s_chamber_name' % chamber]


class ActionsManager(AttrManager):

    def __iter__(self):
        bill = self.inst
        for action in reversed(bill['actions']):
            yield Action.fromdict(action, bill, 'bill')

    def _bytype(self, action_type, action_spec=None):
        '''Return the most recent date on which action_type occurred.
        Action spec is a dictionary of key-value attrs to match.'''
        for action in reversed(self.inst['actions']):
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


class Vote(Subdocument):

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


class Bill(Document):

    collection = db.bills

    sponsors_manager = SponsorsManager()
    actions_manager = ActionsManager()

    class VotesManager(AttrManager):
        '''
        maybe return self.Subdocument(mydict)
        '''
        def __iter__(self):
            inst = self.inst
            for vote in inst['votes']:
                yield Vote.fromdict(
                    vote, parent_doc=inst, parent_name='bill')

        def has_votes(self):
            return bool(self.inst['votes'])

    votes_manager = VotesManager()

    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    def version_objects(self):
        cls = self.subdocument
        for obj in self['versions']:
            yield cls(obj)

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

    @property
    def state(self):
        return self.metadata

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
        chamber = self['chamber']
        actions = self.actions_type_dict.get('bill:introduced')
        if actions:
            for action in actions:
                if chamber in action['actor']:
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
        actions = self.actions_type_dict.get('upper', 'governor:signed')
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

            ('stage4', 'Governor Signs', 'date_passed_upper'),
            ]
        for stage, text, method in data:
            print stage, text, getattr(self, method)()
            yield stage, text, getattr(self, method)()


class Metadata(Document):
    '''
    The metadata can also be thought as the "state" (i.e., Montana, Texas)
    when it's an attribute of another object. For example, if you have a
    bill, you can do this:

    >>> bill.state.abbr
    'de'
    '''
    instance_key = 'state'

    class VotesManager(AttrManager):
        def __iter__(self):
            for bill in self.inst.bills():
                for vote in bill.votes_manager:
                        yield vote

    collection = db.metadata

    legislators = RelatedDocuments(Legislator, model_keys=['state'],
                                   instance_key='abbreviation')

    committees = RelatedDocuments(Committee, model_keys=['state'],
                                  instance_key='abbreviation')

    bills = RelatedDocuments(Bill, model_keys=['state'],
                             instance_key='abbreviation')

    feed_entries = RelatedDocuments(FeedEntry, model_keys=['state'],
                                    instance_key='abbreviation')

    votes_manager = VotesManager()

    @classmethod
    def get_object(cls, abbr):
        '''
        This particular model need its own constructor in order to take
        advantage of the metadata cache in billy.util, which would otherwise
        return unwrapped objects.
        '''
        obj = get_metadata(abbr)
        if obj is None:
            msg = 'No metatdata found for abbreviation %r' % abbr
            raise DoesNotExist(msg)
        return cls(obj)

    @property
    def abbr(self):
        '''Return the state's two letter abbreviation.'''
        return self['_id']

    @property
    def most_recent_session(self):
        'Get the most recent session for this state.'
        session = self['terms'][-1]['sessions'][-1]
        return session


class Report(Document):

    collection = db.reports
    #metadata = RelatedDocument('Metadata', instance_key='_id')

    def session_link_data(self):
        '''
        An iterable of tuples like
        ('821', '82nd Legislature, 1st Called Session')
        '''
        session_details = self.metadata['session_details']
        for s in self['bills']['sessions']:
            yield (s, session_details[s]['display_name'])


# ---------------------------------------------------------------------------
# Setup the SON manipulator.
_collection_model_dict = {}

models_list = [
    FeedEntry,
    Metadata,
    Report,
    Bill,
    Legislator,
    Committee,
    ]

for m in models_list:
    _collection_model_dict[m.collection.name] = m


class Transformer(SONManipulator):
    def transform_outgoing(self, son, collection,
                           mapping=_collection_model_dict):
        try:
            return mapping[collection.name](son)
        except KeyError:
            return son

db.add_son_manipulator(Transformer())


if __name__ == "__main__":
    xx = Metadata.get_object('ca')
    legs = xx.legislators({'full_name': 1})
    cc = db.committees.find_one()
    qq = cc.members_objects()
    ww = qq[0].legislator_object()

    pdb.set_trace()
