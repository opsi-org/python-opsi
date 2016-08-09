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
Testing the Host Control backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import unittest

from .Backends.HostControl import HostControlBackendMixin
from .test_hosts import getClients


class HostControlBackendTestCase(unittest.TestCase, HostControlBackendMixin):
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testCallingStartAndStopMethod(self):
        """
        Test if calling the methods works.

        This test does not check if WOL on these clients work nor that
        they do exist.
        """
        clients = getClients()
        self.backend.host_createObjects(clients)

        self.backend.hostControl_start([u'client1.test.invalid'])
        self.backend.hostControl_shutdown([u'client1.test.invalid'])


if __name__ == '__main__':
    unittest.main()
