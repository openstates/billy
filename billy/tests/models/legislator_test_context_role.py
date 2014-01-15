'''
Things that need tests:

- Wrapped items from ListManager and DictManager return
  have the correct inherited attributes.
- RelatedDocument returns the right document.
- RelatedDocuments returns the right sequence of documents.
- CursorWrapper works as expected--all methods do the same
  thing as an actual cursor.
'''
import datetime

import nose.tools
from nose.tools import with_setup
from billy.models import db


def setup_func():
    assert db.name.endswith('_test')
    db.metadata.drop()
    db.bills.drop()
    db.votes.drop()
    db.legislators.drop()
    db.document_ids.drop()
    db.vote_ids.drop()
    db.committees.drop()

    vote = {
        u'+threshold': u'2/3',
        u'_type': u'vote',
        u'chamber': u'lower',
        u'date': datetime.datetime(2010, 6, 21, 21, 6),
        u'motion': u'Assembly Third Reading',
        u'no_count': 27,
        u'no_votes': [],
        u'other_count': 5,
        u'other_votes': [],
        u'passed': True,
        u'sources': [],
        u'type': u'passage',
        u'vote_id': u'CAV00032373',
        u'yes_count': 47,
        u'yes_votes': [
            {u'leg_id': u'CAL000104', u'name': u'Ammiano'},
        ]
    }

    # Add a vote for the current session bill.
    db.votes.insert(dict(vote, bill_id='CAB00007468',
                         date=datetime.datetime(2011, 12, 6, 0, 0)))

    # Add a vote for the prior session bill.
    db.votes.insert(dict(vote, bill_id='CAB00005131',
                         date=datetime.datetime(2009, 12, 6, 0, 0)))

    # Insert some test records.
    db.legislators.insert({
        "_all_ids": ["CAL000104"],
        "_id": "CAL000104",
        "_type": "person",
        "active": True,
        "district": "13",
        "leg_id": "CAL000104",

        "old_roles": {
            "20092010": [
                {
                    "+active": True,
                    "chamber": "lower",
                    "country": "us",
                    "district": "1",
                    "end_date": datetime.datetime(2010, 1, 1, 0, 0),
                    "level": "state",
                    "party": "Democratic",
                    "start_date": datetime.datetime(2009, 1, 1, 0, 0),
                    "state": "ca",
                    "term": "20092010",
                    "type": "member"
                },
                {
                    "+active": True,
                    "chamber": "lower",
                    "country": "us",
                    "district": "2",
                    "end_date": datetime.datetime(2010, 12, 1, 0, 0),
                    "level": "state",
                    "party": "Democratic",
                    "start_date": datetime.datetime(2010, 1, 2, 0, 0),
                    "state": "ca",
                    "term": "20092010",
                    "type": "member"
                },
            ],
            'fake-session': [{
                "state": "ca",
                "chamber": "joint",
                "district": "13",
                "end_date": None,
                "party": "Democratic",
                "start_date": None,
                "term": "fake-term",
                "type": "member"
            }]

        },
        "party": "Democratic",
        "roles": [

            # Earlier role from 2011 to 2012.
            {
                "chamber": "lower",
                "district": "13",
                "start_date": datetime.datetime(2011, 1, 1, 0, 0),
                "party": "Democratic",
                "end_date": datetime.datetime(2012, 1, 1, 0, 0),
                "state": "ca",
                "term": "20112012",
                "type": "member"
            },

            # Later role from 2012-2013.
            {
                "chamber": "lower",
                "district": "14",
                "start_date": datetime.datetime(2012, 1, 2, 0, 0),
                "party": "Democratic",
                "end_date": datetime.datetime(2012, 12, 1, 0, 0),
                "state": "ca",
                "term": "20112012",
                "type": "member"
            },
            {
                "state": "ca",
                "chamber": "joint",
                "district": "13",
                "end_date": None,
                "party": "Democratic",
                "start_date": None,
                "term": "fake-term",
                "type": "member"
            }
        ],
        "state": "ca",
    })

    db.metadata.insert({
        u'_id': u'ca',
        u'_type': u'metadata',
        u'abbreviation': u'ca',
        u'legislature_name': u'California State Legislature',
        u'name': u'California',
        u'session_details': {
            u'20092010': {
                u'display_name': u'2009-2010 Regular Session',
                u'start_date': datetime.datetime(2008, 12, 1, 0, 0),
                u'type': u'primary'},
            u'20092010 Special Session 1': {
                u'display_name': u'2009-2010, 1st Special Session',
                u'type': u'special'},
            u'20092010 Special Session 2': {
                u'display_name': u'2009-2010, 2nd Special Session',
                u'type': u'special'},
            u'20092010 Special Session 3': {
                u'display_name': u'2009-2010, 3rd Special Session',
                u'type': u'special'},
            u'20092010 Special Session 4': {
                u'display_name': u'2009-2010, 4th Special Session',
                u'type': u'special'},
            u'20092010 Special Session 5': {
                u'display_name': u'2009-2010, 5th Special Session',
                u'type': u'special'},
            u'20092010 Special Session 6': {
                u'display_name': u'2009-2010, 6th Special Session',
                u'type': u'special'},
            u'20092010 Special Session 7': {
                u'display_name': u'2009-2010, 7th Special Session',
                u'type': u'special'},
            u'20092010 Special Session 8': {
                u'display_name': u'2009-2010, 8th Special Session',
                u'type': u'special'},
            u'20112012': {
                u'display_name': u'2011-2012 Regular Session',
                u'start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'type': u'primary'},
            u'fake-session': {
                u'display_name': u'2011-2012 Regular Session',
                u'start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'type': u'primary'},
            u'fake-session2': {
                u'display_name': u'2011-2012 Regular Session',
                u'start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'type': u'primary'},
            u'20112012 Special Session 1': {
                u'display_name': u'2011-2012, 1st Special Session',
                u'type': u'special'}},

        u'terms': [
            {
                u'+start_date': datetime.datetime(2008, 12, 1, 0, 0),
                u'end_year': 2010,
                u'name': u'20092010',
                u'sessions': [u'20092010', u'20092010 Special Session 1',
                              u'20092010 Special Session 2', u'20092010 Special Session 3',
                              u'20092010 Special Session 4', u'20092010 Special Session 5',
                              u'20092010 Special Session 6', u'20092010 Special Session 7',
                              u'20092010 Special Session 8'],
                u'start_year': 2009
            },
            {
                u'+start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'end_year': 2012,
                u'name': u'20112012',
                u'sessions': [u'20112012 Special Session 1', u'20112012'],
                u'start_year': 2011
            },
            {
                u'+start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'end_year': 2012,
                u'name': u'fake-term',
                u'sessions': [u'fake-session'],
                u'start_year': 2011
            },
            {
                u'+start_date': datetime.datetime(2010, 12, 6, 0, 0),
                u'end_year': 2012,
                u'name': u'fake-term2',
                u'sessions': [u'fake-session2'],
                u'start_year': 2011
            },
        ]
    })

    # A current session bill, where current session is 20112012.
    db.bills.insert({
        u'_all_ids': [u'CAB00007468'],
        u'_id': u'CAB00007468',
        u'_term': u'20112012',
        u'_type': u'bill',
        u'action_dates': {
            u'first': datetime.datetime(2011, 2, 17, 0, 0),
            u'last': datetime.datetime(2011, 8, 25, 0, 0),
            u'passed_lower': datetime.datetime(2011, 6, 2, 0, 0),
            u'passed_upper': None,
            u'signed': None},
        u'alternate_titles': [],
        u'bill_id': u'AB 889',
        u'chamber': u'lower',
        u'country': u'us',
        u'created_at': datetime.datetime(2011, 3, 24, 20, 45, 24, 16000),
        u'documents': [],
        u'level': u'state',
        u'session': u'20112012',
        u'sources': [{u'url': u'http://leginfo.legislature.ca.gov/fake'}],
        u'sponsors': [
            {u'leg_id': u'CAL000104',
             u'name': u'Ammiano',
             u'official_type': u'LEAD_AUTHOR',
             u'type': u'primary'},
        ],
        u'state': u'ca',
    })

    # A prior session bill, where prior is 20092010.
    db.bills.insert({
        u'_all_ids': [u'CAB00005131'],
        u'_id': u'CAB00005131',
        u'_term': u'20092010',
        u'_type': u'bill',
        u'action_dates': {
            u'first': datetime.datetime(2009, 2, 17, 0, 0),
            u'last': datetime.datetime(2009, 8, 25, 0, 0),
            u'passed_lower': datetime.datetime(2009, 6, 2, 0, 0),
            u'passed_upper': None,
            u'signed': None},
        u'chamber': u'lower',
        u'country': u'us',
        u'session': u'20092010 Special Session 4',
        u'sponsors': [
            {u'leg_id': u'CAL000104', u'name': u'Ammiano',
             u'type': u'cosponsor'}
        ],
        u'state': u'ca',
    })


'''
Need to test context_role with:
 - no related bill or vote (returns '')
 - related bill, single role for term
 - related vote, single role for term
 - related bill, multiple roles for term, one that fits
 - related vote, multiple roles for term, one that fits
 - related bill, multiple roles for term, none that fits
 - related vote, multiple roles for term, none that fits
 - passed-in term, bill, vote, session
'''


# Test context_role for current term, session, bill, vote.
@with_setup(setup_func)
def test_current_using_bill():
    # The bill's first action was in 2011, so the correct role is the first
    # one in leg['roles'], which lasts from 2011 to 2012.
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][0]
    bill = db.bills.find_one({'_term': '20112012'})
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))


@with_setup(setup_func)
def test_current_using_vote():
    leg = db.legislators.find_one()
    correct_role = leg['roles'][0]
    bill = db.bills.find_one({'_term': '20112012'})
    vote = next(bill.votes_manager())
    nose.tools.eq_(correct_role, leg.context_role(vote=vote))


@with_setup(setup_func)
def test_current_using_session_multiple_roles():
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][0]
    nose.tools.eq_(correct_role, leg.context_role(session='20112012'))


@with_setup(setup_func)
def test_current_using_session_single_role():
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][2]
    nose.tools.eq_(correct_role, leg.context_role(session='fake-session'))


@with_setup(setup_func)
def test_current_using_term_multiple_roles():
    # If there're multiple roles for a term, return the first role in the list.
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][0]
    nose.tools.eq_(correct_role, leg.context_role(term='20112012'))


@with_setup(setup_func)
def test_current_using_term_single_role():
    # If there'only one role for a term, return it.
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][2]
    nose.tools.eq_(correct_role, leg.context_role(term='fake-term'))


@with_setup(setup_func)
def test_current_using_related_bill():
    bill = db.bills.find_one({'_term': '20112012'})
    leg = next(iter(bill.sponsors_manager))
    correct_role = leg['roles'][0]
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))


@with_setup(setup_func)
def test_current_using_related_vote():
    bill = db.bills.find_one({'_term': '20112012'})
    vote = next(bill.votes_manager())
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['roles'][0]
    nose.tools.eq_(correct_role, leg.context_role(vote=vote))


@with_setup(setup_func)
def test_current_using_term_no_matching_roles():
    # If there're multiple roles for a term, return the
    leg = db.legislators.find_one('CAL000104')
    correct_role = ''
    nose.tools.eq_(correct_role, leg.context_role(term='fake-term2'))


@with_setup(setup_func)
def test_current_using_session_no_matching_roles():
    # If there're multiple roles for a term, return the first role in the list.
    leg = db.legislators.find_one('CAL000104')
    correct_role = ''
    nose.tools.eq_(correct_role, leg.context_role(session='fake-session2'))


# Test context_role with for old term, session, bill, vote.
@with_setup(setup_func)
def test_old_using_bill():
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['20092010'][0]
    bill = db.bills.find_one({'_term': '20092010'})
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))


@with_setup(setup_func)
def test_old_using_vote():
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    bill = db.bills.find_one({'_term': '20092010'})
    vote = next(bill.votes_manager())
    nose.tools.eq_(correct_role, leg.context_role(vote=vote))


@with_setup(setup_func)
def test_old_using_session_multiple_roles():
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(session='20092010'))


@with_setup(setup_func)
def test_old_using_session_single_role():
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['fake-session'][0]
    nose.tools.eq_(correct_role, leg.context_role(session='fake-session'))


@with_setup(setup_func)
def test_old_using_term_multiple_roles():
    # If there're multiple roles for a term, return the first role in the list.
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(term='20092010'))


@with_setup(setup_func)
def test_old_using_term_single_role():
    # If there's only one role for a term, return it.
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['fake-session'][0]
    nose.tools.eq_(correct_role, leg.context_role(term='fake-term'))


@with_setup(setup_func)
def test_old_using_related_bill():
    bill = db.bills.find_one({'_term': '20092010'})
    leg = next(iter(bill.sponsors_manager))
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))


@with_setup(setup_func)
def test_old_using_related_vote():
    bill = db.bills.find_one({'_term': '20092010'})
    vote = next(bill.votes_manager())
    leg = db.legislators.find_one('CAL000104')
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(vote=vote))
