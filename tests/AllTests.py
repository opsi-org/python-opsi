
__unittest = True

from backend.FileTest import FileTestCase
from backend.MySQLTest import MySQLTestCase
from backend.LdapTest import LdapTestCase
from backend.JsonRPCTest import JSONRPCTestCase
from backend.HostControlTest import HostControlTestCase
#from OPSI.Logger import *

#logger = Logger()
#logger.setSyslogLevel(LOG_NONE)
#logger.setFileLevel(LOG_NONE)
#logger.setConsoleLevel(LOG_DEBUG2)
#logger.setConsoleColor(True)

from opsi_unittest.lib.unittest2.suite import TestSuite
from opsi_unittest.lib.unittest2.case import TestCase
import opsi_unittest.lib.unittest2

test_cases = (FileTestCase,
		MySQLTestCase,
		#LdapTestCase
		JSONRPCTestCase,
		HostControlTestCase)

def load_tests(loader, tests, pattern):
	suite = TestSuite()
	for test_class in test_cases:
		tests = loader.loadTestsFromTestCase(test_class)
		suite.addTests(tests)
	return suite
