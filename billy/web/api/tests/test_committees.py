from .base import BaseTestCase


class CommitteesSearchTestCase(BaseTestCase):

    url_tmpl = '/api/v1/committees/'
    data = dict(state='ex', chamber='lower')

    def test_count(self):
        self.assertEquals(
            len(self.json),
            self.db.committees.find(self.data).count())

    def test_correct_keys_present(self):
        expected_keys = set([
            u'level', u'country', u'updated_at', u'parent_id',
            u'state', u'subcommittee', u'committee', u'chamber', u'id', 'all_ids'])
        self.assertEquals(set(self.json[0]), expected_keys)

    def test_status(self):
        self.assert_200()


class CommitteeLookupTestCase(BaseTestCase):

    url_tmpl = '/api/v1/committees/{committee_id}/'
    url_args = dict(committee_id='EXC000001')

    def test_state(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        self.assertEquals(self.json['state'], 'ex')

    def test_correct_keys_present(self):
        expected_keys = set([
            u'members', u'level', u'country', u'updated_at',
            u'parent_id', u'state', u'subcommittee',
            u'committee', u'chamber', u'id', 'all_ids'])
        self.assertEquals(set(self.json), expected_keys)

    def test_id(self):
        self.assertEquals(self.json['id'], 'EXC000001')

    def test_status(self):
        self.assert_200()
