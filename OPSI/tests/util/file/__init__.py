import unittest


def test_suite():
	from OPSI.tests.util.file import (
		test_opsibackup
		)
	modules = [
		test_opsibackup
		]
	suites = map(lambda x: x.test_suite(), modules)
	return unittest.TestSuite(suites)