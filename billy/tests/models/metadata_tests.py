'''
The tests in this module cover the following functions of
the Metadata model:
 * Metadata.legislators RelatedDocuments manager
 * Metadata.committees RelatedDocuments manager
 * Metadata.bills RelatedDocuments manager
 * Metadata.terms_manager ListManager[DictManager...]
'''
from . import setup_func
from nose.tools import with_setup, eq_
from billy.models import db


# Legislators
@with_setup(setup_func)
def test_metadata_legislators():
    '''Does Metadata.legislators return the correct set of legislators?
    '''

    # Get the metadata's legislators manually.
    rv1 = list(db.legislators.find({'state': 'ex'}))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.legislators())

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_legislators_fields():
    '''Does Metadata.legislators limit returned fields as expected?
    '''
    fields = ['full_name']

    # Get the metadata's legislators manually.
    rv1 = list(db.legislators.find({'state': 'ex'}, fields=fields))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.legislators(fields=fields))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_legislators_extra_spec():
    '''Does Metadata.legislators add the extra spec to the mongo query?
    '''
    spec = dict(first_name="Larry")

    # Get the metadata's legislators manually.
    rv1 = list(db.legislators.find(dict({'state': 'ex'}, **spec)))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.legislators(spec))

    eq_(rv1, rv2)


# Committees
@with_setup(setup_func)
def test_metadata_committees():
    '''Does Metadata.committees return the correct set of committees?
    '''

    # Get the metadata's committees manually.
    rv1 = list(db.committees.find({'state': 'ex'}))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.committees())

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_committees_fields():
    '''Does Metadata.committees limit returned fields as expected?
    '''
    fields = ['committee']

    # Get the metadata's committees manually.
    rv1 = list(db.committees.find({'state': 'ex'}, fields=fields))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.committees(fields=fields))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_committees_extra_spec():
    '''Does Metadata.committees add the extra spec to the mongo query?
    '''
    spec = dict(committee=u'Standing Committee on Fakeness')

    # Get the metadata's committees manually.
    rv1 = list(db.committees.find(dict({'state': 'ex'}, **spec)))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.committees(spec))

    eq_(rv1, rv2)


# Terms
@with_setup(setup_func)
def test_metadata_terms_session_names():
    # Get term session names manually.
    meta1 = db.metadata.find_one('ex')
    for term1 in meta1['terms']:
        if term1['name'] == 'T1':
            break
    names1 = []
    for sess in term1['sessions']:
        names1.append(meta1['session_details'][sess]['display_name'])

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    names2 = list(meta2.terms_manager[1].session_names())

    eq_(names1, names2)


# Bills.
@with_setup(setup_func)
def test_metadata_bills():
    '''Does Metadata.bills return the correct set of bills?
    '''

    # Get the metadata's bills manually.
    rv1 = list(db.bills.find({'state': 'ex'}))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.bills())

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_bills_fields():
    '''Does Metadata.bills limit returned fields as expected?
    '''
    fields = ['title']

    # Get the metadata's bills manually.
    rv1 = list(db.bills.find({'state': 'ex'}, fields=fields))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.bills(fields=fields))

    eq_(rv1, rv2)


@with_setup(setup_func)
def test_metadata_bills_extra_spec():
    '''Does Metadata.bills add the extra spec to the mongo query?
    '''
    spec = dict(title=u'A fake act.')

    # Get the metadata's bills manually.
    rv1 = list(db.bills.find(dict({'state': 'ex'}, **spec)))

    # Now through the model method.
    meta2 = db.metadata.find_one('ex')
    rv2 = list(meta2.bills(spec))

    eq_(rv1, rv2)
