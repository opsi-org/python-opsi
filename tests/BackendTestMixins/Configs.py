#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import absolute_import
from OPSI.Object import UnicodeConfig, BoolConfig, ConfigState

from .Clients import ClientsMixin
from .Hosts import HostsMixin


class ConfigsMixin(ClientsMixin, HostsMixin):
    def setUpConfigs(self):
        self.setUpHosts()
        self.setUpClients()

        # TODO: turn this into tests?
        self.config1 = UnicodeConfig(
            id=u'opsi-linux-bootimage.cmdline.reboot',
            description=(u'Some string üöä?').encode('latin-1'),
            possibleValues = ['w', 'c', 'b', 'h', 'b,c'],
            defaultValues = ['b,c']
        )

        self.config2 = BoolConfig(
            id=u'opsi-linux-bootimage.cmdline.bool',
            description='Bool?',
            defaultValues='on'
        )

        self.config3 = UnicodeConfig(
            id=u'some.products',
            description=u'Install this products',
            possibleValues=['product1', 'product2', 'product3', 'product4'],
            defaultValues=['product1', 'product3']
        )

        self.config4 = UnicodeConfig(
            id=u'clientconfig.depot.id',
            description=u'Depotserver to use',
            possibleValues=[],
            defaultValues=[self.depotserver1.id]
        )

        self.config5 = UnicodeConfig(
            id=u'some.other.products',
            description=u'Some other product ids',
            possibleValues=['product3', 'product4', 'product5'],
            defaultValues=['product3']
        )

        self.config6 = UnicodeConfig(
            id=u'%username%',
            description=u'username',
            possibleValues=None,
            defaultValues=['opsi']
        )

        self.configs = [
            self.config1, self.config2, self.config3, self.config4,
            self.config5, self.config6
        ]

    def createConfigOnBackend(self):
        for config in self.configs:
            config.setDefaults()
        self.backend.config_createObjects(self.configs)


class ConfigTestsMixin(ConfigsMixin):
    def configureBackendOptions(self):
        self.backend.backend_setOptions({
            'processProductPriorities': False,
            'processProductDependencies': False,
            'addProductOnClientDefaults': False,
            'addProductPropertyStateDefaults': False,
            'addConfigStateDefaults': False,
            'deleteConfigStateIfDefault': False,
            'returnObjectsOnUpdateAndCreate': False
        })

    def testConfigMethods(self):
        self.configureBackendOptions()

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


class ConfigStatesMixin(ConfigsMixin):
    def setUpConfigStates(self):
        self.setUpConfigs()

        # TODO: turn this into tests?
        self.configState1 = ConfigState(
            configId=self.config1.getId(),
            objectId=self.client1.getId(),
            values=['w']
        )

        # TODO: turn this into tests?
        self.configState2 = ConfigState(
            configId=self.config2.getId(),
            objectId=self.client1.getId(),
            values=[False]
        )

        # TODO: turn this into tests?
        self.configState3 = ConfigState(
            configId=self.config2.getId(),
            objectId=self.client2.getId(),
            values=[False]
        )

        # TODO: turn this into tests?
        self.configState4 = ConfigState(
            configId=self.config6.getId(),
            objectId=self.client2.getId(),
            values=["-------- test --------\n4: %4\n1: %1\n2: %2\n5: %5"]
        )

        # TODO: turn this into tests?
        self.configState5 = ConfigState(
            configId=self.config4.getId(),
            objectId=self.client5.getId(),
            values=self.depotserver2.id
        )

        self.configState6 = ConfigState(
            configId=self.config4.getId(),
            objectId=self.client6.getId(),
            values=self.depotserver2.id
        )

        self.configState7 = ConfigState(
            configId=self.config4.getId(),
            objectId=self.client7.getId(),
            values=self.depotserver2.id
        )

        self.configStates = [
            self.configState1, self.configState2, self.configState3,
            self.configState4, self.configState5, self.configState6,
            self.configState7
        ]

    def createConfigStatesOnBackend(self):
        self.backend.configState_createObjects(self.configStates)


class ConfigStateTestsMixin(ConfigStatesMixin):
    def configureBackendOptions(self):
        self.backend.backend_setOptions({
            'processProductPriorities': False,
            'processProductDependencies': False,
            'addProductOnClientDefaults': False,
            'addProductPropertyStateDefaults': False,
            'addConfigStateDefaults': False,
            'deleteConfigStateIfDefault': False,
            'returnObjectsOnUpdateAndCreate': False
        })

    def testConfigStateMethods(self):
        self.configureBackendOptions()

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
