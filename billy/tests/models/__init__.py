import datetime
from billy.models import db

from .. import fixtures


def setup_func():
    assert db.name.endswith('_test')
    db.bills.drop()
    db.legislators.drop()
    db.document_ids.drop()
    db.votes.drop()
    db.vote_ids.drop()
    db.committees.drop()

    fixtures.load_metadata()

    db.legislators.insert({
        u'_all_ids': [u'EXL000001'],
        u'_id': u'EXL000001',
        u'_locked_fields': [u'full_name'],
        u'_type': u'person',
        u'active': True,
        u'country': u'us',
        u'created_at': datetime.datetime(2010, 7, 9, 17, 19, 48, 768000),
        u'first_name': u'Larry',
        u'full_name': u'Larry FakeLegislator1',
        u'last_name': u'FakeLegislator1',
        u'leg_id': u'CAL000001',
        u'level': u'state',
        u'middle_name': u'',
        u'offices': [],
        u'photo_url': u'http://cssrc.us/lib/uploads/1/Cox_Standard.jpg',
        u'roles': [],
        u'sources': [{u'url': u'ftp://www.leginfo.ca.gov/pub/bill/'}],
        u'state': u'ex',
        u'suffixes': u'',
        u'roles': [{
            u'chamber': u'lower',
            u'district': u'1',
            u'end_date': None,
            u'party': u'Democratic',
            u'start_date': None,
            u'state': u'ex',
            u'term': u'T1',
            u'type': u'member'},

            {u'chamber': u'lower',
             u'committee': u'Standing Committee on Phony',
             u'committee_id': u'EXC000001',
             u'state': u'ex',
             u'subcommittee': None,
             u'term': u'T1',
             u'type': u'committee member'}],
    })

    db.legislators.insert({
        u'_all_ids': [u'EXL000002'],
        u'_id': u'EXL000002',
        u'_locked_fields': [u'full_name'],
        u'_type': u'person',
        u'active': True,
        u'country': u'us',
        u'created_at': datetime.datetime(2010, 7, 9, 17, 19, 48, 768000),
        u'first_name': u'Curly',
        u'full_name': u'Curly FakeLegislator2',
        u'last_name': u'FakeLegislator2',
        u'leg_id': u'EXL000002',
        u'level': u'state',
        u'middle_name': u'',
        u'state': u'ex',
        u'suffixes': u'',
        u'roles': [
            {
                u'chamber': u'lower',
                u'district': u'2',
                u'end_date': None,
                u'party': u'Democratic',
                u'start_date': None,
                u'state': u'ex',
                u'term': u'T1',
                u'type': u'member'},
            {
                u'chamber': u'lower',
                u'committee': u'Standing Committee on Phony',
                u'committee_id': u'EXC000001',
                u'state': u'ex',
                u'subcommittee': None,
                u'term': u'T1',
                u'type': u'committee member'}],
    })

    db.legislators.insert({
        u'_all_ids': [u'EXL000003'],
        u'_id': u'EXL000003',
        u'_locked_fields': [u'full_name'],
        u'_type': u'person',
        u'active': True,
        u'country': u'us',
        u'created_at': datetime.datetime(2010, 7, 9, 17, 19, 48, 768000),
        u'first_name': u'Moe',
        u'full_name': u'Moe FakeLegislator3',
        u'last_name': u'FakeLegislator3',
        u'leg_id': u'EXL000003',
        u'level': u'state',
        u'middle_name': u'',
        u'state': u'ex',
        u'suffixes': u'',
        u'roles': [{
            u'chamber': u'lower',
            u'district': u'3',
            u'end_date': None,
            u'party': u'Democratic',
            u'start_date': None,
            u'state': u'ex',
            u'term': u'T1',
            u'type': u'member'},

            {
                u'chamber': u'lower',
                u'committee': u'Standing Committee on Fakeness',
                u'committee_id': u'EXC000002',
                u'state': u'ex',
                u'subcommittee': None,
                u'term': u'T1',
                u'type': u'committee member'
            }
        ],
    })

    # Insert an extra LOL legislator, to confirm model methods are
    # only returning a subset of the mongo records.
    db.legislators.insert({
        u'_all_ids': [u'LOL000001'],
        u'_id': u'LOL000001',
        u'_locked_fields': [u'full_name'],
        u'_type': u'person',
        u'active': True,
        u'country': u'us',
        u'created_at': datetime.datetime(2010, 7, 9, 17, 19, 48, 768000),
        u'first_name': u'NYAN',
        u'full_name': u'NYAN CAT',
        u'last_name': u'CAT',
        u'leg_id': u'LOL000001',
        u'level': u'state',
        u'middle_name': u'',
        u'state': u'LO',
        u'suffixes': u'',
        u'roles': [{
            u'chamber': u'lower',
            u'district': u'A',
            u'end_date': None,
            u'party': u'Democratic',
            u'start_date': None,
            u'state': u'LO',
            u'term': u'T1',
            u'type': u'member'},

            {u'chamber': u'lower',
             u'committee': u'Standing Committee on Fakeness',
             u'committee_id': u'EXC000002',
             u'state': u'LO',
             u'subcommittee': None,
             u'term': u'T1',
             u'type': u'committee member'}],
    })

    db.committees.insert({
        u'_all_ids': [u'EXC000001'],
        u'_id': u'EXC000001',
        u'_type': u'committee',
        u'chamber': u'lower',
        u'committee': u'Standing Committee on Phony',
        u'country': u'us',
        u'level': u'state',
        u'members': [
            {u'+chamber': u'lower',
             u'leg_id': u'EXL000001',
             u'name': u'Larry FakeLegislator1',
             u'role': u'member'},
            {u'+chamber': u'lower',
             u'leg_id': u'EXL000002',
             u'name': u'Curly FakeLegislator2',
             u'role': u'Vice Chair'}],
        u'parent_id': None,
        u'state': u'ex',
        u'subcommittee': None,
        u'updated_at': datetime.datetime(2012, 8, 26, 0, 37, 49, 402000)})

    db.committees.insert({
        u'_all_ids': [u'EXC000002'],
        u'_id': u'EXC000002',
        u'_type': u'committee',
        u'chamber': u'lower',
        u'committee': u'Standing Committee on Fakeness',
        u'country': u'us',
        u'level': u'state',
        u'members': [
            {u'+chamber': u'lower',
             u'leg_id': u'EXL000003',
             u'name': u'Moe FakeLegislator3',
             u'role': u'chair'}],
        u'parent_id': None,
        u'state': u'ex',
        u'subcommittee': None,
        u'updated_at': datetime.datetime(2012, 8, 26, 0, 37, 49, 402000)})

    db.votes.insert({
        u'_id': u'EXV00000001',
        u'_type': u'vote',
        u'_voters': [u'EXL000001', u'EXL000002', u'EXL000003'],
        u'bill_id': u'EXB00000001',
        u'chamber': u'upper',
        u'date': datetime.datetime(2011, 3, 7, 0, 0),
        u'motion': u'Fake motion',
        u'no_count': 1,
        u'no_votes': [{u'leg_id': u'EXL000003', u'name': u'FakeLegislator3'}],
        u'other_count': 0,
        u'other_votes': [],
        u'passed': True,
        u'state': u'ex',
        u'type': u'other',
        u'vote_id': u'EXV00000001',
        u'yes_count': 2,
        u'yes_votes': [
            {u'leg_id': u'EXL000001', u'name': u'FakeLegislator1'},
            {u'leg_id': u'EXL000002', u'name': u'FakeLegislator2'},
        ]})

    db.bills.insert({
        u'_all_ids': [u'EXB00000001'],
        u'_current_session': True,
        u'_current_term': True,
        u'_id': u'EXB00000001',
        u'_term': u'T1',
        u'_type': u'bill',
        u'action_dates': {
            u'first': datetime.datetime(2011, 1, 7, 0, 0),
            u'last': datetime.datetime(2011, 4, 15, 0, 0),
            u'passed_lower': datetime.datetime(2011, 4, 15, 0, 0),
            u'passed_upper': None,
            u'signed': None
        },
        u'actions': [
            {u'action': u'Fake Passed',
             u'actor': u'lower',
             u'date': datetime.datetime(2011, 8, 24, 0, 0),
             u'related_entities': [],
             u'type': [u'bill:passed']},
            {u'action': u'Fake introduced',
             u'actor': u'lower',
             u'date': datetime.datetime(2012, 1, 23, 0, 0),
             u'related_entities': []}],
        u'type': [u'bill:introduced'],
        u'alternate_titles': [],
        u'bill_id': u'AB 1',
        u'chamber': u'lower',
        u'companions': [],
        u'country': u'us',
        u'level': u'state',
        u'session': u'S1',
        u'sponsors': [
            {u'leg_id': u'EXL000001',
             u'name': u'FakeLegislator1',
             u'type': u'primary'}],
        u'state': u'ex',
        u'title': u'A fake act.',
        u'type': [u'bill']
    })

    db.bills.insert({
        u'_all_ids': [u'LOB00000001'],
        u'_current_session': True,
        u'_current_term': True,
        u'_id': u'LOB00000001',
        u'_term': u'T1',
        u'_type': u'bill',
        u'action_dates': {
            u'first': datetime.datetime(2011, 1, 7, 0, 0),
            u'last': datetime.datetime(2011, 4, 15, 0, 0),
            u'passed_lower': datetime.datetime(2011, 4, 15, 0, 0),
            u'passed_upper': None,
            u'signed': None
        },
        u'actions': [
            {u'action': u'LOL Passed',
             u'actor': u'lower',
             u'date': datetime.datetime(2011, 8, 24, 0, 0),
             u'related_entities': [],
             u'type': [u'bill:passed']},
            {u'action': u'LOL introduced',
             u'actor': u'lower',
             u'date': datetime.datetime(2012, 1, 23, 0, 0),
             u'related_entities': []}],
        u'type': [u'bill:introduced'],
        u'alternate_titles': [],
        u'bill_id': u'HB 1',
        u'chamber': u'lower',
        u'companions': [],
        u'country': u'us',
        u'level': u'state',
        u'session': u'S1',
        u'sponsors': [
            {u'leg_id': u'LOL000001',
             u'name': u'NYAN CAT',
             u'type': u'primary'}],
        u'state': u'ex',
        u'title': u'A fake act.',
        u'type': [u'bill']
    })
