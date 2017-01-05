from nose.tools import with_setup, assert_equal

from billy.core import db
from billy.importers.subjects import SubjectCategorizer
from .. import fixtures


def setup_func():
    fixtures.load_metadata()
    db.bills.drop()
    db.subjects.drop()


@with_setup(setup_func)
def test_basic_categorization():

    db.subjects.insert({'abbr': 'ex', 'remote': 'AK-47',
                        'normal': ['Guns', 'Crime']})
    db.subjects.insert({'abbr': 'ex', 'remote': 'Hunting', 'normal': ['Guns']})
    db.subjects.insert({'abbr': 'ex', 'remote': 'Candy', 'normal': ['Food']})

    categorizer = SubjectCategorizer('ex')

    # simple
    bill = {'scraped_subjects': ['AK-47']}
    categorizer.categorize_bill(bill)
    bill['subjects'] = sorted(bill['subjects'])

    assert_equal(bill, {'scraped_subjects': ['AK-47'],
                        'subjects': [u'Crime', u'Guns']})

    # no subjects
    bill = {'scraped_subjects': ['Welfare']}
    categorizer.categorize_bill(bill)
    bill['subjects'] = sorted(bill['subjects'])
    assert_equal(bill, {'scraped_subjects': ['Welfare'],
                        'subjects': []})

    # two subjects
    bill = {'scraped_subjects': ['AK-47', 'Candy']}
    categorizer.categorize_bill(bill)
    bill['subjects'] = sorted(bill['subjects'])
    assert_equal(bill['subjects'], [u'Crime', u'Food', u'Guns'])

    # avoid duplicates
    bill = {'scraped_subjects': ['AK-47', 'Hunting']}
    categorizer.categorize_bill(bill)
    bill['subjects'] = sorted(bill['subjects'])
    assert_equal(bill, {'scraped_subjects': ['AK-47', 'Hunting'],
                        'subjects': [u'Crime', u'Guns']})


@with_setup(setup_func)
def test_all_bills_categorization():

    db.subjects.insert({'abbr': 'ex', 'remote': 'AK-47',
                        'normal': ['Guns', 'Crime']})
    db.subjects.insert({'abbr': 'ex', 'remote': 'Hunting', 'normal': ['Guns']})
    db.subjects.insert({'abbr': 'ex', 'remote': 'Candy', 'normal': ['Food']})

    categorizer = SubjectCategorizer('ex')

    # can insert dummy bills w/ state
    bills = [{'scraped_subjects': ['AK-47'], 'bill_id': '1', 'state': 'ex'},
             {'scraped_subjects': ['Welfare'], 'bill_id': '2', 'state': 'ex'},
             {'scraped_subjects': ['AK-47', 'Candy'], 'bill_id': '3',
              'state': 'ex'},
             {'scraped_subjects': ['AK-47', 'Hunting'], 'bill_id': '4',
              'state': 'ex'}]
    map(db.bills.insert, bills)

    # run categorization on all bills
    categorizer.categorize_bills()

    # simple
    bill = db.bills.find_one({'bill_id': '1'})
    assert_equal(set(bill['subjects']), set([u'Guns', u'Crime']))

    # no subjects
    bill = db.bills.find_one({'bill_id': '2'})
    assert_equal(bill['subjects'], [])

    # two subjects
    bill = db.bills.find_one({'bill_id': '3'})
    assert_equal(set(bill['subjects']), set([u'Guns', u'Crime', u'Food']))

    # avoid duplicates
    bill = db.bills.find_one({'bill_id': '4'})
    assert_equal(set(bill['subjects']), set([u'Guns', u'Crime']))
