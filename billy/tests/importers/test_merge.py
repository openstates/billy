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
    if one != two:
        print ""
        print one
        print two
        print ""
    return one == two

def _test_logic( name ):
    leg1, leg2, compare = _load_test_data( name )
    produced, to_del = merge_legislators( leg1, leg2 )
    assert _check_results( produced, compare ) == True


##########
# Cut below the line

def test_legid_sanity():
    _test_logic( "leg_id_sanity" )

def test_scraped_name_sanity():
    _test_logic( "scraped_name_sanity" )

def test_locked_sanity():
    _test_logic( "locked_field_sanity" )

def test_role_migration():
    _test_logic( "role_conflict" )

def test_role_migration_two():
    _test_logic( "role_conflict_with_prev_roles" )

def test_vanishing_photo():
    _test_logic( "vanishing_photo_url" )

def test_order():
    _test_logic( "test_legi_order" )
