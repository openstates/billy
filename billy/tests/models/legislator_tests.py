'''
The tests in this module cover the following functions of
the Legislator model:

'''
from . import setup_func
from nose.tools import with_setup, eq_
from billy.models import db


@with_setup(setup_func)
def test_legislator_committees():
    '''Does Legislator.committees return the correct set of committees?
    '''

    # Get the leg's committees manually.
    rv1 = list(db.committees.find({'members.leg_id': 'EXL000001'}))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.committees())

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_legislator_committees_fields():
    '''Does Legislator.committees limit fields appropriately?
    '''
    fields = ['committee']

    # Get the leg's committees manually.
    rv1 = list(db.committees.find({'members.leg_id': 'EXL000001'},
                                  fields=fields))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.committees(fields=fields))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_legislator_committees_extra_spec():
    '''Does Legislator.committees apply an extra spec properly?
    '''
    extra_spec = {'committee': u'Standing Committee on Phony'}
    # Get the leg's committees manually.
    spec = dict({'members.leg_id': 'EXL000001'}, **extra_spec)
    rv1 = list(db.committees.find(spec))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.committees(extra_spec))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_legislator_votes():
    '''Does Legislator.votes return the correct set of votes?
    '''
    # Get the leg's votes manually.
    rv1 = list(db.votes.find({'_voters': 'EXL000001'}))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.votes_manager())

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_legislator_votes_fields():
    '''Does Legislator.votes limit fields appropriately?
    '''
    fields = ['motion']

    # Get the leg's votes manually.
    rv1 = list(db.votes.find({'_voters': 'EXL000001'}, fields=fields))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.votes_manager(fields=fields))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_legislator_votes_extra_spec():
    '''Does Legislator.votes apply an extra spec properly?
    '''
    extra_spec = {'motion': u'Fake motion'}

    # Get the leg's votes manually.
    spec = dict({'_voters': 'EXL000001'}, **extra_spec)
    rv1 = list(db.votes.find(spec))

    # Now through the model method.
    leg = db.legislators.find_one('EXL000001')
    rv2 = list(leg.votes_manager(extra_spec))

    eq_(rv1, rv2)


# votes
@with_setup(setup_func)
def test_legislator_rolesmanager_mutation():
    '''Verify Legislator.roles_manager doesn't mutate legislator['roles'].
    '''
    leg = db.legislators.find_one('EXL000001')
    eq_(leg['roles'], leg.roles_manager)


# @with_setup(setup_func)
# def test_metadata_committees_fields():
#     '''Does Metadata.committees limit returned fields as expected?
#     '''
#     fields = ['committee']

#     # Get the metadata's committees manually.
#     rv1 = list(db.committees.find({'state': 'ex'}, fields=fields))

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     rv2 = list(meta2.committees(fields=fields))

#     eq_(rv1, rv2)


# @with_setup(setup_func)
# def test_metadata_committees_extra_spec():
#     '''Does Metadata.committees add the extra spec to the mongo query?
#     '''
#     spec = dict(committee=u'Standing Committee on Fakeness')

#     # Get the metadata's committees manually.
#     rv1 = list(db.committees.find(dict({'state': 'ex'}, **spec)))

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     rv2 = list(meta2.committees(spec))

#     eq_(rv1, rv2)


# # Terms
# @with_setup(setup_func)
# def test_metadata_terms_session_names():
#     '''Does Metadata.committees add the extra spec to the mongo query?
#     '''
#     # Get term session names manually.
#     meta1 = db.metadata.find_one('ex')
#     for term1 in meta1['terms']:
#         if term1['name'] == '20112012':
#             break
#     names1 = []
#     for sess in term1['sessions']:
#         names1.append(meta1['session_details'][sess]['display_name'])

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     names2 = list(meta2.terms_manager[0].session_names())

#     eq_(names1, names2)


# # Bills.
# @with_setup(setup_func)
# def test_metadata_bills():
#     '''Does Metadata.bills return the correct set of bills?
#     '''

#     # Get the metadata's bills manually.
#     rv1 = list(db.bills.find({'state': 'ex'}))

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     rv2 = list(meta2.bills())

#     eq_(rv1, rv2)


# @with_setup(setup_func)
# def test_metadata_bills_fields():
#     '''Does Metadata.bills limit returned fields as expected?
#     '''
#     fields = ['title']

#     # Get the metadata's bills manually.
#     rv1 = list(db.bills.find({'state': 'ex'}, fields=fields))

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     rv2 = list(meta2.bills(fields=fields))

#     eq_(rv1, rv2)


# @with_setup(setup_func)
# def test_metadata_bills_extra_spec():
#     '''Does Metadata.bills add the extra spec to the mongo query?
#     '''
#     spec = dict(title=u'A fake act.')

#     # Get the metadata's bills manually.
#     rv1 = list(db.bills.find(dict({'state': 'ex'}, **spec)))

#     # Now through the model method.
#     meta2 = db.metadata.find_one('ex')
#     rv2 = list(meta2.bills(spec))

#     eq_(rv1, rv2)
