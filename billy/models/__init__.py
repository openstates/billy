import pdb

from pymongo import Connection
from pymongo.son_manipulator import SONManipulator
from bson.code import Code

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

	@classmethod
	def all(cls):
		return cls()

	@property
	def abbr(self):
		return self['_id']

	def legislators(self, spec=None, **kw):
		_spec = {'state': self['_id']}
		if spec:
			_spec.update(spec)
		return db.legislators.find(_spec, **kw)

	def committees(self, spec=None, **kw):
		_spec = {'state': self['_id']}
		if spec:
			_spec.update(spec) 
		return db.committees.find(_spec, **kw)		


class Legislator(dict):
	
	@staticmethod
	def get(**spec):
		return db.legislators.find_one(spec)

	def committees(self):
		'''
		This simple method doesn't currently account for subcomittee membership.
		'''
		committees = db.committees.find({}, {'committee': 1, 'members': 1})
		leg_id = self['_id']
		res = []
		for c in committees:
			for m in c['members']:
				if leg_id == m['leg_id']:
					res.append(c)
					break
		return res

	def sponsored_bills(self):
		'''
		This overly-simple method would be a good candidate for optimization.
		I tried map/reduce and it forced me to eat a gigantic pail of FAIL...
		'''
		_id = self['_id']
		spec = {'state': self['state']}
		fields = {'actions': 1, 'title': 1, 'bill_id': 1, 'sponsors': 1}
		bills = db.bills.find(spec, fields)
		sponsored_bills = []
		for bill in bills:
			for s in bill['sponsors']:
				if s['leg_id'] == _id:
					sponsored_bills.append(bill)

		return sponsored_bills[:5]


class CommitteeMember(dict):

	def legislator(self):
		leg_id = self['leg_id']
		if leg_id:
			return Legislator.get(_id=leg_id)


class Committee(dict):

	@property
	def id(self):
		return self['_id']

	def members_objects(self):
		'''
		Return a list of CommitteeMember objects.
		'''
		m = map(CommitteeMember, self['members'])
		return map(CommitteeMember, self['members'])

	def display_name(self):
		try:
			return self['committee']
		except KeyError:
			try:
				return self['subcommittee']
			except KeyError:
				raise

	@staticmethod
	def get(**spec):
		return db.committees.find_one(spec)

		

class Bill(dict):

	@staticmethod
	def get(**spec):
		return db.bills.find_one(spec)

	def id(self):
		return self['_id']

	@property
	def metadata(self, get_metadata=billy.utils.metadata):
		return get_metadata(self['state'])

	session_details = SessionDetails()

	def most_recent_action(self):
		return self['actions'][-1]


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
			  'legislators': Legislator,
			  'committees': Committee}

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
