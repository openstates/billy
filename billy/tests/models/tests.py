
import unittest
from random import choice

from billy.models import Bill, Metadata, Legislator, CommitteeMember
from billy.models import models_list
from billy import db

class TestNoConflict(unittest.TestCase):
	'''
	Make sure no model attribute names conflict with document keys.
	'''
	def conflict_exists(self, model_attrs, doc_keys):
		return model_attrs & doc_keys

	def test_all_models(self):
		conflict_exists = self.conflict_exists
		for model in models_list:
			model_attrs = set(dir(model))
			for document in model.collection.find():
				doc_keys = set(document)
				self.assertFalse(conflict_exists(model_attrs, doc_keys))

	def test_bogus_key(self, model=Bill):
		document = model.collection.find_one()
		model_attrs = set(dir(model))
		doc_keys = set(document)
		bogus_key = choice(list(model_attrs - doc_keys))
		document[bogus_key] = 3
		doc_keys = set(document)
		self.assertTrue(self.conflict_exists(model_attrs, doc_keys))


class TestDereferencing(unittest.TestCase):

	def test_state_legislators(self):

		# Pick a state.
		meta = list(db.metadata.find())

		for m in meta:

			# First get the state's legislator's manually.
			legislators1 = list(db.legislators.find({'state': m['_id']}))

			# Now get them the spiffy way.
			legislators2 = list(Metadata(m).legislators())

			self.assertEqual(legislators1, legislators2)


	def test_state_committees(self):

		# Pick a state.
		meta = list(db.metadata.find())

		for m in meta:

			# First get the state's legislator's manually.
			committees1 = list(db.committees.find({'state': m['_id']}))

			# Now get them the spiffy way.
			committees2 = list(Metadata(m).committees())

			self.assertEqual(committees1, committees2)


	def test_legislator_committees(self):

		# Pick a state.
		for leg in db.legislators.find():
				
			leg_id = leg['_id']

			# Get the committees manually. 
			committees1 = list(db.committees.find({'members.leg_id': leg_id}))

			# Now the spiffy way.
			committees2 = list(Legislator(leg).committees())

			self.assertEqual(committees1, committees2)


	def test_legislator_sponsored_bills(self):

		# Pick a state.
		for leg in db.legislators.find():
				
			leg_id = leg['_id']

			# Get the legislator's bills manually. 
			bills1 = list(db.bills.find({'sponsors.leg_id': leg_id}))

			# Now the spiffy way.
			bills2 = list(Legislator(leg).sponsored_bills())

			self.assertEqual(bills1, bills2)

	def test_committeemember_legislator(self):

		for c in db.committees.find():

			for member in c['members']:

				leg_id = member['leg_id']

				if leg_id is None:
					continue

				# Get the legislator manually...
				leg1 = db.legislators.find_one(leg_id)

				# And the spiffy way.
				leg2 = CommitteeMember(member).legislator_object()

				if (leg1 is None) or (leg2 is None):
					pdb.set_trace()

				self.assertEqual(leg1, leg2)


if __name__ == "__main__":
	unittest.main()				


