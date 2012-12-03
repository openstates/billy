from .base import BaseTestCase


class LegislatorsSearchTestCase(BaseTestCase):

    url_tmpl = '/api/v1/legislators/'
    data = dict(state='ex', active=True)

    def test_count(self):
        self.assertEquals(
            len(self.json),
            self.db.legislators.find(self.data).count())

    def test_correct_keys_present(self):
        expected_keys = set([
            u'first_name', u'last_name', u'middle_name', u'level',
            u'country', u'created_at', u'leg_id', u'state', u'offices',
            u'full_name', u'active', u'suffixes', u'id', u'photo_url'])
        self.assertTrue(expected_keys < set(self.json[0]))

    def test_status(self):
        self.assert_200()


class LegislatorLookupTestCase(BaseTestCase):

    url_tmpl = '/api/v1/legislators/{legislator_id}/'
    url_args = dict(legislator_id='EXL000001')

    def test_state(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        self.assertEquals(self.json['state'], 'ex')

    def test_correct_keys_present(self):
        expected_keys = set([
            u'last_name', u'sources', u'leg_id', u'full_name',
            u'active', u'id', u'photo_url', u'first_name',
            u'middle_name', u'roles', u'level', u'country',
            u'created_at', u'state', u'offices', u'suffixes'])
        self.assertTrue(expected_keys < set(self.json))

    def test_id(self):
        self.assertEquals(self.json['id'], 'EXL000001')

    def test_status(self):
        self.assert_200()
