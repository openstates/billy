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

def _check_results( one, two ):
    return set(one) == set(two)

def _test_logic( name ):
    leg1, leg2, compare = _load_test_data( name )
    produced = merge_legislators( leg1, leg2 )
    assert _check_results( produced, compare ) == True
##########
# Cut below the line

def test_legid_sanity():
    _test_logic( "leg_id_sanity" )

def test_scraped_name_sanity():
    _test_logic( "scraped_name_sanity" )
