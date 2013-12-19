#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from Backends.MySQL import MySQLBackendMixin
from BackendTestMixins import BackendTestMixin
# from BackendTestMixins import (ConfigStateTestsMixin, ProductPropertiesTestMixin,
#     ProductDependenciesTestMixin, AuditTestsMixin,
#     ConfigTestsMixin, ProductsTestMixin, ProductsOnClientTestsMixin,
#     ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin, GroupTestsMixin,
#     ObjectToGroupTestsMixin, ExtendedBackendTestsMixin, BackendTestsMixin)


class MySQLBackendTestCase(unittest.TestCase, MySQLBackendMixin, BackendTestMixin):
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