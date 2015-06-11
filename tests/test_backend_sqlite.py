#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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
Testing the opsi SQLite backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os.path

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
	import apsw
	from OPSI.Backend.SQLite import SQLiteBackend
except ImportError:
	apsw = None


from Backends.SQLite import SQLiteBackendMixin
from BackendTestMixins import (ConfigStateTestsMixin, LicensesTestMixin,
    AuditTestsMixin, ConfigTestsMixin, ProductsTestMixin,
    ExtendedBackendTestsMixin, BackendTestsMixin)


@unittest.skipIf(not apsw, 'SQLite tests skipped: Missing the module "apsw".')
class BackendSQLiteTestCase(unittest.TestCase):
    def testInitialisationDoesNotFail(self):
        backend = SQLiteBackend()
        backend.backend_createBase()


@unittest.skipIf(not os.path.exists('/etc/opsi/modules'), 'SQLite tests skipped: Missing modules file.')
@unittest.skipIf(not apsw, 'SQLite tests skipped: Missing the module "apsw".')
class SQLiteBackendTestCase(unittest.TestCase, SQLiteBackendMixin,
    BackendTestsMixin, ProductsTestMixin, AuditTestsMixin, LicensesTestMixin,
    ExtendedBackendTestsMixin, ConfigTestsMixin, ConfigStateTestsMixin):
    """Testing the SQLite backend.

    This currently requires a valid modules file with enabled MySQL backend."""

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
