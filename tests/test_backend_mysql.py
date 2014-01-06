#!/usr/bin/env python
#-*- coding: utf-8 -*-

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import Backends.MySQL as MySQLBackend
from BackendTestMixins import BackendTestMixin


@unittest.skipIf(not MySQLBackend.MySQLconfiguration,
    'no MySQL backend configuration given.')
class MySQLBackendTestCase(unittest.TestCase, MySQLBackend.MySQLBackendMixin, BackendTestMixin):
    """
    Testing the MySQL backend.

    Please make sure to have a valid configuration given in Backends/config.
    You also need to have a valid modules file with enabled MySQL backend.
    """
    def setUp(self):
        self.backend = None
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()
        del self.backend

    def testWeHaveABackend(self):
        self.assertNotEqual(None, self.backend)


if __name__ == '__main__':
    unittest.main()