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
from billy.models.base import db


def setup_func():

    # Wipe any any residual data in the test database.
    db.metadata.drop()
    db.bills.drop()
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
            ]
        },
        "party": "Democratic",
        "roles": [
            {
                "chamber": "lower",
                "district": "13",
                "end_date": None,
                "party": "Democratic",
                "start_date": None,
                "state": "ca",
                "term": "20112012",
                "type": "member"
            },
            {
                "chamber": "joint",
                "committee": "Joint Committee on Arts",
                "committee_id": "CAC000356",
                "state": "ca",
                "subcommittee": None,
                "term": "20112012",
                "type": "committee member"
            },
        ],
        "state": "ca",
        })

    db.metadata.insert({
        u'_id': u'ca',
        u'_type': u'metadata',
        u'abbreviation': u'ca',
        u'legislature_name': u'California State Legislature',
        u'lower_chamber_name': u'Assembly',
        u'lower_chamber_term': 2,
        u'lower_chamber_title': u'Assemblymember',
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
            u'20112012 Special Session 1': {
                u'display_name': u'2011-2012, 1st Special Session',
                u'type': u'special'}},

        u'terms': [{
            u'+start_date': datetime.datetime(2008, 12, 1, 0, 0),
            u'end_year': 2010,
            u'name': u'20092010',
            u'sessions': [
                u'20092010',
                u'20092010 Special Session 1',
                u'20092010 Special Session 2',
                u'20092010 Special Session 3',
                u'20092010 Special Session 4',
                u'20092010 Special Session 5',
                u'20092010 Special Session 6',
                u'20092010 Special Session 7',
                u'20092010 Special Session 8'],
           u'start_year': 2009},
          {u'+start_date': datetime.datetime(2010, 12, 6, 0, 0),
           u'end_year': 2012,
           u'name': u'20112012',
           u'sessions': [u'20112012 Special Session 1', u'20112012'],
           u'start_year': 2011}],
         u'upper_chamber_name': u'Senate',
         u'upper_chamber_term': 4,
         u'upper_chamber_title': u'Senator',
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
        u'alternate_titles': [u'An act to amend Sections 226, 3351, 3352, 3551, 3708, 3715, 6303, and 6314 of, to repeal Section 4156 of, and to add Part 4.5 (commencing with Section 1450) to Division 2 of, the Labor Code, relating to domestic work employees.'],
        u'bill_id': u'AB 889',
        u'chamber': u'lower',
        u'country': u'us',
        u'created_at': datetime.datetime(2011, 3, 24, 20, 45, 24, 16000),
        u'documents': [],
        u'level': u'state',
        u'session': u'20112012',
        u'sources': [{u'url': u'http://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=201120120AB889'}],
        u'sponsors': [
            {u'leg_id': u'CAL000104',
             u'name': u'Ammiano',
             u'official_type': u'LEAD_AUTHOR',
             u'type': u'primary'},
             ],
        u'state': u'ca',
        'votes': [dict(vote, date=datetime.datetime(2011, 12, 6, 0, 0))]
        })

    # A prior session bill, where prior is 20092010.
    db.bills.insert({
        u'_all_ids': [u'CAB00005131'],
        u'_id': u'CAB00005131',
        u'_term': u'20092010',
        u'_type': u'bill',
        u'actions': [
            {u'action': u'Introduced. To print.',
            u'actor': u'lower (Desk)',
            u'date': datetime.datetime(2009, 7, 24, 0, 0),
            u'type': [u'bill:introduced']},
            {u'action': u'From printer.',
            u'actor': u'lower (Desk)',
            u'date': datetime.datetime(2009, 7, 27, 0, 0),
            u'type': [u'other']}],
        u'chamber': u'lower',
        u'country': u'us',
        u'session': u'20092010 Special Session 4',
        u'sponsors': [
            {u'leg_id': u'CAL000104', u'name': u'Ammiano', u'type': u'cosponsor'},
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


# @with_setup(setup_func)
# def test_current_role():
#     leg = db.legislators.find_one()
#     correct_role = leg['roles'][0]
#     bill = db.bills.find_one({'_term': '20112012'})

#     # With bill as the argument.
#     nose.tools.set_trace()
#     nose.tools.eq_(correct_role, leg.context_role(bill=bill))

#     # With vote as the argument.
#     vote = next(bill.votes_manager())
#     nose.tools.eq_(correct_role, leg.context_role(vote=vote))

#     # With session as the argument.
#     nose.tools.eq_(correct_role, leg.context_role(session='20112012'))

#     # With term as the argument.
#     nose.tools.eq_(correct_role, leg.context_role(term='20112012'))


@with_setup(setup_func)
def test_old_using_bill():
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    bill = db.bills.find_one({'_term': '20092010'})
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))


@with_setup(setup_func)
def test_old_using_vote():
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    bill = db.bills.find_one({'_term': '20092010'})
    nose.tools.set_trace()
    vote = next(bill.votes_manager())
    nose.tools.eq_(correct_role, leg.context_role(vote=vote))


@with_setup(setup_func)
def test_old_using_session():
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(session='20092010'))


@with_setup(setup_func)
def test_old_using_term():
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(term='20092010'))


@with_setup(setup_func)
def test_old_using_related_bill():
    bill = db.bills.find_one({'_term': '20092010'})
    leg = next(bill.sponsors_manager)
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role())


@with_setup(setup_func)
def test_old_using_related_vote():
    bill = db.bills.find_one({'_term': '20092010'})
    vote = next(bill.votes_manager)
    nose.tools.set_trace()
    leg = db.legislators.find_one()
    correct_role = leg['old_roles']['20092010'][0]
    nose.tools.eq_(correct_role, leg.context_role(bill=bill))
