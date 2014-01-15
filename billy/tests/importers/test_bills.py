import copy
from billy.core import db
from billy.importers import bills, names

from nose.tools import with_setup, assert_equal

from .. import fixtures


def setup_func():
    db.bills.drop()
    db.votes.drop()
    db.legislators.drop()
    db.document_ids.drop()
    db.vote_ids.drop()
    db.committees.drop()
    names.__matchers = {}

    fixtures.load_metadata()

    db.legislators.insert({'state': 'ex',
                           '_id': 'EXL000001', 'leg_id': 'EXL000001',
                           'chamber': 'upper',
                           'full_name': 'John Adams', 'first_name': 'John',
                           'last_name': 'Adams', '_scraped_name': 'John Adams',
                           'roles': [
                               {'type': 'member', 'chamber': 'upper',
                                'term': 'T1', 'state': 'ex'}
                           ]
                          })


@with_setup(setup_func)
def test_import_bill():
    companion_data = {'_type': 'bill', 'state': 'ex', 'bill_id': 'A1',
                      'chamber': 'upper', 'session': 'S1',
                      'title': 'companion', 'sponsors': [], 'versions': [],
                      'documents': [], 'votes': [], 'actions': [],
                      'companions': [],
                     }
    data = {'_type': 'bill', 'state': 'ex', 'bill_id': 'S1',
            'chamber': 'upper', 'session': 'S1',
            'subjects': ['Pigs', 'Sheep', 'Horses'],
            'sponsors': [{'name': 'Adams', 'type': 'primary'},
                         {'name': 'Jackson', 'type': 'cosponsor'}],
            'title': 'main title',
            'alternate_titles': ['second title'],
            'companions': [{'bill_id': 'A1', 'session': 'S1', 'chamber': None}
                          ],
            'versions': [{'title': 'old title',
                          'url': 'http://example.com/old'},
                         {'title': 'main title',
                          'url': 'http://example.com/current'},
                         ],
            'documents': [{'title': 'fiscal note',
                          'url': 'http://example.com/fn'}],
            'actions': [{'action': 'Introduced', 'type': ['bill:introduced'],
                         'actor': 'upper', 'date': 1331000000},
                        {'action': 'Referred to committee',
                         'type': ['committee:referred'], 'actor': 'upper',
                         'date': 1332000000},
                        {'action': 'Passed by voice vote',
                         'type': ['bill:passed'], 'actor': 'upper',
                         'date': 1333000000},
                        {'action': 'Signed', 'type': ['governor:signed'],
                         'actor': 'governor', 'date': 1334000000},
                       ],
            'votes': [{'motion': 'passage', 'chamber': 'upper', 'date': None,
                       'yes_count': 1, 'no_count': 1, 'other_count': 0,
                       'yes_votes': ['John Adams'],
                       'no_votes': ['John Quincy Adams'],
                       'other_votes': [],
                      },
                      {'motion': 'referral', 'chamber': 'upper', 'date': None,
                       'yes_count': 0, 'no_count': 0, 'other_count': 0,
                       'yes_votes': [], 'no_votes': [], 'other_votes': [],
                       'committee': 'Committee on Agriculture',
                      }],
           }
    standalone_votes = {
        # chamber, session, bill id -> vote list
        ('upper', 'S1', 'S 1'): [
            {'motion': 'house passage', 'chamber': 'lower', 'date': None,
             'yes_count': 1, 'no_count': 0, 'other_count': 0,
             'yes_votes': [], 'no_votes': [], 'other_votes': [],
            }
        ]
    }

    # deepcopy here so we can reinsert same data without modification
    bills.import_bill(copy.deepcopy(companion_data), {}, None)
    bills.import_bill(copy.deepcopy(data), copy.deepcopy(standalone_votes),
                      None)

    a1 = db.bills.find_one({'bill_id': 'A 1'})
    assert a1['_id'] == 'EXB00000001'

    # test that basics work
    bill = db.bills.find_one({'bill_id': 'S 1'})
    assert bill['_id'] == 'EXB00000002'
    assert bill['bill_id'] == 'S 1'
    assert bill['chamber'] == 'upper'
    assert bill['scraped_subjects'] == data['subjects']
    assert 'subjects' not in bill
    assert bill['_term'] == 'T1'
    assert bill['created_at'] == bill['updated_at']

    # assure sponsors are there and that John Adams gets matched
    assert len(bill['sponsors']) == 2
    assert bill['sponsors'][0]['leg_id'] == 'EXL000001'

    # test vote import
    bill_votes = db.votes.find()
    assert bill_votes.count() == 3
    assert bill_votes[0]['vote_id'] == 'EXV00000001'
    assert bill_votes[0]['yes_votes'][0]['leg_id'] == 'EXL000001'
    assert 'committee_id' in bill_votes[1]

    # test actions
    assert bill['action_dates']['first'] == 1331000000
    assert bill['action_dates']['last'] == 1334000000
    assert bill['action_dates']['passed_upper'] == 1333000000
    assert bill['action_dates']['signed'] == 1334000000
    assert bill['action_dates']['passed_lower'] is None

    # titles from alternate_titles & versions (not main title)
    assert 'main title' not in bill['alternate_titles']
    assert 'second title' in bill['alternate_titles']
    assert 'old title' in bill['alternate_titles']

    # test version/document import
    assert_equal(bill['versions'][0]['doc_id'], 'EXD00000001')
    assert bill['versions'][1]['doc_id'] == 'EXD00000002'
    assert bill['documents'][0]['doc_id'] == 'EXD00000003'

    # test companions
    bill['companions'][0]['internal_id'] == 'EXB000000001'

    # now test an update
    data['versions'].append({'title': 'third title',
                             'url': 'http://example.com/3rd'})
    data['sponsors'].pop()
    bills.import_bill(data, standalone_votes, None)

    # still only two bills
    assert db.bills.count() == 2
    bill = db.bills.find_one('EXB00000002')

    # votes haven't changed, versions, titles, and sponsors have
    bill_votes = db.votes.find()
    assert bill_votes.count() == 3
    assert bill_votes[0]['vote_id'] == 'EXV00000001'
    assert len(bill['versions']) == 3
    assert len(bill['sponsors']) == 1
    assert 'third title' in bill['alternate_titles']
    # check that old doc ids haven't changed, and new one is 4
    assert bill['versions'][0]['doc_id'] == 'EXD00000001'
    assert bill['versions'][1]['doc_id'] == 'EXD00000002'
    assert bill['versions'][2]['doc_id'] == 'EXD00000004'
    assert bill['documents'][0]['doc_id'] == 'EXD00000003'


@with_setup(setup_func)
def test_import_bill_with_partial_bill_vote_id():
    # test a hack added for Rhode Island where vote bill_ids are missing
    # their prefix (ie. 7033 instead of HB 7033)
    # fixture's yz state has _partial_vote_bill_id enabled
    data = {'_type': 'bill', 'state': 'yz', 'bill_id': 'S1',
            'chamber': 'upper', 'session': 'S1a',
            'title': 'main title',
            'sponsors': [],
            'versions': [],
            'documents': [],
            'votes': [],
            'actions': [],
            'companions': [],
           }
    standalone_votes = {
        # chamber, session, bill id -> vote list
        ('upper', 'S1a', '1'): [
            {'motion': 'house passage', 'chamber': 'lower', 'date': None,
             'yes_count': 1, 'no_count': 0, 'other_count': 0,
             'yes_votes': [], 'no_votes': [], 'other_votes': [],
            }
        ]
    }

    bills.import_bill(copy.deepcopy(data), copy.deepcopy(standalone_votes),
                      None)

    bill = db.bills.find_one()
    assert bill['bill_id'] == 'S 1'
    vote = db.votes.find_one()
    assert vote['motion'] == 'house passage'
    assert vote['chamber'] == 'lower'


def test_fix_bill_id():
    expect = 'AB 74'
    bill_ids = ['A.B. 74', 'A.B.74', 'AB74', 'AB 0074',
                'AB074', 'A.B.074', 'A.B. 074', 'A.B\t074']

    for bill_id in bill_ids:
        assert bills.fix_bill_id(bill_id) == expect

    assert bills.fix_bill_id('PR19-0041') == 'PR 19-0041'
    assert bills.fix_bill_id('HB12S-0041') == 'HB 12S-0041'
    assert bills.fix_bill_id('HB 12S-0041') == 'HB 12S-0041'
    assert bills.fix_bill_id(' 999') == '999'
    assert bills.fix_bill_id('999') == '999'
    assert bills.fix_bill_id('SJR AA') == 'SJR AA'
    assert bills.fix_bill_id('SJRAA') == 'SJR AA'


@with_setup(setup_func)
def test_populate_current_fields():
    db.bills.insert({'state': 'ex', 'session': 'S2', 'title': 'current term'})
    db.bills.insert({'state': 'ex', 'session': 'Special2',
                     'title': 'current everything'})
    db.bills.insert({'state': 'ex', 'session': 'S0', 'title': 'not current'})

    bills.populate_current_fields('ex')

    b = db.bills.find_one({'title': 'current everything'})
    assert b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'current term'})
    assert not b['_current_session']
    assert b['_current_term']

    b = db.bills.find_one({'title': 'not current'})
    assert not b['_current_session']
    assert not b['_current_term']


@with_setup(setup_func)
def test_votematcher():
    # three votes, two with the same fingerprint
    votes = [{'motion': 'a', 'chamber': 'b', 'date': 'c',
              'yes_count': 1, 'no_count': 2, 'other_count': 3},
             {'motion': 'x', 'chamber': 'y', 'date': 'z',
              'yes_count': 0, 'no_count': 0, 'other_count': 0},
             {'motion': 'a', 'chamber': 'b', 'date': 'c',
              'yes_count': 1, 'no_count': 2, 'other_count': 3},
            ]
    vm = bills.VoteMatcher('ex')

    vm.set_ids(votes)
    assert votes[0]['vote_id'] == 'EXV00000001'
    assert votes[1]['vote_id'] == 'EXV00000002'
    assert votes[2]['vote_id'] == 'EXV00000003'

    # a brand new matcher has to learn first
    vm = bills.VoteMatcher('ex')
    vm.learn_ids(votes)

    # clear vote_ids & add a new vote
    for v in votes:
        v.pop('vote_id', None)
    votes.insert(2, {'motion': 'f', 'chamber': 'g', 'date': 'h',
                     'yes_count': 5, 'no_count': 5, 'other_count': 5})

    # setting ids now should restore old ids & give the new vote a new id
    vm.set_ids(votes)
    assert votes[0]['vote_id'] == 'EXV00000001'
    assert votes[1]['vote_id'] == 'EXV00000002'
    assert votes[2]['vote_id'] == 'EXV00000004'
    assert votes[3]['vote_id'] == 'EXV00000003'


@with_setup(setup_func)
def test_get_committee_id():
    # 2 committees with the same name, different chamber
    db.committees.insert({'state': 'ex', 'chamber': 'upper',
                          'committee': 'Animal Control', 'subcommittee': None,
                          '_id': 'EXC000001'})
    db.committees.insert({'state': 'ex', 'chamber': 'lower',
                          'committee': 'Animal Control', 'subcommittee': None,
                          '_id': 'EXC000002'})
    # committee w/ subcommittee (also has 'Committee on' prefix)
    db.committees.insert({'state': 'ex', 'chamber': 'upper',
                          'committee': 'Committee on Science',
                          'subcommittee': None, '_id': 'EXC000004'})
    db.committees.insert({'state': 'ex', 'chamber': 'upper',
                          'committee': 'Committee on Science',
                          'subcommittee': 'Space',
                          '_id': 'EXC000005'})

    # simple lookup
    assert (bills.get_committee_id('ex', 'upper', 'Animal Control') ==
            'EXC000001')
    # different chamber
    assert (bills.get_committee_id('ex', 'lower', 'Animal Control') ==
            'EXC000002')
    # without 'Committee on'  (this one also has a subcommittee)
    assert (bills.get_committee_id('ex', 'upper', 'Science') ==
            'EXC000004')
    assert bills.get_committee_id('ex', 'upper', 'Nothing') is None
