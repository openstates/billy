import pdb

import pymongo

from mongoengine import Document
from mongoengine.base import BaseField, get_document
from mongoengine.fields import *
from mongoengine.fields import DO_NOTHING, RECURSIVE_REFERENCE_CONSTANT

class CrossReferenceField(BaseField):
    """This crossreference field allows references to other collections, 
    which mongodengine astonishingly does'nt support, unless I misunderstood
    something obvious about it.e
    """

    def __init__(self, document_type, id_field_name='_id', 
                 reverse_delete_rule=DO_NOTHING, **kwargs):
        """Initialises the Reference Field.

        :param reverse_delete_rule: Determines what to do when the referring
          object is deleted
        """
        if not isinstance(document_type, basestring):
            if not issubclass(document_type, (Document, basestring)):
                raise ValidationError('Argument to ReferenceField constructor '
                                      'must be a document class or a string')
        self.document_type_obj = document_type
        self.reverse_delete_rule = reverse_delete_rule
        self.id_field_name = id_field_name
        super(CrossReferenceField, self).__init__(**kwargs)


    @property
    def document_type(self):
        if isinstance(self.document_type_obj, basestring):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj


    def __get__(self, instance, owner):
        """Descriptor to allow lazy dereferencing.
        """

        if instance is None:
            # Document class being used rather than a document object
            return self

        # Get value from document instance if available
        value = instance._data.get(self.name)

        # Dereference DBRefs

        if isinstance(value, basestring):
            spec = {self.id_field_name: value}
            value = self.document_type.objects.get(**spec)
            if value is not None:
                instance._data[self.name] = value

        return super(CrossReferenceField, self).__get__(instance, owner)

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)

    # Note: these write methods would have to be re-written if this
    # model were to be used for writing to mongo.
    def to_mongo(self, document):
        raise NotImplemented

    def prepare_query_value(self, op, value):
        raise NotImplemented

    def validate(self, value):
        raise NotImplemented




class SessionsField(BaseField):
    """Worst docstring of all time.
    """

    def __init__(self, document_type, 
                 reverse_delete_rule=DO_NOTHING, **kwargs):
        """Initialises the Reference Field.

        :param reverse_delete_rule: Determines what to do when the referring
          object is deleted
        """
        if not isinstance(document_type, basestring):
            if not issubclass(document_type, (Document, basestring)):
                raise ValidationError('Argument to ReferenceField constructor '
                                      'must be a document class or a string')
        self.document_type_obj = document_type
        self.reverse_delete_rule = reverse_delete_rule
        super(SessionsField, self).__init__(**kwargs)


    @property
    def document_type(self):
        if isinstance(self.document_type_obj, basestring):
            if self.document_type_obj == RECURSIVE_REFERENCE_CONSTANT:
                self.document_type_obj = self.owner_document
            else:
                self.document_type_obj = get_document(self.document_type_obj)
        return self.document_type_obj
        

    def __get__(self, instance, owner):
        """Descriptor to allow lazy dereferencing.
        """

        if instance is None:
            # Document class being used rather than a document object
            return self

        # Get value from document instance if available
        value = instance._data.get(self.name)

        # Dereference DBRefs
        pdb.set_trace()
        if isinstance(value, basestring):
            spec = {self.id_field_name: value}
            value = self.document_type.objects.get(**spec)
            if value is not None:
                instance._data[self.name] = value

        return super(CrossReferenceField, self).__get__(instance, owner)

    def lookup_member(self, member_name):
        return self.document_type._fields.get(member_name)

    # Note: these write methods would have to be re-written if this
    # model were to be used for writing to mongo.
    def to_mongo(self, document):
        raise NotImplemented

    def prepare_query_value(self, op, value):
        raise NotImplemented

    def validate(self, value):
        raise NotImplemented
    

