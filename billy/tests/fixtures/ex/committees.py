import datetime


committees = [
    {
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
        u'updated_at': datetime.datetime(2012, 8, 26, 0, 37, 49, 402000)
    },
    {
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
        u'updated_at': datetime.datetime(2012, 8, 26, 0, 37, 49, 402000)
    }
]
