from .base import BaseTestCase


class BillsSearchTestCase(BaseTestCase):

    url_tmpl = '/api/v1/bills/'
    data = dict(state='ex', chamber='lower')

    def test_count(self):
        self.assertEquals(
            len(self.json),
            self.db.bills.find(self.data).count())

    def test_correct_keys_present(self):
        expected_keys = set([u'chamber', u'state', u'session', u'title',
                             u'type', u'id', u'bill_id', 'subjects'])
        self.assertEquals(set(self.json[0]), expected_keys)

    def test_status(self):
        self.assert_200()


class BillLookupTestCase(BaseTestCase):

    url_tmpl = '/api/v1/bills/{abbr}/{session}/{bill_id}/'
    url_args = dict(abbr='ex', session='S1', bill_id='AB 1')

    def test_state(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        self.assertEquals(self.json['state'], 'ex')

    def test_correct_keys_present(self):
        expected_keys = set([
            u'votes', u'title', u'alternate_titles', u'country',
            u'companions', u'sponsors', u'actions', u'chamber',
            u'state', u'session', u'action_dates', u'level',
            u'type', u'id', u'bill_id', 'subjects', 'all_ids'])
        self.assertEquals(set(self.json), expected_keys)

    def test_bill_id(self):
        self.assertEquals(self.json['bill_id'], 'AB 1')

    def test_status(self):
        self.assert_200()


class BillyIDTestCase(BaseTestCase):

    url_tmpl = '/api/v1/bills/{billy_bill_id}/'
    url_args = dict(billy_bill_id='EXB00000001')

    def test_state(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        self.assertEquals(self.json['state'], 'ex')

    def test_correct_keys_present(self):
        expected_keys = set([
            u'votes', u'title', u'alternate_titles', u'country',
            u'companions', u'sponsors', u'actions', u'chamber',
            u'state', u'session', u'action_dates', u'level',
            u'type', u'id', u'bill_id', 'subjects', 'all_ids'])
        self.assertEquals(set(self.json), expected_keys)

    def test_bill_id(self):
        self.assertEquals(self.json['bill_id'], 'AB 1')

    def test_status(self):
        self.assert_200()


class SubjectCountTestCase(BaseTestCase):

    url_tmpl = '/api/v1/subject_counts/{abbr}/{session}/'
    url_args = dict(abbr='ex', session='S1')

    def test_count(self):
        self.assertEquals(self.json[u'Labor and Employment'], 1)

    def test_status(self):
        self.assert_200()
