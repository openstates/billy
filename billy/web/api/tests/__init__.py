# flake8: noqa  (because we import * for a decent reason)
'''
The django test runner looks for unittest.TestCase subclasses
defined in this file, so import any testcases here.
'''
from .test_metadata import *
from .test_bills import *
from .test_legislators import *
from .test_committees import *
from .test_events import *
from .test_districts import *
from .test_boundaries import *
