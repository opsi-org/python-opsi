#!/usr/bin/env python
#-*- coding: utf-8 -*-

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from OPSI.Backend.SQLite import SQLiteBackend

# from Backends.SQLite import SQLiteBackendMixin
# from BackendTestMixins import (ConfigStateTestsMixin, LicensesTestMixin,
#     AuditTestsMixin, ConfigTestsMixin, ProductsTestMixin,
#     ExtendedBackendTestsMixin, BackendTestsMixin)


class BackendSQLiteTestCase(unittest.TestCase):
    def testInitialisationDoesNotFail(self):
        backend = SQLiteBackend()
        backend.backend_createBase()


# # This is currently disabled because the tests require a valid modules file.
# class SQLiteBackendTestCase(unittest.TestCase, SQLiteBackendMixin,
#     BackendTestsMixin, ProductsTestMixin, AuditTestsMixin, LicensesTestMixin,
#     ExtendedBackendTestsMixin, ConfigTestsMixin, ConfigStateTestsMixin):
#     """Testing the SQLite backend.

#     This currently requires a valid modules file."""

#     def setUp(self):
#         self.backend = None
#         self.setUpBackend()

#     def tearDown(self):
#         self.tearDownBackend()
#         del self.backend

#     def testWeHaveABackend(self):
#         self.assertNotEqual(None, self.backend)


if __name__ == '__main__':
    unittest.main()