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
Testing the opsi SQLite backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Backends.SQLite import SQLiteBackendMixin
from .BackendTestMixins import (ConfigStateTestsMixin, ConfigTestsMixin,
    BackendTestsMixin)
from .helpers import unittest, requiresModulesFile

import pytest


def testInitialisationOfSQLiteBackendWithoutParametersDoesNotFail():
    sqlModule = pytest.importorskip("OPSI.Backend.SQLite")
    SQLiteBackend = sqlModule.SQLiteBackend

    backend = SQLiteBackend()
    backend.backend_createBase()


class SQLiteBackendTestCase(unittest.TestCase, SQLiteBackendMixin,
    BackendTestsMixin, ConfigTestsMixin, ConfigStateTestsMixin):
    """Testing the SQLite backend.

    This currently requires a valid modules file with enabled MySQL backend."""

    @requiresModulesFile
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
