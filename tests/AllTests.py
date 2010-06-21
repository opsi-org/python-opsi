
__unittest = True

from backend.FileTest import FileTestCase
#from OPSI.Logger import *

#logger = Logger()
#logger.setSyslogLevel(LOG_NONE)
#logger.setFileLevel(LOG_NONE)
#logger.setConsoleLevel(LOG_DEBUG2)
#logger.setConsoleColor(True)

from OPSI.unittest2.suite import TestSuite
from OPSI.unittest2.case import TestCase
import OPSI.unittest2

test_cases = (FileTestCase,)

def load_tests(loader, tests, pattern):
    suite = TestSuite()
    for test_class in test_cases:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    return suite
