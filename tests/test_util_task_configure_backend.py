#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2016 uib GmbH <info@uib.de>

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
Testing the backend configuration.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os

from OPSI.Object import UnicodeConfig
import OPSI.Util.Task.ConfigureBackend as backendConfigUtils
import OPSI.Util.Task.ConfigureBackend.ConfigurationData as confData

from .Backends.File import FileBackendMixin
from .helpers import createTemporaryTestfile, unittest

import pytest


class ConfigFileManagementTestCase(unittest.TestCase):

    EXAMPLE_CONFIG = os.path.join(
        os.path.dirname(__file__), '..',
        'data', 'backends', 'mysql.conf'
    )

    def testReadingMySQLConfigFile(self):
        defaultMySQLConfig = {
            "address": u"localhost",
            "database": u"opsi",
            "username": u"opsi",
            "password": u"opsi",
            "databaseCharset": "utf8",
            "connectionPoolSize": 20,
            "connectionPoolMaxOverflow": 10,
            "connectionPoolTimeout": 30
        }

        with createTemporaryTestfile(self.EXAMPLE_CONFIG) as fileName:
            config = backendConfigUtils.getBackendConfiguration(fileName)

        self.assertEqual(config, defaultMySQLConfig)

    def testUpdatingTestConfigFile(self):
        with createTemporaryTestfile(self.EXAMPLE_CONFIG) as fileName:
            config = backendConfigUtils.getBackendConfiguration(fileName)

            self.assertNotEqual('notYourCurrentPassword', config['password'])
            config['password'] = 'notYourCurrentPassword'
            backendConfigUtils.updateConfigFile(fileName, config)
            self.assertEqual('notYourCurrentPassword', config['password'])

            del config['address']
            del config['database']
            del config['password']

            backendConfigUtils.updateConfigFile(fileName, config)

            config = backendConfigUtils.getBackendConfiguration(fileName)

        for key in ('address', 'database', 'password'):
            self.assertTrue(
                key not in config,
                '{0} should not be in {1}'.format(key, config)
            )

        for key in ('username', 'connectionPoolMaxOverflow'):
            self.assertTrue(
                key in config,
                '{0} should be in {1}'.format(key, config)
            )


def testReadingWindowsDomainFromSambaConfig():
    testConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    domain = confData.readWindowsDomainFromSambaConfig(testConfig)

    assert 'WWWORK' == domain


@pytest.mark.parametrize("configId", [
    u'clientconfig.depot.dynamic',
    u'clientconfig.depot.drive',
    u'clientconfig.depot.protocol',
    u'clientconfig.windows.domain',
    u'opsi-linux-bootimage.append',
    u'license-management.use',
    u'software-on-demand.active',
    u'software-on-demand.product-group-ids',
    u'product_sort_algorithm',
    u'clientconfig.dhcpd.filename',
    pytest.mark.xfail(u'software-on-demand.show-details', strict=True),
    u'opsiclientd.event_user_login.active',
    u'opsiclientd.event_user_login.action_processor_command',
])
def testConfigureBackendAddsMissingEntries(extendedConfigDataBackend, configId):
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    configIdents = set(extendedConfigDataBackend.config_getIdents(returnType='unicode'))

    assert configId in configIdents


def testAddingDynamicClientConfigDepotDrive(extendedConfigDataBackend):
    """
    'dynamic' should be a possible value in 'clientconfig.depot.drive'.

    This makes sure that old configs are updated aswell.
    """
    extendedConfigDataBackend.config_delete(id=[u'clientconfig.depot.drive'])

    oldConfig = UnicodeConfig(
        id=u'clientconfig.depot.drive',
        description=u'Drive letter for depot share',
        possibleValues=[
            u'c:', u'd:', u'e:', u'f:', u'g:', u'h:', u'i:', u'j:',
            u'k:', u'l:', u'm:', u'n:', u'o:', u'p:', u'q:', u'r:',
            u's:', u't:', u'u:', u'v:', u'w:', u'x:', u'y:', u'z:',
        ],
        defaultValues=[u'p:'],
        editable=False,
        multiValue=False
    )
    extendedConfigDataBackend.config_createObjects([oldConfig])

    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    config = extendedConfigDataBackend.config_getObjects(id=u'clientconfig.depot.drive')[0]
    assert u'dynamic' in config.possibleValues


def testAddingDynamicClientConfigDepotDriveKeepsOldDefault(extendedConfigDataBackend):
    """
    Adding the new property should keep the old defaults.
    """
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    extendedConfigDataBackend.config_delete(id=[u'clientconfig.depot.drive'])
    oldConfig = UnicodeConfig(
        id=u'clientconfig.depot.drive',
        description=u'Drive letter for depot share',
        possibleValues=[
            u'c:', u'd:', u'e:', u'f:', u'g:', u'h:', u'i:', u'j:',
            u'k:', u'l:', u'm:', u'n:', u'o:', u'p:', u'q:', u'r:',
            u's:', u't:', u'u:', u'v:', u'w:', u'x:', u'y:', u'z:',
        ],
        defaultValues=[u'n:'],
        editable=False,
        multiValue=False
    )
    extendedConfigDataBackend.config_createObjects([oldConfig])

    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    config = extendedConfigDataBackend.config_getObjects(id=u'clientconfig.depot.drive')[0]
    assert [u'n:'] == config.defaultValues


def testAddingWANConfigs(extendedConfigDataBackend):
    requiredConfigIdents = [
        "opsiclientd.event_gui_startup.active",
        "opsiclientd.event_gui_startup{user_logged_in}.active",
        "opsiclientd.event_net_connection.active",
        "opsiclientd.event_timer.active",
    ]

    confData.createWANconfigs(extendedConfigDataBackend)
    identsInBackend = set(extendedConfigDataBackend.config_getIdents())

    for ident in requiredConfigIdents:
        assert ident in identsInBackend, "Missing config id {0}".format(ident)


def testAddingInstallByShutdownConfig(extendedConfigDataBackend):
    requiredConfigIdents = [
        "clientconfig.install_by_shutdown.active",
    ]

    confData.createInstallByShutdownConfig(extendedConfigDataBackend)
    identsInBackend = set(extendedConfigDataBackend.config_getIdents())

    for ident in requiredConfigIdents:
        assert ident in identsInBackend, "Missing config id {0}".format(ident)
