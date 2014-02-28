#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from Backends.File import FileBackendMixin
from BackendTestMixins import (ConfigStateTestsMixin, ProductPropertiesTestMixin,
    ProductDependenciesTestMixin, AuditTestsMixin,
    ConfigTestsMixin, ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin, GroupTestsMixin,
    ObjectToGroupTestsMixin, ExtendedBackendTestsMixin, BackendTestsMixin)


class FileBackendTestCase(unittest.TestCase, FileBackendMixin,
    ConfigStateTestsMixin, ProductPropertiesTestMixin, ConfigTestsMixin,
    ProductDependenciesTestMixin, AuditTestsMixin, ProductsTestMixin,
    ProductsOnClientTestsMixin, ProductsOnDepotTestsMixin,
    ProductPropertyStateTestsMixin, GroupTestsMixin, ObjectToGroupTestsMixin,
    ExtendedBackendTestsMixin, BackendTestsMixin):
    """
    Testing the file backend.

    There is no license backend test, because that information gets not
    stored in the file backend.
    """
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testMethod(self):
        self.assertNotEqual(None, self.backend)


if __name__ == '__main__':
    unittest.main()
