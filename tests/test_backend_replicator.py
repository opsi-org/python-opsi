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

import unittest

from OPSI.Backend.Replicator import BackendReplicator

from .Backends import getTestBackend
from .BackendTestMixins.Audit import (getAuditHardwares,
    getAuditHardwareOnHost, getAuditSoftwares, getAuditSoftwareOnClient)
from .BackendTestMixins.Clients import getClients
from .BackendTestMixins.Configs import getConfigs, getConfigStates
from .BackendTestMixins.Groups import (getHostGroups, getObjectToGroups,
    getProductGroup)
from .BackendTestMixins.Hosts import getConfigServer, getDepotServers
from .BackendTestMixins.Licenses import getLicenseContracts
from .BackendTestMixins.Products import (getLocalbootProducts,
    getNetbootProduct, getProductDepdencies, getProductProperties,
    getProductsOnDepot, getProductsOnClients, getProductPropertyStates)


class ReplicatorTestCase(unittest.TestCase):
    # TODO: there are some cases we should test
    # * cleanupBackend
    # * handling backends with / without license management
    # * handling replicating the audit data

    def testInitialisation(self):
        replicator = BackendReplicator(None, None)

    def testReplication(self):
        with getTestBackend(extended=True) as readBackend:
            fillBackend(readBackend)

            with getTestBackend() as writeBackend:
                replicator = BackendReplicator(readBackend, writeBackend)
                replicator.replicate()

                self.checkBackendDataIsEqual(readBackend, writeBackend)

    def checkBackendDataIsEqual(self, first, second):
        self.assertEquals(first.host_getObjects(), second.host_getObjects())
        self.assertEquals(first.product_getObjects(), second.product_getObjects())
        self.assertEquals(first.config_getObjects(), second.config_getObjects())
        self.assertEquals(first.group_getObjects(), second.group_getObjects())
        self.assertEquals(first.licenseContract_getObjects(), second.licenseContract_getObjects())
        self.assertEquals(first.licensePool_getObjects(), second.licensePool_getObjects())
        self.assertEquals(first.softwareLicense_getObjects(), second.softwareLicense_getObjects())
        self.assertEquals(first.auditHardware_getObjects(), second.auditHardware_getObjects())
        self.assertEquals(first.auditSoftware_getObjects(), second.auditSoftware_getObjects())
        self.assertEquals(first.productDependency_getObjects(), second.productDependency_getObjects())
        self.assertEquals(first.productProperty_getObjects(), second.productProperty_getObjects())
        self.assertEquals(first.productOnDepot_getObjects(), second.productOnDepot_getObjects())
        self.assertEquals(first.productOnClient_getObjects(), second.productOnClient_getObjects())
        self.assertEquals(first.productPropertyState_getObjects(), second.productPropertyState_getObjects())
        self.assertEquals(first.configState_getObjects(), second.configState_getObjects())
        self.assertEquals(first.objectToGroup_getObjects(), second.objectToGroup_getObjects())
        self.assertEquals(first.auditHardwareOnHost_getObjects(), second.auditHardwareOnHost_getObjects())
        self.assertEquals(first.auditSoftwareOnClient_getObjects(), second.auditSoftwareOnClient_getObjects())
        self.assertEquals(first.softwareLicenseToLicensePool_getObjects(), second.softwareLicenseToLicensePool_getObjects())
        self.assertEquals(first.licenseOnClient_getObjects(), second.licenseOnClient_getObjects())
        self.assertEquals(first.auditSoftwareToLicensePool_getObjects(), second.auditSoftwareToLicensePool_getObjects())


def fillBackend(backend, licenseManagementData=False):
    # TODO: remove the asserts from the backend - they should be subject to tests!
    configServer, depotServer, clients = fillBackendWithHosts(backend)
    products = fillBackendWithProducts(backend)
    configs = fillBackendWithConfigs(backend)
    groups = fillBackendWithGroups(backend)

    if licenseManagementData:
        fillBackendWithLicenseContracts(backend)
        fillBackendWithLicensePools(backend)
        fillBackendWithSoftwareLicenses(backend)

    auditHardwares = fillBackendWithAuditHardwares(backend)
    auditSoftwares = fillBackendWithAuditSoftwares(backend)
    fillBackendWithProductDependencys(backend, products)
    productProperties = fillBackendWithProductPropertys(backend, products)
    fillBackendWithProductOnDepots(backend, products, configServer, depotServer)
    fillBackendWithProductOnClients(backend, products, clients)
    fillBackendWithProductPropertyStates(backend, productProperties, depotServer, clients)
    fillBackendWithConfigStates(backend, configs, clients, depotServer)
    fillBackendWithObjectToGroups(backend, groups, clients)
    fillBackendWithAuditHardwareOnHosts(backend, auditHardwares, clients)
    fillBackendWithAuditSoftwareOnClients(backend, auditSoftwares, clients)

    if licenseManagementData:
        fillBackendWithSoftwareLicenseToLicensePools(backend)
        fillBackendWithLicenseOnClients(backend)
        fillBackendWithAuditSoftwareToLicensePools(backend)


def fillBackendWithHosts(backend):
    configServer = getConfigServer()
    backend.host_insertObject(configServer)

    depots = getDepotServers()
    backend.host_createObjects(depots)

    clients = getClients()
    backend.host_createObjects(clients)

    assert len(clients) + len(depots) + 1 == len(backend.host_getObjects())

    return configServer, depots, clients


def fillBackendWithProducts(backend):
    netbootProduct = getNetbootProduct()
    backend.product_createObjects(netbootProduct)

    localbootProducts = getLocalbootProducts()
    backend.product_createObjects(localbootProducts)

    assert len(localbootProducts) + 1 == len(backend.product_getObjects())

    return [netbootProduct] + list(localbootProducts)


def fillBackendWithConfigs(backend):
    configs = getConfigs()
    assert len(configs) > 0

    backend.config_createObjects(configs)
    assert len(configs) == len(backend.config_getObjects())

    return configs


def fillBackendWithGroups(backend):
    groups = list(getHostGroups())
    groups.append(getProductGroup())
    assert len(groups) > 0

    backend.group_createObjects(groups)
    assert len(groups) == len(backend.group_getObjects())

    return groups


def fillBackendWithLicenseContracts(backend):
    licenseContracts = getLicenseContracts()
    backend.licenseContract_createObjects(licenseContracts)

    assert len(licenseContracts) == len(backend.licenseContract_getObjects())


def fillBackendWithLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithSoftwareLicenses(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithAuditHardwares(backend):
    auditHardwares = getAuditHardwares()
    assert len(auditHardwares) > 0

    backend.auditHardware_createObjects(auditHardwares)
    assert len(auditHardwares) == len(backend.auditHardware_getObjects())

    return auditHardwares


def fillBackendWithAuditSoftwares(backend):
    auditSoftwares = getAuditSoftwares()
    assert len(auditSoftwares) > 0

    backend.auditSoftware_createObjects(auditSoftwares)
    assert len(auditSoftwares) == len(backend.auditSoftware_getObjects())

    return auditSoftwares


def fillBackendWithProductDependencys(backend, products):
    dependencies = getProductDepdencies(products)
    assert len(dependencies) > 0

    backend.productDependency_createObjects(dependencies)
    assert len(dependencies) == len(backend.productDependency_getObjects())


def fillBackendWithProductPropertys(backend, products):
    properties = getProductProperties(products)
    assert len(properties) > 0

    backend.productProperty_createObjects(properties)
    assert len(properties) == len(backend.productProperty_getObjects())

    return properties


def fillBackendWithProductOnDepots(backend, products, configServer, depotServer):
    productsOnDepots = getProductsOnDepot(products, configServer, depotServer)
    assert len(productsOnDepots) > 0

    backend.productOnDepot_createObjects(productsOnDepots)
    assert len(productsOnDepots) == len(backend.productOnDepot_getObjects())


def fillBackendWithProductOnClients(backend, products, clients):
    productsOnClients = getProductsOnClients(products, clients)
    assert len(productsOnClients) > 0

    backend.productOnClient_createObjects(productsOnClients)
    assert len(productsOnClients) == len(backend.productOnClient_getObjects())


def fillBackendWithProductPropertyStates(backend, productProperties, depotServer, clients):
    productPropertyStates = getProductPropertyStates(productProperties, depotServer, clients)
    assert len(productPropertyStates) > 0

    backend.productPropertyState_createObjects(productPropertyStates)
    assert len(productPropertyStates) == len(backend.productPropertyState_getObjects())


def fillBackendWithConfigStates(backend, configs, clients, depotserver):
    configStates = getConfigStates(configs, clients, depotserver)
    assert len(configStates) > 0

    backend.configState_createObjects(configStates)
    assert len(configStates) == len(backend.configState_getObjects())


def fillBackendWithObjectToGroups(backend, groups, clients):
    objectToGroups = getObjectToGroups(groups, clients)
    assert len(objectToGroups) > 0

    backend.objectToGroup_createObjects(objectToGroups)
    assert len(objectToGroups) == len(backend.objectToGroup_getObjects())


def fillBackendWithAuditHardwareOnHosts(backend, auditHardwares, clients):
    ahoh = getAuditHardwareOnHost(auditHardwares, clients)
    assert len(ahoh) > 0

    backend.auditHardwareOnHost_createObjects(ahoh)
    assert len(ahoh) == len(backend.auditHardwareOnHost_getObjects())


def fillBackendWithAuditSoftwareOnClients(backend, auditSoftwares, clients):
    asoc = getAuditSoftwareOnClient(auditSoftwares, clients)
    assert len(asoc) > 0

    backend.auditSoftwareOnClient_createObjects(asoc)
    assert len(asoc) == len(backend.auditSoftwareOnClient_getObjects())


def fillBackendWithSoftwareLicenseToLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithLicenseOnClients(backend):
    raise NotImplementedError("This is yet to be implemented.")


def fillBackendWithAuditSoftwareToLicensePools(backend):
    raise NotImplementedError("This is yet to be implemented.")


if __name__ == '__main__':
    unittest.main()
