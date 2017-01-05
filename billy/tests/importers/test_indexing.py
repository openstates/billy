import argparse
from billy.core import db
from billy.bin.commands.ensure_indexes import MongoIndex
import unittest


def _assert_index(query, name_piece=None):
    try:
        index = query.explain()['queryPlanner']['winningPlan']['inputStage']['indexName']
    except KeyError:
        index = None
    assert index is not None
    if name_piece:
        assert name_piece in index, ("%s not used %s" % (name_piece, index))



@unittest.skip("temporarily disabled")
def test_bill_indexes():
    parser = argparse.ArgumentParser(description='generic billy util')
    subparsers = parser.add_subparsers(dest='subcommand')

    class StubObj(object):
        collections = ['bills', 'votes']

    db.create_collection('bills')
    db.create_collection('votes')
    MongoIndex(subparsers).handle(StubObj())

    # looking up individual bills
    _assert_index(db.bills.find({'state': 'ex'}))
    _assert_index(db.bills.find({'state': 'ex', 'chamber': 'lower'}))
    _assert_index(db.bills.find({'state': 'ex', 'chamber': 'lower',
                                 'bill_id': 'HB 27'}))
    _assert_index(db.bills.find({'state': 'ex', '_id': 'XYZ'}))

    # ensure that the sort indices work correctly
    _assert_index(db.bills.find({'versions.doc_id': 'XYZ'}).sort('created_at'))
    _assert_index(db.bills.find({'versions.doc_id': 'XYZ'}).sort('updated_at'))
    _assert_index(db.bills.find({'versions.doc_id': 'XYZ'}).sort(
        'action_dates.last'))

    # subjects
    _assert_index(db.bills.find({'state': 'ex', 'subjects': 'test'}),
                  'subjects')
    _assert_index(db.bills.find({'state': 'ex', 'subjects': 'test'})
                  .sort('action_dates.last'), 'subjects')

    _assert_index(db.bills.find({'state': 'ex'}).sort('action_dates.first'),
                  'first')
    _assert_index(db.bills.find({'state': 'ex'}).sort('action_dates.last'),
                  'last')
    _assert_index(db.bills.find({'state': 'ex'})
                  .sort('action_dates.passed_upper'), 'passed_upper')
    _assert_index(db.bills.find({'state': 'ex'})
                  .sort('action_dates.passed_lower'), 'passed_lower')

    # votes
    _assert_index(db.votes.find({'bill_id': 'XYZ'}))
    _assert_index(db.votes.find({'bill_id': 'XYZ', 'date': 123}))
    _assert_index(db.votes.find({'_voters': 'XYZ'}))
    _assert_index(db.votes.find({'_voters': 'XYZ', 'date': 123}))
