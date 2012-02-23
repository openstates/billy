'''


'''
import pdb
import sys

from pymongo import Connection
from pymongo.son_manipulator import SONManipulator

from billy.conf import settings
from billy.utils import metadata as get_metadata


db = Connection(host=settings.MONGO_HOST, port=settings.MONGO_PORT)
db = getattr(db, settings.MONGO_DATABASE)

def  get_model(classname, this_module=sys.modules[__name__]):
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
        return get_metadata(self['state'])


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
            msg = "Can't dereference: model %r has no foreign_key_string defined."
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
    def __init__(self, model, model_key, instance_key='_id'):
        self.model = model
        self.instance_key = instance_key
        self.model_key = model_key


    def __get__(self, instance, type_=None, *args, **kwargs):

        model = self.model
        if isinstance(model, basestring):
            model = self.model = get_model(model)
        
        self.instance_val = instance[self.instance_key]

        return self
        

    def __call__(self, extra_spec={}, *args, **kwargs):
        spec = {self.model_key: self.instance_val}
        spec.update(extra_spec)
        return self.model.collection.find(spec, *args, **kwargs)



# ---------------------------------------------------------------------------
# Model definitions. 


class CommitteeMember(dict):
    legislator_object = RelatedDocument('Legislator')

class Committee(Document):

    collection = db.committees

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



class Legislator(Document):
    
    collection = db.legislators
    foreign_key_string = 'leg_id'

    committees = RelatedDocuments('Committee', model_key='members.leg_id')
    sponsored_bills = RelatedDocuments('Bill', model_key='sponsors.leg_id')



class Metadata(Document):
    '''
    The metadata can also be thought as the "state" (i.e., Montana, Texas)
    when it's an attribute of another object. For example, if you have a 
    bill, you can do this:

    >>> bill.state.abbr
    'de'
    '''
    collection = db.metadata

    legislators = RelatedDocuments(Legislator, model_key='state', 
                                   instance_key='abbreviation')


    committees = RelatedDocuments(Committee, model_key='state', 
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




class Bill(Document):

    collection = db.bills

    def session_details(self):
        metadata = self.metadata
        return metadata['session_details'][self['session']]

    def most_recent_action(self):
        return self['actions'][-1]

    def chamber_name(self):
        '''"lower" --> "House of Representatives"'''
        return self.metadata['%s_chamber_name' % self['chamber']]



class Report(Document):

    collection = db.reports

    def session_link_data(self):
        '''
        An iterable of tuples like ('821', '82nd Legislature, 1st Called Session')
        '''
        session_details = self.metadata['session_details']
        for s in self['bills']['sessions']:
            yield (s, session_details[s]['display_name'])
    


# ---------------------------------------------------------------------------
# Setup the SON manipulator.
_collection_model_dict = {}

models_list = [
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


