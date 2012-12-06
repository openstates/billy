"""
    Simple tests for committees, events
"""
from nose.tools import assert_raises, assert_equal

from billy.scrape.legislators import Legislator
from billy.scrape.committees import Committee
from billy.scrape.events import Event
from billy.scrape.votes import Vote

import datetime


def test_legislator():
    l = Legislator('T1', 'upper', '1', 'Adam Smith', 'Adam', 'Smith')
    assert_equal(l, {'_type': 'person', 'full_name': 'Adam Smith',
                     'first_name': 'Adam', 'last_name': 'Smith',
                     'middle_name': '', 'suffixes': '', 'roles': [
                         {'chamber': 'upper', 'term': 'T1',
                          'role': 'member', 'start_date': None,
                          'end_date': None, 'district': '1',
                          'party': ''}],
                     'offices': [], 'sources': []})

    l.add_role('committee member', 'T1', committee='Some Committee',
               position='chairman')
    assert_equal(l['roles'][1], {'role': 'committee member', 'term': 'T1',
                                 'start_date': None, 'end_date': None,
                                 'committee': 'Some Committee',
                                 'position': 'chairman'})

    l.add_office('capitol', 'Statehouse Office', '123 Main St', '123-456-7890',
                 '123-555-5555', 'asmith@government.gov')
    assert_equal(l['offices'], [{'type': 'capitol',
                                 'name': 'Statehouse Office',
                                 'address': '123 Main St',
                                 'phone': '123-456-7890',
                                 'fax': '123-555-5555',
                                 'email': 'asmith@government.gov'}])


def test_committee():
    c = Committee('upper', 'committee name')
    c.add_member('Washington', role='chairman')
    c.add_member('Filmore', note='note')

    assert_equal(c['members'],
                 [{'name': 'Washington', 'role': 'chairman'},
                  {'name': 'Filmore', 'role': 'member', 'note': 'note'}])


def test_event():
    e = Event('S1', datetime.datetime(2012, 1, 1), 'meeting',
              'event description', 'event location')
    e.add_document('agenda', 'http://example.com/event/agenda.txt')
    e.add_related_bill('HB 1', relation='considered')
    assert_equal(e['documents'],
                 [{'name': 'agenda',
                   'url': 'http://example.com/event/agenda.txt',
                   'type': 'other'}])
    assert_equal(e['related_bills'],
                 [{'bill_id': 'HB 1', 'relation': 'considered'}])


def test_vote():
    v = Vote('upper', datetime.datetime(2012, 1, 1), 'passage', True,
             3, 1, 2, note='note')
    assert_equal(v, {'chamber': 'upper', 'date': datetime.datetime(2012, 1, 1),
                     'motion': 'passage', 'passed': True, 'yes_count': 3,
                     'no_count': 1, 'other_count': 2, 'type': 'other',
                     'yes_votes': [], 'no_votes': [], 'other_votes': [],
                     'note': 'note', '_type': 'vote', 'sources': []})

    yes_voters = ['Lincoln', 'Adams', 'Johnson']
    map(v.yes, yes_voters)
    assert_equal(v['yes_votes'], yes_voters)

    no_voters = ['Kennedy']
    map(v.no, no_voters)
    assert_equal(v['no_votes'], no_voters)

    other_voters = ['Polk', 'Pierce']
    map(v.other, other_voters)
    assert_equal(v['other_votes'], other_voters)

    # validate should work
    v.validate()

    # now add someone else and make sure it doesn't validate
    v.yes('Clinton')
    with assert_raises(ValueError):
        v.validate()
