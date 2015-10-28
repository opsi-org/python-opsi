#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015 uib GmbH <info@uib.de>

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
Tests for the dynamically loaded legacy extensions.

This tests what usually is found under
``/etc/opsi/backendManager/extend.de/20_legacy.conf``.

The legacy extensions are to maintain backwards compatibility for scripts
that were written for opsi 3.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from .Backends.File import ExtendedFileBackendMixin
from .helpers import unittest


class LegacyFunctionsTestCase(unittest.TestCase, ExtendedFileBackendMixin):
    """
    Testing the group actions.
    """
    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testGetGeneralConfigValueFailsWithInvalidObjectId(self):
        self.assertRaises(ValueError, self.backend.getGeneralConfig_hash, 'foo')

    def testGetGeneralConfig(self):
        """
        Calling the function with some valid FQDN must not fail.
        """
        self.backend.getGeneralConfig_hash('some.client.fqdn')

    def testSetGeneralConfigValue(self):
        # required by File-backend
        self.backend.host_createOpsiClient('some.client.fqdn')

        self.backend.setGeneralConfigValue('foo', 'bar', 'some.client.fqdn')

        self.assertEquals(
            'bar',
            self.backend.getGeneralConfigValue('foo', 'some.client.fqdn')
        )

    def testGetDomainShouldWork(self):
        self.assertNotEqual('', self.backend.getDomain())


if __name__ == '__main__':
    unittest.main()
