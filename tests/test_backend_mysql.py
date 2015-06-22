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
Testing opsi MySQL backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import Backends.MySQL as MySQLBackend
from BackendTestMixins import BackendTestMixin
from BackendTestMixins.Backend import MultiThreadingTestMixin


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


@unittest.skipIf(not MySQLBackend.MySQLconfiguration,
    'no MySQL backend configuration given.')
class MySQLBackendMultiThreadTestCase(unittest.TestCase, MySQLBackend.MySQLBackendMixin, MultiThreadingTestMixin):
    def setUp(self):
        self.backend = None
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()
        del self.backend


if __name__ == '__main__':
    unittest.main()
