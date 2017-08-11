# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2017 uib GmbH <info@uib.de>

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
import pytest

from OPSI.Object import UnicodeConfig
from OPSI.System.Posix import CommandNotFoundException
import OPSI.Util.Task.ConfigureBackend as backendConfigUtils
import OPSI.Util.Task.ConfigureBackend.ConfigurationData as confData

from .test_hosts import getConfigServer
from .helpers import createTemporaryTestfile, mock


@pytest.fixture
def exampleMySQLBackendConfig():
    templateFile = os.path.join(
        os.path.dirname(__file__), '..',
        'data', 'backends', 'mysql.conf'
    )

    with createTemporaryTestfile(templateFile) as fileName:
        yield fileName


def testReadingMySQLConfigFile(exampleMySQLBackendConfig):
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

    config = backendConfigUtils.getBackendConfiguration(exampleMySQLBackendConfig)

    assert config == defaultMySQLConfig


def testUpdatingTestConfigFile(exampleMySQLBackendConfig):
    fileName = exampleMySQLBackendConfig
    config = backendConfigUtils.getBackendConfiguration(fileName)

    assert 'notYourCurrentPassword' != config['password']
    config['password'] = 'notYourCurrentPassword'
    backendConfigUtils.updateConfigFile(fileName, config)
    assert 'notYourCurrentPassword' == config['password']

    del config['address']
    del config['database']
    del config['password']

    backendConfigUtils.updateConfigFile(fileName, config)

    config = backendConfigUtils.getBackendConfiguration(fileName)

    for key in ('address', 'database', 'password'):
        assert key not in config, '{0} should not be in {1}'.format(key, config)

    for key in ('username', 'connectionPoolMaxOverflow'):
        assert key in config, '{0} should be in {1}'.format(key, config)


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
    pytest.param(u'software-on-demand.show-details', marks=pytest.mark.xfail),
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


@pytest.mark.parametrize("runningOnUCS", [True, False])
def testAddingUCSSpecificConfigs(extendedConfigDataBackend, runningOnUCS):
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    with mock.patch('OPSI.Util.Task.ConfigureBackend.ConfigurationData.Posix.isUCS', lambda: runningOnUCS):
        confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    configIdents = set(extendedConfigDataBackend.config_getIdents(returnType='unicode'))

    assert ('clientconfig.depot.user' in configIdents) == runningOnUCS

    if runningOnUCS:
        configs = extendedConfigDataBackend.config_getHashes(id='clientconfig.depot.user')
        assert len(configs) == 1
        config = configs[0]

        assert len(config['defaultValues']) == 1
        defaultValues = config['defaultValues'][0]
        assert 'pcpatch' in defaultValues


def testAddingConfigsBasedOnConfigServer(extendedConfigDataBackend):
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    configServer = getConfigServer()
    configServer.ipAddress = '12.34.56.78'

    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig, configServer=configServer)

    configIdents = set(extendedConfigDataBackend.config_getIdents(returnType='unicode'))
    expectedConfigIDs = [u'clientconfig.configserver.url', u'clientconfig.depot.id']

    for cId in expectedConfigIDs:
        assert cId in configIdents

    urlConfig = extendedConfigDataBackend.config_getObjects(id=u'clientconfig.configserver.url')[0]
    assert 1 == len(urlConfig.defaultValues)
    value = urlConfig.defaultValues[0]
    assert value.endswith('/rpc')
    assert value.startswith('https://')
    assert configServer.ipAddress in value
    assert urlConfig.editable

    depotConfig = extendedConfigDataBackend.config_getObjects(id=u'clientconfig.depot.id')[0]
    assert 1 == len(depotConfig.defaultValues)
    assert configServer.id == depotConfig.defaultValues[0]
    assert configServer.id == depotConfig.possibleValues[0]
    assert not depotConfig.multiValue
    assert depotConfig.editable


def testAddingConfigBasedOnConfigServerFailsIfServerMissesIP(extendedConfigDataBackend):
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    configServer = getConfigServer()
    configServer.ipAddress = None

    with pytest.raises(Exception):
        confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig, configServer=configServer)


def testConfigsAreOnlyAddedOnce(extendedConfigDataBackend):
    sambaTestConfig = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'task', 'smb.conf')
    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)

    configIdentsFirst = extendedConfigDataBackend.config_getIdents(returnType='unicode')
    configIdentsFirst.sort()

    confData.initializeConfigs(backend=extendedConfigDataBackend, pathToSMBConf=sambaTestConfig)
    configIdentsSecond = extendedConfigDataBackend.config_getIdents(returnType='unicode')
    configIdentsSecond.sort()

    assert configIdentsFirst == configIdentsSecond
    assert len(configIdentsSecond) == len(set(configIdentsSecond))


def testReadingDomainFromUCR():
    with mock.patch('OPSI.Util.Task.ConfigureBackend.ConfigurationData.Posix.which', lambda x: '/no/real/path/ucr'):
        with mock.patch('OPSI.Util.Task.ConfigureBackend.ConfigurationData.Posix.execute', lambda x: ['sharpdressed']):
            assert 'SHARPDRESSED' == confData.readWindowsDomainFromUCR()


def testReadingDomainFromUCRReturnEmptyStringOnProblem():
    failingWhich = mock.Mock(side_effect=CommandNotFoundException('Whoops.'))
    with mock.patch('OPSI.Util.Task.ConfigureBackend.ConfigurationData.Posix.which', failingWhich):
        assert '' == confData.readWindowsDomainFromUCR()
