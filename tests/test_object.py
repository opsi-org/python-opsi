#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing OPSI.Objects

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import unittest

from OPSI.Object import (AuditHardwareOnHost, Host, OpsiConfigserver,
    OpsiDepotserver, LocalbootProduct, UnicodeConfig,
    getPossibleClassAttributes)


class GetPossibleClassAttributesTestCase(unittest.TestCase):
    def testMethod(self):
        self.assertEquals(
            getPossibleClassAttributes(Host),
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
            id='configserver1.test.invalid',
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
            id='configserver1.test.invalid',
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
            id='depotserver1.test.invalid',
            opsiHostKey='19012334567845645678901232789012',
            depotLocalUrl='file:///opt/pcbin/install',
            depotRemoteUrl='smb://depotserver1.test.invalid/opt_pcbin/install',
            repositoryLocalUrl='file:///var/lib/opsi/repository',
            repositoryRemoteUrl='webdavs://depotserver1.test.invalid:4447/repository',
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


class UnicodeConfigTestCase(unittest.TestCase):
    def testMultivalueWithUnicode(self):
        config = UnicodeConfig(
            id=u'python-opsi.test',
            description="Something from the OPSI forums.",
            possibleValues=[u"Neutron Gerätetechnik GmbH", u"Neutron Mikroelektronik GmbH"],
            defaultValues=[u"Neutron Mikroelektronik GmbH"]
        )

        self.assertTrue(u"Neutron Gerätetechnik GmbH" in config.possibleValues)
        self.assertTrue(u"Neutron Mikroelektronik GmbH" in config.possibleValues)


class AuditHardwareOnHostTestCase(unittest.TestCase):
    def setUp(self):
        self.ahoh = AuditHardwareOnHost(
            hostId="client.test.local",
            hardwareClass='COMPUTER_SYSTEM',
            description="Description for auditHardware",
            vendor="Vendor for auditHardware",
            model="Model for auditHardware",
            serialNumber='843391034-2192',
            systemType='Desktop',
            totalPhysicalMemory=1073741824
        )

    def tearDown(self):
        del self.ahoh

    def test__unicode__(self):
        self.ahoh.__unicode__()

    def test__unicode__with_additionals(self):
        self.ahoh.name = "Ünicöde name."
        self.ahoh.__unicode__()
