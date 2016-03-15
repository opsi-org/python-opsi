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
Backend mixin for testing configuration objects on a backend.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""


from __future__ import absolute_import
from OPSI.Object import UnicodeConfig, BoolConfig, ConfigState

from .Clients import ClientsMixin, getClients
from .Hosts import HostsMixin, getDepotServers


def getConfigs(depotServerId=None):
    config1 = UnicodeConfig(
        id=u'opsi-linux-bootimage.cmdline.reboot',
        description=(u'Some string üöä?').encode('latin-1'),
        possibleValues = ['w', 'c', 'b', 'h', 'b,c'],
        defaultValues = ['b,c']
    )

    config2 = BoolConfig(
        id=u'opsi-linux-bootimage.cmdline.bool',
        description='Bool?',
        defaultValues='on'
    )

    config3 = UnicodeConfig(
        id=u'some.products',
        description=u'Install this products',
        possibleValues=['product1', 'product2', 'product3', 'product4'],
        defaultValues=['product1', 'product3']
    )

    config4 = UnicodeConfig(
        id=u'clientconfig.depot.id',
        description=u'Depotserver to use',
        possibleValues=[],
        defaultValues=[depotServerId or "depot3000.domain.invalid"]
    )

    config5 = UnicodeConfig(
        id=u'some.other.products',
        description=u'Some other product ids',
        possibleValues=['product3', 'product4', 'product5'],
        defaultValues=['product3']
    )

    config6 = UnicodeConfig(
        id=u'%username%',
        description=u'username',
        possibleValues=None,
        defaultValues=['opsi']
    )

    return (config1, config2, config3, config4, config5, config6)


def getConfigStates(configs, clients, depotserver):
    config1, config2, _, config4, _, config6 = configs[:6]
    client1, client2, _, _, client5, client6, client7 = clients[:7]
    depotserver2 = depotserver[1]

    # TODO: turn this into tests?
    configState1 = ConfigState(
        configId=config1.getId(),
        objectId=client1.getId(),
        values=['w']
    )

    # TODO: turn this into tests?
    configState2 = ConfigState(
        configId=config2.getId(),
        objectId=client1.getId(),
        values=[False]
    )

    # TODO: turn this into tests?
    configState3 = ConfigState(
        configId=config2.getId(),
        objectId=client2.getId(),
        values=[False]
    )

    # TODO: turn this into tests?
    configState4 = ConfigState(
        configId=config6.getId(),
        objectId=client2.getId(),
        values=["-------- test --------\n4: %4\n1: %1\n2: %2\n5: %5"]
    )

    # TODO: turn this into tests?
    configState5 = ConfigState(
        configId=config4.getId(),
        objectId=client5.getId(),
        values=depotserver2.id
    )

    configState6 = ConfigState(
        configId=config4.getId(),
        objectId=client6.getId(),
        values=depotserver2.id
    )

    configState7 = ConfigState(
        configId=config4.getId(),
        objectId=client7.getId(),
        values=depotserver2.id
    )

    return (configState1, configState2, configState3, configState4,
            configState5, configState6, configState7)


class ConfigsMixin(ClientsMixin, HostsMixin):
    def setUpConfigs(self):
        self.setUpHosts()
        self.setUpClients()

        (self.config1, self.config2, self.config3, self.config4,
         self.config5, self.config6) = getConfigs(self.depotserver1.id)

        self.configs = [
            self.config1, self.config2, self.config3, self.config4,
            self.config5, self.config6
        ]

    def createConfigOnBackend(self):
        for config in self.configs:
            config.setDefaults()
        self.backend.config_createObjects(self.configs)


class ConfigTestsMixin(ConfigsMixin):
    def testConfigMethods(self):
        self.setUpConfigs()
        self.createConfigOnBackend()

        configs = self.backend.config_getObjects()
        assert len(configs) == len(
            self.configs), u"got: '%s', expected: '%s'" % (configs, len(self.configs))
        ids = []
        for config in configs:
            ids.append(config.id)
        for config in self.configs:
            assert config.id in ids

        for config in configs:
            for c in self.configs:
                if (config.id == c.id):
                    assert config == c, u"got: '%s', expected: '%s'" % (
                        config, c)

        configs = self.backend.config_getObjects(
            defaultValues=self.config2.defaultValues)
        assert len(configs) == 1, u"got: '%s', expected: '%s'" % (configs, 1)
        assert configs[0].getId() == self.config2.getId(), u"got: '%s', expected: '%s'" % (
            configs[0].getId(), self.config2.getId())

        configs = self.backend.config_getObjects(possibleValues=[])
        assert len(configs) == len(
            self.configs), u"got: '%s', expected: '%s'" % (configs, len(self.configs))

        configs = self.backend.config_getObjects(
            possibleValues=self.config1.possibleValues, defaultValues=self.config1.defaultValues)
        assert len(configs) == 1, u"got: '%s', expected: '%s'" % (configs, 1)
        assert configs[0].getId() == self.config1.getId(), u"got: '%s', expected: '%s'" % (
            configs[0].getId(), self.config1.getId())

        configs = self.backend.config_getObjects(
            possibleValues=self.config5.possibleValues, defaultValues=self.config5.defaultValues)
        assert len(configs) == 2, u"got: '%s', expected: '%s'" % (configs, 2)
        for config in configs:
            assert config.getId() in (self.config3.id, self.config5.id), u"'%s' not in '%s'" % (
                config.getId(), (self.config3.id, self.config5.id))

        multiValueConfigNames = []
        for config in self.configs:
            if config.getMultiValue():
                multiValueConfigNames.append(config.id)
        configs = self.backend.config_getObjects(
            attributes=[], multiValue=True)
        assert len(configs) == len(multiValueConfigNames), u"got: '%s', expected: '%s'" % (
            configs, len(multiValueConfigNames))
        for config in configs:
            assert config.id in multiValueConfigNames, u"'%s' not in '%s'" % (
                config.id, multiValueConfigNames)

        self.backend.config_deleteObjects(self.config1)
        configs = self.backend.config_getObjects()
        assert len(configs) == len(self.configs) - \
            1, u"got: '%s', expected: '%s'" % (
                configs, len(self.configs) - 1)

        self.backend.config_createObjects(self.config1)

        self.config3.setDescription(u'Updated')
        self.config3.setPossibleValues(['1', '2', '3'])
        self.config3.setDefaultValues(['1', '2'])
        self.backend.config_updateObject(self.config3)

        configs = self.backend.config_getObjects(description=u'Updated')
        assert len(configs) == 1, u"got: '%s', expected: '%s'" % (configs, 1)
        assert len(configs[0].getPossibleValues()) == 3, u"got %s, expected length 3" % configs[
            0].getPossibleValues()
        for i in ['1', '2', '3']:
            assert i in configs[0].getPossibleValues(), u"%s not in %s" % (
                i, configs[0].getPossibleValues())
        assert len(configs[0].getDefaultValues()) == 2, u"got %s, expected length 2" % configs[
            0].getDefaultValues()
        for i in ['1', '2']:
            assert i in configs[0].getDefaultValues(), u"%s not in %s" % (
                i, configs[0].getDefaultValues())

    def test_getConfigFromBackend(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        configs = self.backend.config_getObjects()
        self.assertEqual(len(configs), len(configsOrig))

    def test_verifyConfigs(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        configs = self.backend.config_getObjects()
        assert configs

        ids = [config.id for config in configs]
        for config in configsOrig:
            self.assertIn(config.id, ids)

        for config in configs:
            for c in configsOrig:
                if config.id == c.id:
                    self.assertEqual(config, c)

    def test_getConfigByDefaultValues(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        config2 = configsOrig[1]

        configs = self.backend.config_getObjects(defaultValues=config2.defaultValues)
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].getId(), config2.getId())

    def test_getConfigByPossibleValues(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        configs = self.backend.config_getObjects(possibleValues=[])
        self.assertEqual(len(configs), len(configsOrig))

        config1 = configsOrig[0]
        configs = self.backend.config_getObjects(possibleValues=config1.possibleValues, defaultValues=config1.defaultValues)
        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].getId(), config1.getId())

        config5 = configsOrig[4]
        configs = self.backend.config_getObjects(possibleValues=config5.possibleValues, defaultValues=config5.defaultValues)
        self.assertEqual(len(configs), 2)

        config3 = configsOrig[2]
        for config in configs:
            self.assertIn(config.getId(), (config3.id, config5.id))

    def test_getMultiValueConfigs(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        multiValueConfigNames = [config.id for config in configsOrig if config.getMultiValue()]
        assert multiValueConfigNames

        configs = self.backend.config_getObjects(attributes=[], multiValue=True)
        self.assertEqual(len(configs), len(multiValueConfigNames))
        for config in configs:
            self.assertIn(config.id, multiValueConfigNames)

    def test_deleteConfigFromBackend(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        config1 = configsOrig[0]
        self.backend.config_deleteObjects(config1)
        configs = self.backend.config_getObjects()
        self.assertEqual(len(configs), len(configsOrig) - 1)

    def test_updateConfig(self):
        configsOrig = getConfigs()
        self.backend.config_createObjects(configsOrig)

        config3 = configsOrig[2]

        config3.setDescription(u'Updated')
        config3.setPossibleValues(['1', '2', '3'])
        config3.setDefaultValues(['1', '2'])
        self.backend.config_updateObject(config3)

        configs = self.backend.config_getObjects(description=u'Updated')
        self.assertEqual(len(configs), 1)
        config = configs[0]
        self.assertEqual(len(config.getPossibleValues()), 3)
        for i in ['1', '2', '3']:
            self.assertIn(i, config.getPossibleValues())
        self.assertEqual(len(config.getDefaultValues()), 2)
        for i in ['1', '2']:
            self.assertIn(i, config.getDefaultValues())


class ConfigStatesMixin(ConfigsMixin):
    def setUpConfigStates(self):
        self.setUpConfigs()

        (self.configState1, self.configState2, self.configState3,
         self.configState4, self.configState5, self.configState6,
         self.configState7) = getConfigStates(self.configs, self.clients, self.depotservers)

        self.configStates = [
            self.configState1, self.configState2, self.configState3,
            self.configState4, self.configState5, self.configState6,
            self.configState7
        ]

    def createConfigStatesOnBackend(self):
        self.backend.configState_createObjects(self.configStates)


class ConfigStateTestsMixin(ConfigStatesMixin):
    def testConfigStateMethods(self):
        self.setUpConfigStates()

        self.createHostsOnBackend()
        self.createConfigOnBackend()
        self.createConfigStatesOnBackend()

        configStates = self.backend.configState_getObjects()
        assert len(configStates) == len(self.configStates), u"got: '%s', expected: '%s'" % (configStates, len(self.configStates))

        client1ConfigStates = []
        for configState in self.configStates:
            if configState.getObjectId() == self.client1.getId():
                client1ConfigStates.append(configState)
        configStates = self.backend.configState_getObjects(
            attributes=[], objectId=self.client1.getId())
        #assert len(configStates) == len(client1ConfigStates), u"got: '%s', expected: '%s'" % (configStates, len(client1ConfigStates))
        for configState in configStates:
            assert configState.objectId == self.client1.getId(), u"got: '%s', expected: '%s'" % (
                configState.objectId, self.client1.getId())

        self.backend.configState_deleteObjects(self.configState2)
        configStates = self.backend.configState_getObjects()
        #assert len(configStates) == len(self.configStates)-1
        # for configState in configStates:
        #   assert not (configState.objectId == self.configState2.objectId and configState.configId == self.configState2.configId)

        self.configState3.setValues([True])
        self.backend.configState_updateObject(self.configState3)
        configStates = self.backend.configState_getObjects(
            objectId=self.configState3.getObjectId(), configId=self.configState3.getConfigId())
        assert len(configStates) == 1, u"got: '%s', expected: '%s'" % (
            configStates, 1)
        assert configStates[0].getValues() == [
            True], u"got: '%s', expected: '%s'" % (configStates[0].getValues(), [True])

        configStates = self.backend.configState_getObjects(
            objectId=self.configState4.getObjectId(), configId=self.configState4.getConfigId())
        assert len(configStates) == 1, u"got: '%s', expected: '%s'" % (
            configStates, 1)
        assert configStates[0].getValues()[0] == self.configState4.getValues()[
            0], u"got: '%s', expected: '%s'" % (configStates[0].getValues()[0], self.configState4.getValues()[0])

    def test_getConfigStatesFromBackend(self):
        configs = getConfigs()
        clients = getClients()
        depots = getDepotServers()
        configStatesOrig = getConfigStates(configs, clients, depots)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depots)
        self.backend.config_createObjects(configs)
        self.backend.configState_createObjects(configStatesOrig)

        configStates = self.backend.configState_getObjects()
        assert configStates

        for state in configStatesOrig:
            self.assertIn(state, configStates)

    def test_getConfigStateByClientID(self):
        configs = getConfigs()
        clients = getClients()
        depots = getDepotServers()
        configStatesOrig = getConfigStates(configs, clients, depots)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depots)
        self.backend.config_createObjects(configs)
        self.backend.configState_createObjects(configStatesOrig)

        client1 = clients[0]
        client1ConfigStates = [configState for configState in configStatesOrig if configState.getObjectId() == client1.getId()]

        configStates = self.backend.configState_getObjects(attributes=[], objectId=client1.getId())
        assert configStates
        for configState in configStates:
            self.assertEqual(configState.objectId, client1.getId())

    def test_deleteConfigStateFromBackend(self):
        configs = getConfigs()
        clients = getClients()
        depots = getDepotServers()
        configStatesOrig = getConfigStates(configs, clients, depots)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depots)
        self.backend.config_createObjects(configs)
        self.backend.configState_createObjects(configStatesOrig)

        configState2 = configStatesOrig[1]

        self.backend.configState_deleteObjects(configState2)
        configStates = self.backend.configState_getObjects()
        self.assertEqual(len(configStates), len(configStatesOrig) - 1)
        self.assertNotIn(configState2, configStates)

    def test_updateConfigState(self):
        configs = getConfigs()
        clients = getClients()
        depots = getDepotServers()
        configStatesOrig = getConfigStates(configs, clients, depots)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depots)
        self.backend.config_createObjects(configs)
        self.backend.configState_createObjects(configStatesOrig)

        configState3 = configStatesOrig[2]
        configState3.setValues([True])
        self.backend.configState_updateObject(configState3)
        configStates = self.backend.configState_getObjects(objectId=configState3.getObjectId(), configId=configState3.getConfigId())
        self.assertEqual(len(configStates), 1)
        self.assertEqual(configStates[0].getValues(), [True])

    def test_selectConfigStateFromBackend(self):
        configs = getConfigs()
        clients = getClients()
        depots = getDepotServers()
        configStatesOrig = getConfigStates(configs, clients, depots)

        self.backend.host_createObjects(clients)
        self.backend.host_createObjects(depots)
        self.backend.config_createObjects(configs)
        self.backend.configState_createObjects(configStatesOrig)

        configState4 = configStatesOrig[3]

        configStates = self.backend.configState_getObjects(objectId=configState4.getObjectId(), configId=configState4.getConfigId())
        self.assertEqual(len(configStates), 1)
        self.assertEqual(configStates[0].getValues()[0], configState4.getValues()[0])
