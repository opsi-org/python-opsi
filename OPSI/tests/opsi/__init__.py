import unittest


def test_suite():
	from tests.opsi import (
		test_application,
		test_logger
		)
	modules = [
		test_application,
		test_logger
		]
	suites = map(lambda x: x.test_suite(), modules)
	return unittest.TestSuite(suites)

