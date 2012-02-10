import pdb

from django.db import models
from pymongo import Connection
from pymongo.son_manipulator import SONManipulator

from billy.conf import settings

import billy.utils



db = Connection(host=settings.MONGO_HOST, port=settings.MONGO_PORT)
db = getattr(db, settings.MONGO_DATABASE)


# ---------------------------------------------------------------------------
# 
class ReadOnlyAttribute(object):

	def __set__(self, instance, value):
		msg = self.__class__.__name__ + " is instance is read-only."
		raise Exception(msg)




# ---------------------------------------------------------------------------
# 
class SessionDetails(ReadOnlyAttribute, dict):

	def __get__(self, instance, collection=db.metadata):
		return instance.metadata['session_details']






# ---------------------------------------------------------------------------
#

class Metadata(dict):

	@classmethod
	def get(cls, abbr):
		return cls(billy.utils.metadata(abbr))

	@property
	def abbr(self):
		return self['_id']

	def legislators(self, spec=None, **kw):
		_spec = {'state': self['_id']}
		if spec:
			_spec.update(spec)
		return db.legislators.find(_spec, **kw)


class Legislator(dict):
	pass

	

class Bill(dict):

	@property
	def metadata(self, get_metadata=billy.utils.metadata):
		return get_metadata(self['state'])

	session_details = SessionDetails()


class Report(dict):

	@property
	def metadata(self, get_metadata=billy.utils.metadata):
		return get_metadata(self['_id'])

	@property
	def session_link_data(self):
		'''
		An iterable of tuples like ('821', '82nd Legislature, 1st Called Session')
		'''
		session_details = self.metadata['session_details']
		for s in self['bills']['sessions']:
			yield (s, session_details[s]['display_name'])
	


# ---------------------------------------------------------------------------
# 
class_dict = {'bills': Bill,
			  'reports': Report,
			  'metadata': Metadata,
			  'legislators': Legislator,}

class Transformer(SONManipulator):
    def transform_outgoing(self, son, collection, class_dict=class_dict):
    	name = collection.name 
    	if name in class_dict:
        	return class_dict[name](son)
        else:
        	return son

db.add_son_manipulator(Transformer())




if __name__ == "__main__":
    bb = db.bills.find_one()
    print bb.session_details
    import pdb
    pdb.set_trace()
