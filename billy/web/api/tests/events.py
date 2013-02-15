import datetime


from .base import BaseTestCase


class EventsTestCase(BaseTestCase):

    def setUp(self):
        '''Load test data. The API only returns future events, so we need
        to set the 'when' attribute of the test event to a future date.
        '''
        BaseTestCase.setUp(self)
        future_data = datetime.datetime.now() + datetime.timedelta(weeks=1)
        spec = getattr(self, 'data', {})
        self.db.events.find_and_modify(spec, {'$set': {'when': future_data}})


class EventsSearchTestCase(EventsTestCase):

    url_tmpl = '/api/v1/events/'
    data = dict(state='ex')

    def test_count(self):
        self.assertEquals(
            len(self.json),
            self.db.events.find(self.data).count())

    def test_correct_keys_present(self):
        expected_keys = set([
            u'end', u'description', u'level', u'country',
            u'created_at', u'when', u'updated_at', u'sources',
            u'state', u'session', u'location', u'participants',
            u'type', u'id'])

        self.assertEquals(set(self.json[0]), expected_keys)

    def test_status(self):
        self.assert_200()


class EventLookupTestCase(EventsTestCase):

    url_tmpl = '/api/v1/events/{event_id}/'
    url_args = dict(event_id='EXE00000001')

    def test_state(self):
        '''Make sure the returned data has the correct
        level field value.
        '''
        self.assertEquals(self.json['state'], 'ex')

    def test_correct_keys_present(self):
        expected_keys = set([
            u'end', u'description', u'level', u'country', u'created_at',
            u'when', u'updated_at', u'sources', u'state', u'session',
            u'location', u'participants', u'type', u'id'])

        self.assertEquals(set(self.json), expected_keys)

    def test_event_id(self):
        self.assertEquals(self.json['id'], 'EXE00000001')

    def test_status(self):
        self.assert_200()
