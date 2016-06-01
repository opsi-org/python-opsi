#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

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

from OPSI.Object import (OpsiClient, LocalbootProduct, ProductOnClient,
                         OpsiDepotserver, ProductOnDepot, UnicodeConfig,
                         ConfigState)
from OPSI.Types import BackendMissingDataError
from .Backends.File import FileBackendBackendManagerMixin
from .helpers import unittest

import pytest

class LegacyFunctionsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
    "Testing the legacy / simple functins."

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


class LegacyConfigStateAccessTestCase(unittest.TestCase, FileBackendBackendManagerMixin):
    """
    Testing legacy access to ConfigStates.
    """

    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testNoConfigReturnsNoValue(self):
        self.assertEquals(None, self.backend.getGeneralConfigValue(None))
        self.assertEquals(None, self.backend.getGeneralConfigValue(""))

    def testEmptyAfterStart(self):
        self.assertEquals({}, self.backend.getGeneralConfig_hash())

    def testUnabledToHandleNonTextValues(self):
        function = self.backend.setGeneralConfig
        self.assertRaises(Exception, function, {"test": True})
        self.assertRaises(Exception, function, {"test": 1})
        self.assertRaises(Exception, function, {"test": None})

    def testSetGeneralConfigValue(self):
        config = {"test.truth": "True", "test.int": "2"}
        self.backend.setGeneralConfig(config)

        for key, value in config.items():
            self.assertEquals(value, self.backend.getGeneralConfigValue(key))

        self.assertNotEquals({}, self.backend.getGeneralConfig_hash())
        self.assertEquals(2, len(self.backend.getGeneralConfig_hash()))

    def testSetGeneralConfigValueTypeConversion(self):
        trueValues = set(['yes', 'on', '1', 'true'])
        falseValues = set(['no', 'off', '0', 'false'])

        for value in trueValues:
            self.backend.setGeneralConfig({"bool": value})
            self.assertEquals("True", self.backend.getGeneralConfigValue("bool"))

        for value in falseValues:
            self.backend.setGeneralConfig({"bool": value})
            self.assertEquals("False", self.backend.getGeneralConfigValue("bool"))

        self.backend.setGeneralConfig({"bool": "noconversion"})
        self.assertEquals("noconversion", self.backend.getGeneralConfigValue("bool"))

    def testRemovingMissingValue(self):
        config = {"test.truth": "True", "test.int": "2"}
        self.backend.setGeneralConfig(config)
        self.assertEquals(2, len(self.backend.getGeneralConfig_hash()))

        del config["test.int"]
        self.backend.setGeneralConfig(config)
        self.assertEquals(1, len(self.backend.getGeneralConfig_hash()))


def testMassFilling(backendManager):
    numberOfConfigs = 50  # len(config) will be double

    config = {}
    for value in range(numberOfConfigs):
        config["bool.{0}".format(value)] = str(value % 2 == 0)

    for value in range(numberOfConfigs):
        config["normal.{0}".format(value)] = "norm-{0}".format(value)

    assert numberOfConfigs * 2 == len(config)

    backendManager.setGeneralConfig(config)

    assert config == backendManager.getGeneralConfig_hash()
