'''
The django test runner looks for unittest.TestCase subclasses
defined in this file, so import any testcases here.
'''
from api_tests.metadata import *
from api_tests.bills import *
from api_tests.legislators import *
from api_tests.committees import *
from api_tests.events import *
from api_tests.auth import *
