from nose.tools import with_setup

from billy.core import db
from billy.importers import committees
from billy.importers import names

from .. import fixtures


def setup_func():
    db.legislators.drop()
    db.committees.drop()
    names.__matchers = {}

    fixtures.load_metadata()

    leg_a = {'full_name': 'Richard Feynman', 'leg_id': 'EXL000001',
             '_id': 'EXL000001',
             '_all_ids': ['EXL000001'],
             'state': 'ex',
             '_scraped_name': 'Richard Feynman', 'first_name': 'Richard',
             'last_name': 'Feynman',
             'roles': [
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'member'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
             ],
             'sources': [{'url': 'http://example.com/feynman'}],
            }
    leg_b = {'full_name': 'Albert Einstein', 'leg_id': 'EXL000002',
             '_id': 'EXL000002',
             '_all_ids': ['EXL000002'],
             'state': 'ex',
             '_scraped_name': 'Albert Einstein', 'first_name': 'Albert',
             'last_name': 'Einstein',
             'roles': [
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'member'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'position': 'chairman',
                  'type': 'committee member', 'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
                 {'state': 'ex', 'term': 'T1', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Appropriations'},
             ],
             'sources': [{'url': 'http://example.com/einstein'}],
            }
    # in a different term
    leg_c = {'full_name': 'Werner Heisenberg', 'leg_id': 'EXL000003',
             '_id': 'EXL000003',
             '_all_ids': ['EXL000003'],
             'state': 'ex',
             '_scraped_name': 'Werner Heisenberg', 'first_name': 'Werner',
             'last_name': 'Heisenberg',
             'roles': [
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'member'},
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture'},
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Agriculture',
                  'subcommittee': 'Tractors'},
                 {'state': 'ex', 'term': 'T0', 'chamber': 'upper',
                  'type': 'committee member', 'committee': 'Appropriations'},
             ],
             'sources': [{'url': 'http://example.com/einstein'}],
            }

    db.legislators.insert(leg_a)
    db.legislators.insert(leg_b)
    db.legislators.insert(leg_c)


@with_setup(setup_func)
def test_committees_from_legislators():
    committees.import_committees_from_legislators('T1', 'ex')

    # 3 overall
    assert db.committees.count() == 3

    ag_com = db.committees.find_one({'_id': 'EXC000001'})
    assert ag_com['subcommittee'] is None
    assert ag_com['members'][0]['leg_id'] == 'EXL000001'
    # Heisenberg isn't added (wrong term)
    assert len(ag_com['members']) == 2
    # sources are copied over too
    assert len(ag_com['sources']) == 2
    assert ag_com['members'][0]['role'] == 'member'
    # check that position is copied over
    assert ag_com['members'][1]['role'] == 'chairman'

    # check that state is copied over
    assert ag_com['state'] == 'ex'

    # subcommittee
    tractor_subcom = db.committees.find_one({'subcommittee': 'Tractors'})
    assert tractor_subcom['committee'] == 'Agriculture'
    assert tractor_subcom['_id'] == 'EXC000002'

    # make sure that committee_ids are added to legislators
    feynman = db.legislators.find_one({'leg_id': 'EXL000001'})
    assert 'committee_id' in feynman['roles'][1]


@with_setup(setup_func)
def test_import_committee():
    committee = {'_type': 'committee', 'state': 'ex',
                 'chamber': 'joint', 'committee': 'Reptilian Task Force',
                 'members': [
                     {'name': 'Richard Feynman', 'role': 'Vice-Chair'},
                     {'name': 'A. Einstein', 'role': 'Chair'},
                 ]
                }

    committees.import_committee(committee, 'S1', 'T1')

    com = db.committees.find_one()
    assert com
    assert com['_id'] == 'EXC000001'
    assert com['committee'] == 'Reptilian Task Force'
    assert com['created_at'] == com['updated_at']
    assert com['members'][0]['leg_id'] == 'EXL000001'
    assert com['members'][1]['name'] == 'A. Einstein'

    leg = db.legislators.find_one({'_id': 'EXL000001'})
    assert leg['roles'][-1] == {'term': 'T1',
                                'committee_id': 'EXC000001',
                                'chamber': 'joint',
                                'state': 'ex',
                                'type': 'committee member',
                                'committee': 'Reptilian Task Force',
                                'position': 'Vice-Chair'
                               }
