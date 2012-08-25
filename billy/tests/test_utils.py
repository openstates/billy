from billy import utils
from billy.utils import popularity
from billy.core import db

from nose.tools import with_setup


def drop_everything():
    db.metadata.drop()
    db.legislators.drop()
    db.bills.drop()
    db.committees.drop()


@with_setup(drop_everything)
def test_find_bill():
    # simplest case
    db.bills.insert({'bill_id': 'HB 1', 'alternate_bill_ids': []})
    assert utils.find_bill({'bill_id': 'HB 1'})['bill_id'] == 'HB 1'

    # asking for HB/SB 2
    db.bills.insert({'bill_id': 'HB 2', 'alternate_bill_ids': ['SB 2']})
    assert utils.find_bill({'bill_id': 'HB 2'})['bill_id'] == 'HB 2'
    assert utils.find_bill({'bill_id': 'SB 2'})['bill_id'] == 'HB 2'

    # asking for HB 4 should get HB 4, not 3
    db.bills.insert({'bill_id': 'HB 3', 'alternate_bill_ids': ['HB 4']})
    db.bills.insert({'bill_id': 'HB 4', 'alternate_bill_ids': []})
    assert utils.find_bill({'bill_id': 'HB 4'})['bill_id'] == 'HB 4'

    # TODO: also test fields parameter


def test_popularity_counter():
    c = popularity.counter
    c.counts.drop()

    c.inc('bill', 'LAB00000001', abbr='la', session='2011')
    c.inc('bill', 'LAB00000001', abbr='la', session='2011')
    c.inc('bill', 'LAB00000001', abbr='la', session='2011')
    c.inc('bill', 'GAB00000001', abbr='ga', session='2012')

    # test basic top()
    assert c.top('bill')[0] == 'LAB00000001'
    # test with_counts=True
    assert c.top('bill', with_counts=True)[0] == ('LAB00000001', 3)
    # test n=2
    assert c.top('bill', n=2)[1] == 'GAB00000001'
    # test filtering on attributes
    assert c.top('bill', abbr='ga')[0] == 'GAB00000001'
