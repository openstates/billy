from .base import BaseTestCase


class AllMetadataTestCase(BaseTestCase):

    url_tmpl = '/api/v1/metadata/'

    def test_length(self):
        '''Make sure all known metadata entries are being
        returned.
        '''
        self.assertEquals(
            len(self.json),
            self.db.metadata.count())

    def test_ids(self):
        '''Make sure the same ids are being returned thru
        the api and database.
        '''
        api_data = self.json
        database_data = self.db.metadata.find()

        api_ids = [x['abbreviation'] for x in api_data]
        database_ids = [x['_id'] for x in database_data]
        self.assertEquals(api_ids, database_ids)

    def test_status(self):
        self.assert_200()


class StateMetadataTestCase(BaseTestCase):

    url_tmpl = '/api/v1/metadata/{abbr}/'
    url_args = dict(abbr='ex')

    def test_id(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        api_data = self.json
        self.assertEquals(api_data['id'], 'ex')

    def test_status(self):
        self.assert_200()
