import pdb
import sys
import itertools
import operator
import math
import urlparse

from pymongo import Connection
from pymongo.son_manipulator import SONManipulator

from django.core import urlresolvers

from billy.conf import settings
from billy.utils import metadata as get_metadata

from billy.web.public.viewdata import blurbs


db = Connection(host=settings.MONGO_HOST, port=settings.MONGO_PORT)
db = getattr(db, settings.MONGO_DATABASE)


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
            return Metadata.get_object(self['_id'])

    @property
    def state(self):
        '''Sometimes calling metadata "state" is clearer, BUT if the
        document also has a key named 'state', django's templating
        engine will use that instead, so using 'metadata' is safer.'''
        return self.metadata


class RelatedDocument(ReadOnlyAttribute):
    '''
    Set an instance of this discriptor as a class attribute on a
    Document subclass, and when accessed from a document it will deference
    the related document's _id and return the related object.

    You can pass additional find_one arguments and limit the returned
    field, for example.
    '''
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, type_=None):

        self.instance = instance

        model = self.model
        if isinstance(model, basestring):
            model = self.model = get_model(model)

        try:
            model_fk_string = model.foreign_key_string
            self.model_fk_string = model_fk_string

        except KeyError:
            msg = ("Can't dereference: model %r has no foreign_key_string "
                   "defined.")
            raise ModelDefinitionError(msg % model)

        try:
            self.model_id = instance[model_fk_string]
        except KeyError:
            msg = "Can't dereference: model %r has no key %r."
            raise ModelDefinitionError(msg % (model, model_fk_string))

        return self

    def __call__(self, extra_spec={}, *args, **kwargs):
        spec = {'_id': self.model_id}
        spec.update(extra_spec)
        return self.model.collection.find_one(spec, *args, **kwargs)


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

        print 'running %r, %r, %r' % (spec, args, kwargs)
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


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator')


class Committee(Document):

    collection = db.committees
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    def members_objects(self):
        '''
        Return a list of CommitteeMember objects.
        '''
        return map(CommitteeMember, self['members'])

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
    foreign_key_string = 'leg_id'

    committees = RelatedDocuments('Committee', model_keys=['members.leg_id'])
    sponsored_bills = RelatedDocuments('Bill', model_keys=['sponsors.leg_id'])
    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])
    roles_manager = RolesManager()

    def votes(self):
        _id = self['_id']
        for bill in self.state.bills():
            for vote in bill.votes_manager:
                for k in ['yes_votes', 'no_votes', 'other_votes']:
                    for voter in vote[k]:
                        if voter['leg_id'] == _id:
                            yield vote

    def votes_3_sorted(self):
        _id = self['_id']
        votes = self.votes()
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

    def chamber_name(self):
        return self.state['%s_chamber_name' % self['chamber']]

    def primary_sponsored_bills(self):
        return self.sponsored_bills({'sponsors.type': 'primary'})


class Sponsor(dict):
    legislator = RelatedDocument('Legislator')


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
            yield db.legislators.find_one({'_id': _id})

    def yes_vote_legislators(self):
        return self._vote_legislators('yes')

    def no_vote_legislators(self):
        return self._vote_legislators('no')

    def other_vote_legislators(self):
        return self._vote_legislators('other')


class VotesManager(AttrManager):

    def __iter__(self):
        inst = self.inst
        for vote in inst['votes']:
            yield Vote.fromdict(
                vote, parent_doc=inst, parent_name='bill')


class Bill(Document):

    collection = db.bills

    sponsors_manager = SponsorsManager()
    actions_manager = ActionsManager()
    votes_manager = VotesManager()

    feed_entries = RelatedDocuments('FeedEntry', model_keys=['entity_ids'])

    def session_details(self):
        metadata = self.metadata
        return metadata['session_details'][self['session']]

    def most_recent_action(self):
        return self['actions'][-1]

    def chamber_name(self):
        '''"lower" --> "House of Representatives"'''
        return self.metadata['%s_chamber_name' % self['chamber']]

    @property
    def state(self):
        return self.metadata


class Metadata(Document):
    '''
    The metadata can also be thought as the "state" (i.e., Montana, Texas)
    when it's an attribute of another object. For example, if you have a
    bill, you can do this:

    >>> bill.state.abbr
    'de'
    '''
    collection = db.metadata

    legislators = RelatedDocuments(Legislator, model_keys=['state'],
                                   instance_key='abbreviation')

    committees = RelatedDocuments(Committee, model_keys=['state'],
                                  instance_key='abbreviation')

    bills = RelatedDocuments(Bill, model_keys=['state'],
                             instance_key='abbreviation')

    feed_entries = RelatedDocuments(FeedEntry, model_keys=['state'],
                                    instance_key='abbreviation')

    @classmethod
    def get_object(cls, abbr):
        '''
        This particular model need its own constructor in order to take
        advantage of the metadata cache in billy.util, which would otherwise
        return unwrapped objects.
        '''
        return cls(get_metadata(abbr))

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
