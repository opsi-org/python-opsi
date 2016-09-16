#! /usr/bin/env python
# -*- coding: utf-8 -*-

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
Testing opsi MySQL backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Backends import MySQL as MySQLback
from .BackendTestMixins.Backend import MultiThreadingTestMixin
from .helpers import unittest


class MySQLBackendTestCase(unittest.TestCase, MySQLback.MySQLBackendMixin):
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


class MySQLBackendMultiThreadTestCase(unittest.TestCase, MySQLback.MySQLBackendMixin, MultiThreadingTestMixin):
    def setUp(self):
        self.backend = None
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()
        del self.backend


if __name__ == '__main__':
    unittest.main()
