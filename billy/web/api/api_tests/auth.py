from django.utils import unittest
# from django.test import Client


class TestAuth(unittest.TestCase):
    '''I tried to write a test to get the expected
    response/code if no api key is given but couldn'try:
        get it to work.
    '''

    # def test_no_api_key(self):
    #     resp = Client().get('/api/v1/metadata/ex/')
    #     import ipdb;ipdb.set_trace()
