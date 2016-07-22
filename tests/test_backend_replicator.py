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
Testing backend replication.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import sys
import unittest

from OPSI.Backend.Replicator import BackendReplicator

from .Backends import getTestBackend
from .BackendTestMixins.Clients import getClients
from .BackendTestMixins.Configs import getConfigs, getConfigStates
from .BackendTestMixins.Hosts import getConfigServer, getDepotServers
from .test_license_management import getLicenseContracts
from .BackendTestMixins.Products import (getLocalbootProducts,
    getNetbootProduct, getProductDepdencies, getProductProperties,
    getProductsOnDepot, getProductsOnClients, getProductPropertyStates)
from .test_groups import (getHostGroups, getObjectToGroups, getProductGroup)
from .test_software_and_hardware_audit import (getAuditHardwares,
    getAuditHardwareOnHost, getAuditSoftwares, getAuditSoftwareOnClient)


class ReplicatorTestCase(unittest.TestCase):
    # TODO: there are some cases we should test
    # * handling backends with / without license management
    # * test replicating into different backends (file / mysql)
    # * test with serverID, depotID, hostID given

    def testInitialisation(self):
        replicator = BackendReplicator(None, None)

    def testReplication(self):
        with getTestBackend(extended=True) as readBackend:
            fillBackend(readBackend)
            checkIfBackendIsFilled(readBackend)

            with getTestBackend() as writeBackend:
                replicator = BackendReplicator(readBackend, writeBackend)
                replicator.replicate()

                self.checkBackendDataIsEqual(readBackend, writeBackend)

    def testReplicationWithoutAuditData(self):
        with getTestBackend(extended=True) as readBackend:
            fillBackend(readBackend)
            checkIfBackendIsFilled(readBackend)

            with getTestBackend() as writeBackend:
                replicator = BackendReplicator(readBackend, writeBackend)
                replicator.replicate(audit=False)

                self.checkBackendDataIsEqual(readBackend, writeBackend, checkAuditData=False)

                self.assertEquals(0, len(writeBackend.auditHardware_getObjects()))
                self.assertEquals(0, len(writeBackend.auditSoftware_getObjects()))
                self.assertEquals(0, len(writeBackend.auditHardwareOnHost_getObjects()))
                self.assertEquals(0, len(writeBackend.auditSoftwareOnClient_getObjects()))

    def checkBackendDataIsEqual(self, first, second, checkAuditData=True):
        self.assertEquals(first.host_getObjects(), second.host_getObjects())
        self.assertEquals(first.product_getObjects(), second.product_getObjects())
        self.assertEquals(first.config_getObjects(), second.config_getObjects())
        self.assertEquals(first.group_getObjects(), second.group_getObjects())
        self.assertEquals(first.licenseContract_getObjects(), second.licenseContract_getObjects())
        self.assertEquals(first.licensePool_getObjects(), second.licensePool_getObjects())
        self.assertEquals(first.softwareLicense_getObjects(), second.softwareLicense_getObjects())
        self.assertEquals(first.productDependency_getObjects(), second.productDependency_getObjects())
        self.assertEquals(first.productProperty_getObjects(), second.productProperty_getObjects())
        self.assertEquals(first.productOnDepot_getObjects(), second.productOnDepot_getObjects())
        self.assertEquals(first.productOnClient_getObjects(), second.productOnClient_getObjects())
        self.assertEquals(first.productPropertyState_getObjects(), second.productPropertyState_getObjects())
        self.assertEquals(first.configState_getObjects(), second.configState_getObjects())
        self.assertEquals(first.objectToGroup_getObjects(), second.objectToGroup_getObjects())
        self.assertEquals(first.softwareLicenseToLicensePool_getObjects(), second.softwareLicenseToLicensePool_getObjects())
        self.assertEquals(first.licenseOnClient_getObjects(), second.licenseOnClient_getObjects())
        self.assertEquals(first.auditSoftwareToLicensePool_getObjects(), second.auditSoftwareToLicensePool_getObjects())

        if checkAuditData and sys.version_info >= (2, 7):
            self.assertEquals(first.auditHardware_getObjects(), second.auditHardware_getObjects())
            self.assertEquals(first.auditSoftware_getObjects(), second.auditSoftware_getObjects())
            self.assertEquals(first.auditHardwareOnHost_getObjects(), second.auditHardwareOnHost_getObjects())
            self.assertEquals(first.auditSoftwareOnClient_getObjects(), second.auditSoftwareOnClient_getObjects())


def fillBackend(backend, licenseManagementData=False):
    configServer, depotServer, clients = fillBackendWithHosts(backend)
    products = fillBackendWithProducts(backend)
    configs = fillBackendWithConfigs(backend)
    groups = fillBackendWithGroups(backend)

    if licenseManagementData:
        fillBackendWithLicenseContracts(backend)
        fillBackendWithLicensePools(backend)
        fillBackendWithSoftwareLicenses(backend)

    fillBackendWithProductDependencys(backend, products)
    productProperties = fillBackendWithProductPropertys(backend, products)
    fillBackendWithProductOnDepots(backend, products, configServer, depotServer)
    fillBackendWithProductOnClients(backend, products, clients)
    fillBackendWithProductPropertyStates(backend, productProperties, depotServer, clients)
    fillBackendWithConfigStates(backend, configs, clients, depotServer)
    fillBackendWithObjectToGroups(backend, groups, clients)
    auditSoftwares = fillBackendWithAuditSoftwares(backend)
    fillBackendWithAuditSoftwareOnClients(backend, auditSoftwares, clients)

    if existsHwAuditConfig():
        auditHardwares = fillBackendWithAuditHardwares(backend)
        fillBackendWithAuditHardwareOnHosts(backend, auditHardwares, clients)

    if licenseManagementData:
        fillBackendWithSoftwareLicenseToLicensePools(backend)
        fillBackendWithLicenseOnClients(backend)
        fillBackendWithAuditSoftwareToLicensePools(backend)


def checkIfBackendIsFilled(backend, licenseManagementData=False):
    assert len(backend.host_getObjects()) > 2
    assert len(backend.product_getObjects()) > 2
    assert len(backend.config_getObjects()) > 0
    assert len(backend.group_getObjects()) > 2

    if licenseManagementData:
        # TODO: check licenseManagementData
        assert len(backend.licenseContract_getObjects()) > 0
        # fillBackendWithLicensePools(backend)
        # fillBackendWithSoftwareLicenses(backend)

    assert len(backend.productDependency_getObjects()) > 0
    assert len(backend.productProperty_getObjects()) > 0
    assert len(backend.productOnDepot_getObjects()) > 0
    assert len(backend.productOnClient_getObjects()) > 0
    assert len(backend.productPropertyState_getObjects()) > 0
    assert len(backend.objectToGroup_getObjects()) > 0
    assert len(backend.configState_getObjects()) > 0
    assert len(backend.auditSoftware_getObjects()) > 0
    assert len(backend.auditSoftwareOnClient_getObjects()) > 0

    if existsHwAuditConfig():
        assert len(backend.auditHardwareOnHost_getObjects()) > 0
        assert len(backend.auditHardware_getObjects()) > 0


def existsHwAuditConfig():
    return os.path.exists('/etc/opsi/hwaudit/opsihwaudit.conf')


def fillBackendWithHosts(backend):
    configServer = getConfigServer()
    backend.host_insertObject(configServer)

    depots = getDepotServers()
    backend.host_createObjects(depots)

    clients = getClients()
    backend.host_createObjects(clients)

    return configServer, depots, clients


def fillBackendWithProducts(backend):
    netbootProduct = getNetbootProduct()
    backend.product_createObjects(netbootProduct)

    localbootProducts = getLocalbootProducts()
    backend.product_createObjects(localbootProducts)

    return [netbootProduct] + list(localbootProducts)


def fillBackendWithConfigs(backend):
    configs = getConfigs()
    backend.config_createObjects(configs)

    return configs


def fillBackendWithGroups(backend):
    groups = list(getHostGroups())
    groups.append(getProductGroup())

    backend.group_createObjects(groups)

    return groups


def fillBackendWithLicenseContracts(backend):
    licenseContracts = getLicenseContracts()
    backend.licenseContract_createObjects(licenseContracts)


def fillBackendWithLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithSoftwareLicenses(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithAuditHardwares(backend):
    if not existsHwAuditConfig():
        return []

    auditHardwares = getAuditHardwares()
    backend.auditHardware_createObjects(auditHardwares)

    return auditHardwares


def fillBackendWithAuditSoftwares(backend):
    auditSoftwares = getAuditSoftwares()
    backend.auditSoftware_createObjects(auditSoftwares)

    return auditSoftwares


def fillBackendWithProductDependencys(backend, products):
    dependencies = getProductDepdencies(products)
    backend.productDependency_createObjects(dependencies)


def fillBackendWithProductPropertys(backend, products):
    properties = getProductProperties(products)
    backend.productProperty_createObjects(properties)

    return properties


def fillBackendWithProductOnDepots(backend, products, configServer, depotServer):
    productsOnDepots = getProductsOnDepot(products, configServer, depotServer)
    backend.productOnDepot_createObjects(productsOnDepots)


def fillBackendWithProductOnClients(backend, products, clients):
    productsOnClients = getProductsOnClients(products, clients)
    backend.productOnClient_createObjects(productsOnClients)

    return productsOnClients


def fillBackendWithProductPropertyStates(backend, productProperties, depotServer, clients):
    productPropertyStates = getProductPropertyStates(productProperties, depotServer, clients)
    backend.productPropertyState_createObjects(productPropertyStates)


def fillBackendWithConfigStates(backend, configs, clients, depotserver):
    configStates = getConfigStates(configs, clients, depotserver)
    backend.configState_createObjects(configStates)


def fillBackendWithObjectToGroups(backend, groups, clients):
    objectToGroups = getObjectToGroups(groups, clients)
    backend.objectToGroup_createObjects(objectToGroups)


def fillBackendWithAuditHardwareOnHosts(backend, auditHardwares, clients):
    if not auditHardwares:
        return

    ahoh = getAuditHardwareOnHost(auditHardwares, clients)
    backend.auditHardwareOnHost_createObjects(ahoh)


def fillBackendWithAuditSoftwareOnClients(backend, auditSoftwares, clients):
    asoc = getAuditSoftwareOnClient(auditSoftwares, clients)
    assert len(asoc) > 0
    backend.auditSoftwareOnClient_createObjects(asoc)
    assert len(backend.auditSoftwareOnClient_getObjects()) > 0


def fillBackendWithSoftwareLicenseToLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithLicenseOnClients(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithAuditSoftwareToLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


if __name__ == '__main__':
    unittest.main()
