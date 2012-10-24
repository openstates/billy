from nose.tools import with_setup

from billy.core import db
from billy.importers import names

from .. import fixtures


def setup_func():
    fixtures.load_metadata()
    db.legislators.drop()
    # TODO: this is kind of a hack, fix it?
    names.__matchers = {}


@with_setup(setup_func)
def test_get_legislator_id():
    db.legislators.insert({'_id': 'EXL000042',
                           'state': 'ex',
                           'full_name': 'Ed Iron Cloud III',
                           '_scraped_name': 'Ed Iron Cloud III',
                           'first_name': 'Ed',
                           'last_name': 'Iron Cloud',
                           'suffixes': 'III',
                           'roles': [{'type': 'member',
                                      'state': 'ex',
                                      'term': 'T1',
                                      'chamber': 'upper',
                                      'district': '10'}]})

    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'Ed Iron Cloud') == 'EXL000042'
    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'Iron Cloud') == 'EXL000042'
    assert names.get_legislator_id('ex', 'S1',
                                   'upper', 'E. Iron Cloud') == 'EXL000042'
    assert not names.get_legislator_id('ex', 'S1', 'lower', 'Ed Iron Cloud')
