import json
import urllib

from django.utils import unittest
from django.test import Client

import billy.tests
from billy.tests import fixtures
from billy.core import db


class BaseTestCase(unittest.TestCase):
    '''The idea with this base class is that each
    endpoint is represented by a test. Each test has
    a url tempalte, url args used to format the url
    template, an http method (defaults to 'GET') and
    an optional dictionary of get or post data.

    The result of the modeled API call is available from
    self.json on the testcase instance.

    The reasoning behind this is that the need for docstrings
    can be reduced by giving the test functions descriptive
    names (like test_correct_keys_present) which also shows
    up in the output from the test runner.
    '''

    tearDown = staticmethod(billy.tests.teardown)

    @property
    def _data(self):
        '''Return class-level 'data', which is GET or POST
        data in the form of a dict, and augment it with the
        api key.
        '''
        data = getattr(self, 'data', {})
        return data

    @property
    def _method(self):
        '''Return the http method for this test, or a default
        method of GET.
        '''
        return getattr(self, 'method', 'GET')

    @property
    def _url_args(self):
        return getattr(self, 'url_args', {})

    @property
    def _url(self):
        return self.url_tmpl.format(**self._url_args)

    def _full_url(self):
        return self._url + '?' + urllib.urlencode(self._data)

    def setUp(self):
        self.client = Client()
        self.db = db
        fixtures.load_metadata()
        fixtures.load_bills()
        fixtures.load_legislators()
        fixtures.load_committees()
        fixtures.load_events()
        fixtures.load_districts()

    @property
    def json(self):
        '''Access this property to get the decoded json
        from the api call represented by this TestCase
        and its class-level attributes.
        '''
        if self._method == 'GET':
            response = self.client.get(self._url, self._data)
        elif self._method == 'POST':
            response = self.client.get(self._url, self._data)
        else:
            raise ValueError('Unit test class %r must have a "method"'
                             ' attribute of "GET" or "POST"' % self)
        self.response = response
        return self.load(response)

    def load(self, http_response):
        return json.loads(http_response.content)

    def assert_200(self):
        try:
            self.json
        except ValueError:
            raise ValueError('no json object: ' + self.response.content)
        self.assertEquals(self.response.status_code, 200)
