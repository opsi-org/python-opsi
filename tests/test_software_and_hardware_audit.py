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
Backend mixin for testing software / hardware audit functionality.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

from OPSI.Object import (AuditSoftware, AuditSoftwareOnClient,
    AuditHardware, AuditHardwareOnHost, AuditSoftwareToLicensePool)

from .BackendTestMixins.Clients import getClients
from .BackendTestMixins.Products import getLocalbootProducts, ProductsMixin
from .test_license_management import createLicensePool

import pytest


def getAuditHardwares():
    auditHardware1 = AuditHardware(
        hardwareClass='COMPUTER_SYSTEM',
        description='a pc',
        vendor='Dell',
        model='xyz',
    )

    auditHardware2 = AuditHardware(
        hardwareClass='COMPUTER_SYSTEM',
        description=None,
        vendor='HP',
        model='0815',
    )

    auditHardware3 = AuditHardware(
        hardwareClass='BASE_BOARD',
        name='MSI 2442',
        description='AMD motherboard',
        vendor='MSI',
        model='äüöüöäüöüäüööüö11',
        product=None
    )

    auditHardware4 = AuditHardware(
        hardwareClass='CHASSIS',
        name='Manufacturer XX-112',
        description='A chassis',
        chassisType='Desktop'
    )

    return auditHardware1, auditHardware2, auditHardware3, auditHardware4


def getAuditSoftwares(product=None):
    auditSoftware1 = AuditSoftware(
        name='A software',
        version='1.0.21',
        subVersion='',
        language='',
        architecture='',
        windowsSoftwareId='{480aa013-93a7-488c-89c3-b985b6c8440a}',
        windowsDisplayName='A Software',
        windowsDisplayVersion='1.0.21',
        installSize=129012992
    )

    if product is None:
        product = getLocalbootProducts()[0]

    auditSoftware2 = AuditSoftware(
        name=product.getName(),
        version=product.getProductVersion(),
        subVersion='',
        language='de',
        architecture='x64',
        windowsSoftwareId=product.getWindowsSoftwareIds()[0],
        windowsDisplayName=product.getName(),
        windowsDisplayVersion=product.getProductVersion(),
        installSize=217365267
    )

    auditSoftware3 = AuditSoftware(
        name='my software',
        version='',
        subVersion='12;00;01',
        language='',
        architecture='',
        windowsSoftwareId='my software',
        windowsDisplayName='',
        windowsDisplayVersion='',
        installSize=-1
    )

    auditSoftware4 = AuditSoftware(
        name='söftwäre\n;?&%$$$§$§§$$$§$',
        version=u'\\0012',
        subVersion='\n',
        language='de',
        architecture='',
        windowsSoftwareId='söftwäre\n;?&%$$$§$§§$$$§$',
        windowsDisplayName='söftwäre\n;?&%$$$§$§§$$$§$',
        windowsDisplayVersion='\n\r',
        installSize=-1
    )

    return auditSoftware1, auditSoftware2, auditSoftware3, auditSoftware4


def getAuditSoftwareOnClient(auditSoftwares, clients):
    auditSoftware1, auditSoftware2, auditSoftware3 = auditSoftwares[:3]
    client1, client2 = clients[:2]

    auditSoftwareOnClient1 = AuditSoftwareOnClient(
        name=auditSoftware1.getName(),
        version=auditSoftware1.getVersion(),
        subVersion=auditSoftware1.getSubVersion(),
        language=auditSoftware1.getLanguage(),
        architecture=auditSoftware1.getArchitecture(),
        clientId=client1.getId(),
        uninstallString='c:\\programme\\a software\\unistall.exe /S',
        binaryName=u'',
        firstseen=None,
        lastseen=None,
        state=None,
        usageFrequency=2,
        lastUsed='2009-02-12 09:48:22'
    )

    auditSoftwareOnClient2 = AuditSoftwareOnClient(
        name=auditSoftware2.getName(),
        version=auditSoftware2.getVersion(),
        subVersion=auditSoftware2.getSubVersion(),
        language=auditSoftware2.getLanguage(),
        architecture=auditSoftware2.getArchitecture(),
        clientId=client1.getId(),
        uninstallString='msiexec /x %s' % auditSoftware2.getWindowsSoftwareId(),
        binaryName=u'',
        firstseen=None,
        lastseen=None,
        state=None,
        usageFrequency=None,
        lastUsed=None
    )

    auditSoftwareOnClient3 = AuditSoftwareOnClient(
        name=auditSoftware3.getName(),
        version=auditSoftware3.getVersion(),
        subVersion=auditSoftware3.getSubVersion(),
        language=auditSoftware3.getLanguage(),
        architecture=auditSoftware3.getArchitecture(),
        clientId=client1.getId(),
        uninstallString=None,
        firstseen=None,
        lastseen=None,
        state=None,
        usageFrequency=0,
        lastUsed='2009-08-01 14:11:00'
    )

    auditSoftwareOnClient4 = AuditSoftwareOnClient(
        name=auditSoftware2.getName(),
        version=auditSoftware2.getVersion(),
        subVersion=auditSoftware2.getSubVersion(),
        language=auditSoftware2.getLanguage(),
        architecture=auditSoftware2.getArchitecture(),
        clientId=client2.getId(),
        firstseen=None,
        lastseen=None,
        state=None,
        usageFrequency=0,
        lastUsed=None
    )

    return auditSoftwareOnClient1, auditSoftwareOnClient2, auditSoftwareOnClient3, auditSoftwareOnClient4


def getAuditHardwareOnHost(auditHardwares=None, clients=None):
    auditHardwares = auditHardwares or getAuditHardwares()
    auditHardware1, auditHardware2, auditHardware3 = auditHardwares[:3]

    clients = clients or getClients()
    client1, client2, client3 = clients[:3]

    auditHardwareOnHost1 = AuditHardwareOnHost(
        hostId=client1.getId(),
        hardwareClass='COMPUTER_SYSTEM',
        description=auditHardware1.description,
        vendor=auditHardware1.vendor,
        model=auditHardware1.model,
        serialNumber='843391034-2192',
        systemType='Desktop',
        totalPhysicalMemory=1073741824
    )

    auditHardwareOnHost2 = AuditHardwareOnHost(
        hostId=client2.getId(),
        hardwareClass='COMPUTER_SYSTEM',
        description=auditHardware1.description,
        vendor=auditHardware1.vendor,
        model=auditHardware1.model,
        serialNumber='142343234-9571',
        systemType='Desktop',
        totalPhysicalMemory=1073741824
    )

    auditHardwareOnHost3 = AuditHardwareOnHost(
        hostId=client3.getId(),
        hardwareClass='COMPUTER_SYSTEM',
        description=auditHardware2.description,
        vendor=auditHardware2.vendor,
        model=auditHardware2.model,
        serialNumber='a63c09dd234a213',
        systemType=None,
        totalPhysicalMemory=536870912
    )

    auditHardwareOnHost4 = AuditHardwareOnHost(
        hostId=client1.getId(),
        hardwareClass='BASE_BOARD',
        name=auditHardware3.name,
        description=auditHardware3.description,
        vendor=auditHardware3.vendor,
        model=auditHardware3.model,
        product=auditHardware3.product,
        serialNumber='xxxx-asjdks-sll3kf03-828112'
    )

    auditHardwareOnHost5 = AuditHardwareOnHost(
        hostId=client2.getId(),
        hardwareClass='BASE_BOARD',
        name=auditHardware3.name,
        description=auditHardware3.description,
        vendor=auditHardware3.vendor,
        model=auditHardware3.model,
        product=auditHardware3.product,
        serialNumber='xxxx-asjdks-sll3kf03-213791'
    )

    auditHardwareOnHost6 = AuditHardwareOnHost(
        hostId=client3.getId(),
        hardwareClass='BASE_BOARD',
        name=auditHardware3.name,
        description=auditHardware3.description,
        vendor=auditHardware3.vendor,
        model=auditHardware3.model,
        product=auditHardware3.product,
        serialNumber='xxxx-asjdks-sll3kf03-132290'
    )

    return (auditHardwareOnHost1, auditHardwareOnHost2, auditHardwareOnHost3,
            auditHardwareOnHost4, auditHardwareOnHost5, auditHardwareOnHost6)


@pytest.mark.requiresHwauditConfigFile
def test_insertAuditHardwareOnHost(hardwareAuditBackendWithHistory):
    backend = hardwareAuditBackendWithHistory

    clients = getClients()
    auditHardwares = getAuditHardwares()
    ahoh = getAuditHardwareOnHost(auditHardwares, clients)
    backend.auditHardwareOnHost_createObjects(ahoh)

    historyRelevantActions = 0

    auditHardwareOnHost4update = ahoh[3].clone()
    auditHardwareOnHost4update.setLastseen('2000-01-01 01:01:01')
    backend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)
    historyRelevantActions += 1

    auditHardwareOnHosts = backend.auditHardwareOnHost_getObjects()
    assert len(auditHardwareOnHosts) == len(ahoh) + historyRelevantActions

    auditHardwareOnHosts = backend.auditHardwareOnHost_getObjects(lastseen='2000-01-01 01:01:01')
    assert 1 == len(auditHardwareOnHosts)
    assert auditHardwareOnHost4update == auditHardwareOnHosts[0]

    auditHardwareOnHost4update.setState(0)
    backend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)
    historyRelevantActions += 1

    auditHardwareOnHosts = backend.auditHardwareOnHost_getObjects()
    assert len(auditHardwareOnHosts) == len(ahoh) + historyRelevantActions

    auditHardwareOnHost4update.setLastseen(None)
    backend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)
    historyRelevantActions += 1

    auditHardwareOnHosts = backend.auditHardwareOnHost_getObjects()
    assert len(auditHardwareOnHosts) == len(ahoh) + historyRelevantActions


def testInventoryObjectMethods(licenseManagentAndAuditBackend):
    backend = licenseManagentAndAuditBackend

    auditSoftwaresIn = getAuditSoftwares()
    backend.auditSoftware_createObjects(auditSoftwaresIn)

    licensePools, _ = createLicensePool(backend)

    auditSoftware1 = auditSoftwaresIn[0]
    auditSoftware2 = auditSoftwaresIn[1]
    licensePool1 = licensePools[0]
    licensePool2 = licensePools[1]

    auditSoftwareToLicensePool1 = AuditSoftwareToLicensePool(
        name=auditSoftware1.name,
        version=auditSoftware1.version,
        subVersion=auditSoftware1.subVersion,
        language=auditSoftware1.language,
        architecture=auditSoftware1.architecture,
        licensePoolId=licensePool1.id
    )
    auditSoftwareToLicensePool2 = AuditSoftwareToLicensePool(
        name=auditSoftware2.name,
        version=auditSoftware2.version,
        subVersion=auditSoftware2.subVersion,
        language=auditSoftware2.language,
        architecture=auditSoftware2.architecture,
        licensePoolId=licensePool2.id
    )

    auditSoftwareToLicensePoolsIn = [auditSoftwareToLicensePool1, auditSoftwareToLicensePool2]
    backend.auditSoftwareToLicensePool_createObjects(auditSoftwareToLicensePoolsIn)

    auditSoftwareToLicensePools = backend.auditSoftwareToLicensePool_getObjects()
    assert len(auditSoftwareToLicensePools) == len(auditSoftwareToLicensePoolsIn)


def test_getAuditSoftwareFromBackend(softwareAuditBackend):
    auditSoftwaresIn = getAuditSoftwares()
    softwareAuditBackend.auditSoftware_createObjects(auditSoftwaresIn)

    auditSoftwaresOut = softwareAuditBackend.auditSoftware_getObjects()
    assert len(auditSoftwaresIn) == len(auditSoftwaresOut)
    # TODO: provide a check that no data was changed.


def test_updateAuditSoftware(softwareAuditBackend):
    auditSoftwaresIn = getAuditSoftwares()
    softwareAuditBackend.auditSoftware_createObjects(auditSoftwaresIn)

    auditSoftware3 = auditSoftwaresIn[2]
    auditSoftware3update = AuditSoftware(
        name=auditSoftware3.name,
        version=auditSoftware3.version,
        subVersion=auditSoftware3.subVersion,
        language=auditSoftware3.language,
        architecture=auditSoftware3.architecture,
        windowsSoftwareId=auditSoftware3.windowsSoftwareId,
        windowsDisplayName='updatedDN',
        windowsDisplayVersion=auditSoftware3.windowsDisplayVersion,
        installSize=auditSoftware3.installSize
    )

    softwareAuditBackend.auditSoftware_updateObject(auditSoftware3update)
    auditSoftwares = softwareAuditBackend.auditSoftware_getObjects(windowsDisplayName='updatedDN')
    assert 1 == len(auditSoftwares), u"Expected one audit software object, but found %s on backend." % len(auditSoftwares)
    assert auditSoftware3update == auditSoftwares[0]


def test_deleteAuditSoftware(softwareAuditBackend):
    auditSoftwaresIn = getAuditSoftwares()
    softwareAuditBackend.auditSoftware_createObjects(auditSoftwaresIn)

    as3 = auditSoftwaresIn[2]
    softwareAuditBackend.auditSoftware_deleteObjects(as3)
    auditSoftwares = softwareAuditBackend.auditSoftware_getObjects()

    assert len(auditSoftwares) == len(auditSoftwaresIn) - 1
    assert as3.name not in [a.name for a in auditSoftwares]


def test_insertAuditSoftware(softwareAuditBackend):
    auditSoftwaresIn = getAuditSoftwares()
    softwareAuditBackend.auditSoftware_createObjects(auditSoftwaresIn)

    auditSoftware3 = auditSoftwaresIn[2]
    softwareAuditBackend.auditSoftware_deleteObjects(auditSoftware3)
    softwareAuditBackend.auditSoftware_insertObject(auditSoftware3)
    auditSoftwares = softwareAuditBackend.auditSoftware_getObjects()

    assert len(auditSoftwares) == len(auditSoftwaresIn)


def test_getAuditSoftwareOnClients(softwareAuditBackend):
    asoc, _, _ = fillBackendWithAuditSoftwareOnClient(softwareAuditBackend)
    softwareAuditBackend.auditSoftwareOnClient_createObjects(asoc)

    auditSoftwareOnClients = softwareAuditBackend.auditSoftwareOnClient_getObjects()
    assert len(asoc) == len(auditSoftwareOnClients)


def test_updateAuditSoftwareOnClient(softwareAuditBackend):
    asoc, auditSoftwaresIn, clients = fillBackendWithAuditSoftwareOnClient(softwareAuditBackend)

    client1 = clients[0]
    auditSoftware1 = auditSoftwaresIn[0]
    auditSoftwareOnClient1update = AuditSoftwareOnClient(
        name=auditSoftware1.getName(),
        version=auditSoftware1.getVersion(),
        subVersion=auditSoftware1.getSubVersion(),
        language=auditSoftware1.getLanguage(),
        architecture=auditSoftware1.getArchitecture(),
        clientId=client1.getId(),
        uninstallString=None,
        binaryName='updatedBN',
        firstseen=None,
        lastseen=None,
        state=None,
        usageFrequency=2,
        lastUsed='2009-02-12 09:48:22'
    )

    softwareAuditBackend.auditSoftwareOnClient_updateObject(auditSoftwareOnClient1update)
    auditSoftwareOnClients = softwareAuditBackend.auditSoftwareOnClient_getObjects(binaryName='updatedBN')
    assert 1 == len(auditSoftwareOnClients)
    assert auditSoftwareOnClient1update == auditSoftwareOnClients[0]


def test_deleteAuditSoftwareOnClient(softwareAuditBackend):
    asoc, _, _ = fillBackendWithAuditSoftwareOnClient(softwareAuditBackend)
    softwareAuditBackend.auditSoftwareOnClient_createObjects(asoc)

    asoc1 = asoc[0]
    softwareAuditBackend.auditSoftwareOnClient_deleteObjects(asoc1)
    auditSoftwareOnClients = softwareAuditBackend.auditSoftwareOnClient_getObjects()
    assert len(asoc) - 1 == len(auditSoftwareOnClients)


def test_insertAuditSoftwareOnClient(softwareAuditBackend):
    asoc, _, _ = fillBackendWithAuditSoftwareOnClient(softwareAuditBackend)

    asoc1 = asoc[0]

    softwareAuditBackend.auditSoftwareOnClient_deleteObjects(asoc1)
    auditSoftwareOnClients = softwareAuditBackend.auditSoftwareOnClient_getObjects()
    assert len(auditSoftwareOnClients) == len(asoc) - 1

    softwareAuditBackend.auditSoftwareOnClient_insertObject(asoc1)
    auditSoftwareOnClients = softwareAuditBackend.auditSoftwareOnClient_getObjects()

    assert len(auditSoftwareOnClients) == len(asoc)


def fillBackendWithAuditSoftwareOnClient(backend):
    auditSoftwares = getAuditSoftwares()
    backend.auditSoftware_createObjects(auditSoftwares)

    clients = getClients()
    backend.host_createObjects(clients)

    asoc = getAuditSoftwareOnClient(auditSoftwares, clients)
    backend.auditSoftwareOnClient_createObjects(asoc)

    return asoc, auditSoftwares, clients


@pytest.mark.requiresHwauditConfigFile
def testUpdatingAuditHardware(hardwareAuditBackend):
    auditHardwaresIn = getAuditHardwares()
    hardwareAuditBackend.auditHardware_createObjects(auditHardwaresIn)

    auditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert len(auditHardwares) == len(auditHardwaresIn)

    auditHardware1 = auditHardwaresIn[0]
    auditHardware2 = auditHardwaresIn[1]
    hardwareAuditBackend.auditHardware_deleteObjects([auditHardware1, auditHardware2])
    auditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert len(auditHardwares) == len(auditHardwaresIn) - 2

    hardwareAuditBackend.auditHardware_updateObjects([auditHardware1, auditHardware2])
    assert len(auditHardwares) == len(auditHardwaresIn) - 2


@pytest.mark.requiresHwauditConfigFile
def testDeletingHostShouldDeleteHardwareAuditData(hardwareAuditBackend):
    """
    Deleting a host should delete it's audit data.
    """
    clients = getClients()
    auditHardwares = getAuditHardwares()
    auditHardwareOnHosts = getAuditHardwareOnHost(auditHardwares, clients)

    client1 = clients[0]
    auditHardwareOnHost1 = auditHardwareOnHosts[0]

    hardwareAuditBackend.host_createObjects(client1)
    hardwareAuditBackend.auditHardwareOnHost_createObjects(auditHardwareOnHost1)

    assert 1 == len(hardwareAuditBackend.host_getObjects()), 'Self-test failed: Too much hosts.'
    assert 1 == len(hardwareAuditBackend.auditHardwareOnHost_getObjects()), 'Self-test failed: Too much auditHardwareOnHosts.'

    hardwareAuditBackend.host_deleteObjects([client1])
    assert 0 == len(hardwareAuditBackend.host_getObjects())
    assert 0 == len(hardwareAuditBackend.auditHardwareOnHost_getObjects())

    hardwareAuditBackend.host_createObjects(client1)
    assert 1 == len(hardwareAuditBackend.host_getObjects())
    assert 0 == len(hardwareAuditBackend.auditHardwareOnHost_getObjects())


@pytest.mark.requiresHwauditConfigFile
def testSelecingAuditHardwareOnHostByLastseen(hardwareAuditBackend):
    ahoh, _, _ = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)

    auditHardwareOnHost4update = ahoh[3].clone()
    auditHardwareOnHost4update.setLastseen('2000-01-01 01:01:01')
    hardwareAuditBackend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)

    auditHardwareOnHosts = hardwareAuditBackend.auditHardwareOnHost_getObjects(lastseen='2000-01-01 01:01:01')
    assert len(auditHardwareOnHosts) == 1
    assert auditHardwareOnHost4update == auditHardwareOnHosts[0]


@pytest.mark.parametrize("searchTerms", [
    ['CHASSIS', 'COMPUTER_SYSTEM'],
    ['CHA*IS', '*UTER_SYS*']
])
@pytest.mark.requiresHwauditConfigFile
def test_selectAuditHardwareClasses(hardwareAuditBackend, searchTerms):
    auditHardwaresIn = getAuditHardwares()
    hardwareAuditBackend.auditHardware_createObjects(auditHardwaresIn)

    auditHardwareClasses = [x.getHardwareClass() for x in hardwareAuditBackend.auditHardware_getObjects(hardwareClass=searchTerms)]
    assert auditHardwareClasses

    for auditHardwareClass in auditHardwareClasses:
        assert auditHardwareClass in ['CHASSIS', 'COMPUTER_SYSTEM']


@pytest.mark.requiresHwauditConfigFile
def test_deleteAuditHardware(hardwareAuditBackend):
    auditHardwaresIn = getAuditHardwares()
    hardwareAuditBackend.auditHardware_createObjects(auditHardwaresIn)

    auditHardware1, auditHardware2 = auditHardwaresIn[:2]

    hardwareAuditBackend.auditHardware_deleteObjects([auditHardware1, auditHardware2])
    auditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert len(auditHardwares) == len(auditHardwaresIn) - 2


@pytest.mark.requiresHwauditConfigFile
def testDeletingAllAuditHardware(hardwareAuditBackend):
    auditHardwares = getAuditHardwares()
    hardwareAuditBackend.auditHardware_createObjects(auditHardwares)
    assert hardwareAuditBackend.auditHardware_getObjects()

    hardwareAuditBackend.auditHardware_deleteObjects(auditHardwares)
    auditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert 0 == len(auditHardwares), u"Expected 0 audit hardware objects, but found %s on backend." % len(auditHardwares)


@pytest.mark.requiresHwauditConfigFile
def testCreatingAndGetingAuditHardwareFromBackend(hardwareAuditBackend):
    auditHardwaresIn = getAuditHardwares()
    hardwareAuditBackend.auditHardware_createObjects(auditHardwaresIn)

    auditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert len(auditHardwares) == len(auditHardwaresIn)
    # TODO: check content


@pytest.mark.requiresHwauditConfigFile
def testCreatingAuditHardwareAfterDeletion(hardwareAuditBackend):
    auditHardwares = getAuditHardwares()

    hardwareAuditBackend.auditHardware_createObjects(auditHardwares)
    hardwareAuditBackend.auditHardware_deleteObjects(hardwareAuditBackend.auditHardware_getObjects())

    hardwareAuditBackend.auditHardware_createObjects(auditHardwares)
    receivedAuditHardwares = hardwareAuditBackend.auditHardware_getObjects()
    assert len(receivedAuditHardwares) == len(auditHardwares)


@pytest.mark.requiresHwauditConfigFile
def testDeletingAllAuditHardwareOnHost(hardwareAuditBackend):
    ahoh, _, _ = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)
    hardwareAuditBackend.auditHardwareOnHost_createObjects(ahoh)

    assert hardwareAuditBackend.auditHardwareOnHost_getObjects()

    hardwareAuditBackend.auditHardwareOnHost_delete(hostId=[], hardwareClass=[], firstseen=[], lastseen=[], state=[])
    auditHardwareOnHosts = hardwareAuditBackend.auditHardwareOnHost_getObjects()
    assert 0 == len(auditHardwareOnHosts), u"Expected no audit hardware objects on host, but found %s on backend." % len(auditHardwareOnHosts)


@pytest.mark.requiresHwauditConfigFile
def test_createAuditHardwareOnHost(hardwareAuditBackend):
    ahoh, _, _ = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)

    hardwareAuditBackend.auditHardwareOnHost_delete(hostId=[], hardwareClass=[], firstseen=[], lastseen=[], state=[])
    hardwareAuditBackend.auditHardwareOnHost_createObjects(ahoh)
    auditHardwareOnHosts = hardwareAuditBackend.auditHardwareOnHost_getObjects()
    assert len(auditHardwareOnHosts) == len(ahoh)
    # TODO: check the returned data


@pytest.mark.requiresHwauditConfigFile
def test_updatingAuditHardwareOnHost(hardwareAuditBackend):
    auditHardwareOnHosts, _, _ = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)

    numBefore = len(hardwareAuditBackend.auditHardwareOnHost_getObjects())
    assert numBefore == len(auditHardwareOnHosts)

    auditHardwareOnHost4 = auditHardwareOnHosts[3]
    auditHardwareOnHost4update = auditHardwareOnHost4.clone()
    hardwareAuditBackend.auditHardwareOnHost_updateObject(auditHardwareOnHost4update)
    auditHardwareOnHosts = hardwareAuditBackend.auditHardwareOnHost_getObjects()
    numAfter = len(hardwareAuditBackend.auditHardwareOnHost_getObjects())
    assert numBefore == numAfter


@pytest.mark.requiresHwauditConfigFile
def test_deleteAuditHardwareOnHost(hardwareAuditBackend):
    auditHardwareOnHostsIn, _, _ = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)

    ahoh3, ahoh4 = auditHardwareOnHostsIn[2:4]
    hardwareAuditBackend.auditHardwareOnHost_deleteObjects([ahoh3, ahoh4])
    auditHardwareOnHostsOut = hardwareAuditBackend.auditHardwareOnHost_getObjects()
    assert len(auditHardwareOnHostsIn) - 2 == len(auditHardwareOnHostsOut)

    # Making sure that the deleted IDs arent found anymore.
    assert ahoh3 not in auditHardwareOnHostsOut
    assert ahoh4 not in auditHardwareOnHostsOut


@pytest.mark.requiresHwauditConfigFile
def testAuditHardwareOnHostSetObsolete(hardwareAuditBackend):
    auditHardwareOnHostsIn, _, clients = fillBackendWithAuditHardwareOnHosts(hardwareAuditBackend)

    client3 = clients[2]

    hardwareAuditBackend.auditHardwareOnHost_setObsolete(client3.id)
    auditHardwareOnHosts = hardwareAuditBackend.auditHardwareOnHost_getObjects(hostId=client3.id)
    for auditHardwareOnHost in auditHardwareOnHosts:
        assert auditHardwareOnHost.getState() == 0


def fillBackendWithAuditHardwareOnHosts(backend):
    clients = getClients()
    backend.host_createObjects(clients)

    auditHardwares = getAuditHardwares()
    backend.auditHardware_createObjects(auditHardwares)

    auditHardwareOnHosts = getAuditHardwareOnHost(auditHardwares, clients)
    backend.auditHardwareOnHost_createObjects(auditHardwareOnHosts)

    return auditHardwareOnHosts, auditHardwares, clients
