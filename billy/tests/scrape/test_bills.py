from nose.tools import assert_raises, assert_equal

from billy.scrape.bills import Bill

# separate test for duplicate versions to add_version


def test_type():
    # one
    b = Bill('S1', 'upper', 'SB1', 'multiple-types')
    assert b['type'] == ['bill']

    # one
    b = Bill('S1', 'upper', 'SB1', 'multiple-types', type='resolution')
    assert b['type'] == ['resolution']

    # multi
    b = Bill('S1', 'upper', 'SB1', 'multiple-types',
             type=['resolution', 'constitutional amendment'])
    assert b['type'] == ['resolution', 'constitutional amendment']


def test_on_duplicate():
    b = Bill('S1', 'upper', 'SB1', 'on_duplicate')
    b.add_version('current', 'http://example.com/doc/1', mimetype='text/html')

    # error
    with assert_raises(ValueError):
        b.add_version('current', 'http://example.com/doc/1',
                      mimetype='text/html', on_duplicate='error')

    # or without it set, default to error
    with assert_raises(ValueError):
        b.add_version('current', 'http://example.com/doc/1',
                      mimetype='text/html')

    # use_old - keep version name the same
    b.add_version('updated name', 'http://example.com/doc/1',
                  mimetype='text/html', on_duplicate='use_old')
    assert_equal(b['versions'], [{'mimetype': 'text/html',
                                  'url': 'http://example.com/doc/1',
                                  'name': 'current'}])

    # use_new - keep version name the same
    b.add_version('updated name', 'http://example.com/doc/1',
                  mimetype='text/html', on_duplicate='use_new')
    assert_equal(b['versions'], [{'mimetype': 'text/html',
                                  'url': 'http://example.com/doc/1',
                                  'name': 'updated name'}])

    # a new document w/ same name is ok though
    b.add_version('updated name', 'http://example.com/doc/2',
                  mimetype='text/html', on_duplicate='use_old')
    assert len(b['versions']) == 2

    # and now we add a duplicate
    b.add_version('current', 'http://example.com/doc/1',
                  mimetype='text/html', on_duplicate='ignore')
    assert len(b['versions']) == 3
