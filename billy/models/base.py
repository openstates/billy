import re
import copy
import itertools

from django.core import urlresolvers

from billy.core import _model_registry, _model_registry_by_collection
from billy.web.admin import urls as admin_urls


# TODO: put this in a util file
def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(itertools.islice(iterable, n))


def get_model(classname):
    '''
    Helper to enable RelatedDocuments to reference models by name (string)
    rather than passing the actual class, which may not be defined in the
    module.
    '''
    return _model_registry[classname]


class classproperty(property):
    '''Based on the python 2.2 release notes--
    http://www.python.org/download/releases/2.2/descrintro/#property
    '''
    def __get__(self, cls, instance):
        return self.fget.__get__(None, instance)()


class ModelBase(type):
    def __new__(meta, classname, bases, classdict):
        cls = type.__new__(meta, classname, bases, classdict)

        if bases[0] != dict:
            _model_registry[classname] = cls
            _model_registry_by_collection[cls.collection.name] = cls

        return cls


class ModelDefinitionError(Exception):
    '''Raised if there's a problem with a model definition.'''
    pass


class DoesNotExist(Exception):
    pass


class Document(dict):
    '''
    This base class represents a MongoDB document.

    Methods that return related documents from other collections,
    like `metadata.legislators` or `bill.sponsors` should return a cursor
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

    @classmethod
    def related_name(cls):
        try:
            return cls._related_name
        except:
            related_name = cls.__name__.lower()
            return related_name

    @property
    def _related_cache(self):
        '''A cache for storing related objects already retrieved from
        mongo.
        '''
        try:
            return self._related_cache_dict
        except AttributeError:
            _related_cache_dict = {}
            self._related_cache_dict = _related_cache_dict
            return _related_cache_dict

    @property
    def id(self):
        '''
        Alias '_id' to avoid django template complaints about names
        with leading underscores.
        '''
        try:
            return self['_id']
        except KeyError:
            # In API results, some records have an 'id' instead if '_id'.
            return self['id']

    def chamber_name(self):
        chamber = self['chamber']
        if chamber == 'joint':
            return 'Joint'
        elif chamber is None:
            return ''
        return self.metadata['chambers'][chamber]['name']

    @property
    def collection_name(self):
        '''If you try to reference {{obj.collection.name}} in django template,
        it will return a new collection named `collection`.name then call
        its __unicode__. Fail.
        '''
        return self.collection.name

    def get_admin_json_url(self):
        return '/admin' + urlresolvers.reverse(
            'object_json', urlconf=admin_urls,
            args=[self.collection_name, self.id])


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
        context[inst.related_name()] = inst
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
            inst = newclass(inst[self._keyname])
            return inst

    @property
    def _keyname(self):
        try:
            return self.keyname
        except AttributeError:
            pass
        keyname = self.__class__.__name__
        return keyname.lower().replace('manager', '')


class ListManager(list, AttrManager):
    def __iter__(self):
        wrapper = self._wrapper
        for obj in self.document[self._keyname]:
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
        data = dict.__getitem__(self, key)
        if isinstance(data, dict):
            return self._wrapper(data)
        elif isinstance(data, list):
            return map(self._wrapper, data)
        else:
            return data


class RelatedDocument(object):
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

        # Only do this lookup once for each instance.
        related_name = self.model.related_name()
        try:
            return self.instance._related_cache[related_name]
        except KeyError:
            pass

        if self.model_id[2] == 'B':
            spec = {'_all_ids': self.model_id}
        else:
            spec = {'_id': self.model_id}
        spec.update(extra_spec)

        obj = self.model.collection.find_one(spec, *args, **kwargs)
        if obj is None:
            msg = 'No %s found for %r' % (self.model.collection.name,
                                          (spec, args, kwargs))

            raise DoesNotExist(msg)

        self.instance._related_cache_dict[related_name] = obj
        return obj


class RelatedDocuments(object):
    '''
    Set an instance of this descriptor as class attribute on a Document
    subclass, and when accessed on an instance, it will return
    a cursor of all objects that reference this instance's id using
    the key `model_key`. For example, this could be used to get all
    "legislator" documents for a given "metadata".
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
            the default mongo query spec with, like 'abbr' or 'session'.
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
        self.instance = instance

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

        instance = self.instance
        cursor = self.model.collection.find(spec, *args, **kwargs)
        return CursorWrapper(cursor, instance)

    @property
    def _related_name(self):
        related_name = getattr(self.instance, 'related_name', None)
        if related_name is not None:
            return related_name
        related_name = self.model.__name__.lower()
        related_name = re.sub(r'manager$', '', related_name)
        return related_name


class CursorWrapper(object):
    '''The purpose of this hack is to make the original object
    accessible via its related name on related objects retrieved
    through a RelatedDocuments attribute.

    In English, this enables:

    for vote in legislator.votes_manager():
        print(vote.legislator)

    This was the only way I could think of to do this without
    a huge rewrite. The solution in the AttrManager classes is
    better (IMO) but not an option when we're using the pymongo
    Transformer gizmo (see .base)
    '''

    def __init__(self, cursor, instance):
        self.cursor = cursor
        self.instance = instance

    def __iter__(self):
        instance = self.instance
        related_name = instance.related_name()
        for obj in self.cursor:
            try:
                setattr(obj, related_name, instance)
            except AttributeError:
                # Obj has a read-only metadata property. Skip.
                pass
            yield obj

    def next(self):
        obj = next(self.cursor)
        setattr(obj, self.instance.related_name(), self.instance)
        return obj

    def count(self):
        return self.cursor.count()

    def skip(self, *args, **kwargs):
        return CursorWrapper(
            self.cursor.skip(*args, **kwargs), self.instance)

    def limit(self, *args, **kwargs):
        return CursorWrapper(
            self.cursor.limit(*args, **kwargs), self.instance)

    def sort(self, *args, **kwargs):
        return CursorWrapper(
            self.cursor.sort(*args, **kwargs), self.instance)

    def distinct(self, *args, **kwargs):
        return CursorWrapper(
            self.cursor.distinct(*args, **kwargs), self.instance)
