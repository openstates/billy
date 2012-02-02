# Copyright (c) Sunlight Labs, 2012, under the terms and conditions layed out
# in the LICENSE file.

from billy.importers.utils import merge_legislators

import json
import os

def _load_test_data( test_name ):
    test_data = os.path.join( os.path.dirname( os.path.dirname(__file__)),
        "leg_merge_test_data" )
    folder = "%s/%s/" % ( test_data, test_name )
    leg1 = json.loads(open( folder + "1.json", 'r' ).read())
    leg2 = json.loads(open( folder + "2.json", 'r' ).read())
    mrgd = json.loads(open( folder + "merged.json", 'r' ).read())
    
    return ( leg1, leg2, mrgd )

def delt(a, b):
    return dict([
        (key, b.get(key, a.get(key)))
        for key in set(a.keys() + b.keys())
        if (key in a and (not key in b or set(b[key]) != set(a[key])))
        or (key in b and (not key in a or set(a[key]) != set(b[key])))
    ])

def _check_results( one, two ):
    delta = delt(one, two)
    if delta != {}:
        print ""
        print "One:", one
        print ""
        print "Two:", two
        print ""
        print "Delta:", delta
        print ""
    return delta == {}


def _test_logic( name ):
    leg1, leg2, compare = _load_test_data( name )
    produced = merge_legislators( leg1, leg2 )
    assert _check_results( produced, compare ) == True
##########
# Cut below the line

def test_silly_delt_fn():
    l1 = { "foo" : [ "1", "2" ] }
    l2 = { "foo" : [ "2", "1" ] }
    assert delt( l1, l2 ) == {}

def test_legid_sanity():
    _test_logic( "leg_id_sanity" )

def test_scraped_name_sanity():
    _test_logic( "scraped_name_sanity" )

def test_locked_sanity():
    _test_logic( "locked_field_sanity" )
