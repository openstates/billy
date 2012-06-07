import sys
import copy
import logging
import itertools

from pymongo import Connection

from billy.conf import settings as billy_settings


# TODO: put this in a util file
def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(itertools.islice(iterable, n))

# get db connection
db = Connection(host=billy_settings.MONGO_HOST, port=billy_settings.MONGO_PORT)
db = getattr(db, billy_settings.MONGO_DATABASE)

# configure logging (FIXME)
DEBUG = 1  # django_settings.DEBUG
logger = logging.getLogger('billy.models')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
formatter = logging.Formatter('[%(name)s] %(asctime)s - %(message)s',
                              datefmt='%H:%M:%S')
ch.setFormatter(formatter)
logger.addHandler(ch)
query_log_template = 'Query: db.{0}.{1}({2}, {3}, {4})'

_model_registry = {}
_model_registry_by_collection = {}

def get_model(classname):
    '''
    Helper to enable RelatedDocuments to reference models by name (string)
    rather than passing the actual class, which may not be defined in the
    module.
    '''
    return _model_registry[classname]

class ModelBase(type):
    def __new__(meta, classname, bases, classdict):
        cls = type.__new__(meta, classname, bases, classdict)

        if bases[0] != dict:
            _model_registry[classname] = cls
            _model_registry_by_collection[cls.collection.name] = cls

        return cls

class ReadOnlyAttribute(object):
    ''' ensure that an attribute can't be set '''
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

    __metaclass__ = ModelBase

    # Each subclass represents a document from a specific collection.
    collection = None

    # The attribute name that should point to this object in related
    # documents.
    related_name = None

    def __init__(self, *args, **kwargs):
        super(Document, self).__init__(*args, **kwargs)

        # This dictionary enables managed key/values and any objects
        # they contain to easily reference the top-level document.
        self.context = {}

    @property
    def related_name(self):
        try:
            return self._related_name
        except:
            related_name = self.__class__.__name__.lower()
            return related_name

    @property
    def id(self):
        '''
        Alias '_id' to avoid django template complaints about names
        with leading underscores.
        '''
        return self['_id']

    def chamber_name(self):
        chamber = self['chamber']
        if chamber == 'joint':
            return 'Joint'
        return self.metadata['%s_chamber_name' % self['chamber']]


class AttrManager(object):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def _wrapper(self, rubber_stamp=lambda x: x):
        '''Subclasses define a wrapper (or not).
        '''
        return getattr(self, 'wrapper', rubber_stamp)

    def __get__(self, inst, type_=None):

        # Create a child context for the new classes.
        context = copy.copy(inst.context)
        context['context'] = context
        context[inst.related_name] = inst
        if 'document' not in context and isinstance(inst, Document):
            context.update(document=inst)

        # Create a new wrapper class if a wrapper was defined on the
        # manager.
        wrapper = getattr(self, 'wrapper', None)
        if wrapper is not None:
            wrapper_name = wrapper.__name__
            context['manager'] = self
            new_wrapper = type(wrapper_name, (wrapper,), context)
            del context['manager']
            context.update(wrapper=new_wrapper)

        # Otherwise, create the new manager subclass.
        cls = self.__class__
        newclass = type(cls.__name__, (cls,), context)

        if getattr(self, 'methods_only', None):
            # If this manager just adds methods without wrapping any data
            # from the instance, no need to go further; just return self.
            return newclass(self)
        else:
            # Else wrap the instance data in the new class.
            inst = newclass(inst[self.keyname])
            return inst

    @property
    def keyname(self):
        try:
            return self._keyname
        except AttributeError:
            pass
        keyname = self.__class__.__name__
        return keyname.lower().replace('manager', '')


class ListManager(list, AttrManager):
    def __iter__(self):
        wrapper = self._wrapper
        for obj in self.document[self.keyname]:
            yield wrapper(obj)

    def __getitem__(self, int_or_slice):
        '''Note to self for future--django's templating system does some
        perhaps rather silly voodoo to try __getattr__, __getitem__ when you
        reference object attributes in templates, and if your custom ORM
        throws custom errors, django might not handle those correctly, leading
        to difficult-to-debug issues. Better to let python throw its own
        errors from operations, which django handles well.
        '''
        ret = self._wrapper(list.__getitem__(self, int_or_slice))
        if isinstance(int_or_slice, int):
            return self._wrapper(ret)
        elif isinstance(int_or_slice, slice):
            return map(self._wrapper, ret)


class DictManager(dict, AttrManager):
    def items(self):
        return [(k, self._wrapper(v)) for (k, v) in dict.items(self)]

    def __getitem__(self, key):
        return self._wrapper(dict.__getitem__(self, key))


class RelatedDocument(ReadOnlyAttribute):
    '''
    Set an instance of this descriptor as a class attribute on a
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

        # If multiple model keys were defined, apply boolean mongo query syntax
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
