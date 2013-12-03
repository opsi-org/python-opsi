#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.Object import (Host, OpsiConfigserver, OpsiDepotserver,
    LocalbootProduct, getPossibleClassAttributes)


class GetPossibleClassAttributesTestCase(unittest.TestCase):
    def testMethod(self):
        self.assertEquals(
            set(getPossibleClassAttributes(Host)),
            set(
                [
                    'masterDepotId', 'depotLocalUrl', 'repositoryRemoteUrl',
                    'description', 'created', 'inventoryNumber', 'notes',
                    'oneTimePassword', 'isMasterDepot', 'id', 'lastSeen',
                    'maxBandwidth', 'hardwareAddress', 'networkAddress',
                    'repositoryLocalUrl', 'opsiHostKey', 'ipAddress',
                    'depotWebdavUrl', 'depotRemoteUrl', 'type'
                ]
            )
        )


class OpsiConfigServerComparisonTestCase(unittest.TestCase):
    def setUp(self):
        self.reference = OpsiConfigserver(
            id='configserver1.uib.local',
            opsiHostKey='71234545689056789012123678901234',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl=u'smb://configserver1/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl=u'webdavs://configserver1:4447/repository',
            description='The configserver',
            notes='Config 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000001',
            networkAddress='192.168.1.0/24',
            maxBandwidth=10000
        )

    def tearDown(self):
        del self.reference

    def testComparingToSelf(self):
        obj2 = self.reference
        self.assertEquals(self.reference, obj2)

    def testComparingToOtherObjectWithSameSettings(self):
        obj2 = OpsiConfigserver(
            id='configserver1.uib.local',
            opsiHostKey='71234545689056789012123678901234',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl=u'smb://configserver1/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl=u'webdavs://configserver1:4447/repository',
            description='The configserver',
            notes='Config 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000001',
            networkAddress='192.168.1.0/24',
            maxBandwidth=10000
        )

        self.assertEquals(self.reference, obj2)

    def testComparingToDepotserverFails(self):
        obj2 = OpsiDepotserver(
            id='depotserver1.uib.local',
            opsiHostKey='19012334567845645678901232789012',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depotserver1.uib.local/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl='webdavs://depotserver1.uib.local:4447/repository',
            description='A depot',
            notes='D€pot 1',
            hardwareAddress=None,
            ipAddress=None,
            inventoryNumber='00000000002',
            networkAddress='192.168.2.0/24',
            maxBandwidth=10000
        )
        self.assertNotEquals(self.reference, obj2)

    def testComparingToSomeDictFails(self):
        self.assertNotEquals(self.reference, {"test": 123})


class LocalbootProductTestCase(unittest.TestCase):
    def testComparison(self):
        obj1 = LocalbootProduct(
            id                 = 'product2',
            name               = u'Product 2',
            productVersion     = '2.0',
            packageVersion     = 'test',
            licenseRequired    = False,
            setupScript        = "setup.ins",
            uninstallScript    = u"uninstall.ins",
            updateScript       = "update.ins",
            alwaysScript       = None,
            onceScript         = None,
            priority           = 0,
            description        = None,
            advice             = "",
            productClassIds    = ['localboot-products'],
            windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx']
        )
        obj2 = LocalbootProduct(
            id                 = 'product2',
            name               = u'Product 2',
            productVersion     = '2.0',
            packageVersion     = 'test',
            licenseRequired    = False,
            setupScript        = "setup.ins",
            uninstallScript    = u"uninstall.ins",
            updateScript       = "update.ins",
            alwaysScript       = None,
            onceScript         = None,
            priority           = 0,
            description        = None,
            advice             = "",
            productClassIds    = ['localboot-products'],
            windowsSoftwareIds = ['xxxxxxxx', '{98723-7898adf2-287aab}']
        )

        self.assertEquals(obj1, obj2)
