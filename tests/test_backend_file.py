#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing the opsi file backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .helpers import unittest

from OPSI.Types import BackendConfigurationError

from .Backends.File import FileBackendMixin
from .BackendTestMixins import (ConfigStateTestsMixin, ProductPropertiesTestMixin,
    ProductDependenciesTestMixin, AuditTestsMixin,
    ConfigTestsMixin, ProductsTestMixin, ProductsOnClientTestsMixin,
    ProductsOnDepotTestsMixin, ProductPropertyStateTestsMixin, GroupTestsMixin,
    ObjectToGroupTestsMixin, ExtendedBackendTestsMixin, BackendTestsMixin)
from .BackendTestMixins.Hosts import HostsTestMixin


class FileBackendTestCase(unittest.TestCase, FileBackendMixin,
    ConfigStateTestsMixin, ProductPropertiesTestMixin, ConfigTestsMixin,
    ProductDependenciesTestMixin, AuditTestsMixin, ProductsTestMixin,
    ProductsOnClientTestsMixin, ProductsOnDepotTestsMixin,
    ProductPropertyStateTestsMixin, GroupTestsMixin, ObjectToGroupTestsMixin,
    ExtendedBackendTestsMixin, BackendTestsMixin, HostsTestMixin):
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

    def testGetRawDataFailsBecauseNoQuerySupport(self):
        self.assertRaises(BackendConfigurationError, self.backend.getRawData, "blabla")


if __name__ == '__main__':
    unittest.main()
