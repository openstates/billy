import datetime


bills = [
    {
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
             u'related_entities': []}
        ],
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
        u'type': [u'bill'],
        u'subjects': [u'Labor and Employment']
    },

    {
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
    }
]
