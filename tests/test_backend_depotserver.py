#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016 uib GmbH <info@uib.de>

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
Testing Depotserver features.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import pwd
import grp
import os
import pytest
from OPSI.Backend.Depotserver import DepotserverBackend

from .test_util import fileAndHash
from .helpers import mock, patchAddress, workInTemporaryDirectory


@pytest.fixture
def depotserverBackend(extendedConfigDataBackend):
    fakeFQDN = "depotserver.test.invalid"

    extendedConfigDataBackend.host_createOpsiDepotserver(fakeFQDN)

    depot = extendedConfigDataBackend.host_getObjects(id=fakeFQDN)[0]

    with workInTemporaryDirectory() as tempDir:
        depot.depotLocalUrl = 'file://' + tempDir
        extendedConfigDataBackend.host_updateObject(depot)

        for g in grp.getgrall():
            if g.gr_gid == os.getgid():
                groupData = grp.getgrnam(g.gr_name)
                break
        else:
            pytest.skip("Unable to get group data for patching.")

        for u in pwd.getpwall():
            if u.pw_uid == os.getuid():
                userData = pwd.getpwnam(u.pw_name)
                break
        else:
            pytest.skip("Unable to get user data for mocking.")

        with patchAddress(fqdn=fakeFQDN):
            with mock.patch('OPSI.Util.Product.grp.getgrnam', lambda x: groupData):
                with mock.patch('OPSI.Util.Product.pwd.getpwnam', lambda x: userData):
                    yield DepotserverBackend(extendedConfigDataBackend)


@pytest.mark.requiresModulesFile  # because of SQLite...
def testInstallingPackageOnDepotserver(depotserverBackend):
    pathToPackage = os.path.join(os.path.dirname(__file__), 'testdata', 'backend', 'testingproduct_23-42.opsi')
    depotserverBackend.depot_installPackage(pathToPackage)

    products = depotserverBackend.product_getObjects()
    assert len(products) == 1

    product = products[0]
    assert product.id == 'testingproduct'
    assert product.productVersion == '23'
    assert product.packageVersion == '42'

    depot = depotserverBackend.host_getObjects(type="OpsiDepotserver")[0]
    depotPath = depot.depotLocalUrl.replace('file://', '')

    assert isProductFolderInDepot(depotPath, 'testingproduct')


def isProductFolderInDepot(depotPath, productId):
    for listing in os.listdir(depotPath):
        if productId == listing:
            if os.path.isdir(listing):
                return True

    return False


@pytest.mark.requiresModulesFile  # because of SQLite...
def testInstallingPackageOnDepotserverWithForcedProductId(depotserverBackend):
    pathToPackage = os.path.join(os.path.dirname(__file__), 'testdata', 'backend', 'testingproduct_23-42.opsi')
    wantedProductId = 'jumpinthefire'

    depotserverBackend.depot_installPackage(pathToPackage, forceProductId=wantedProductId)

    products = depotserverBackend.product_getObjects()
    assert len(products) == 1

    product = products[0]
    assert product.id == wantedProductId
    assert product.productVersion == '23'
    assert product.packageVersion == '42'

    depot = depotserverBackend.host_getObjects(type="OpsiDepotserver")[0]
    depotPath = depot.depotLocalUrl.replace('file://', '')

    assert isProductFolderInDepot(depotPath, wantedProductId)
    assert not isProductFolderInDepot(depotPath, 'testingproduct')

    dependencies = depotserverBackend.productDependency_getObjects()
    assert len(dependencies) == 1
    dependency = dependencies[0]
    assert dependency.productId == wantedProductId
    assert dependency.requiredProductId == 'javavm'

    properties = depotserverBackend.productProperty_getObjects()
    assert len(properties) == 1
    prodProperty = properties[0]
    assert prodProperty.productId == wantedProductId
    assert prodProperty.propertyId == 'awesome'

    assert prodProperty.productVersion == product.productVersion
    assert prodProperty.packageVersion == product.packageVersion


@pytest.mark.requiresModulesFile  # because of SQLite...
def testReadingMd5sum(depotserverBackend, fileAndHash):
    filename, expectedHash = fileAndHash
    assert expectedHash == depotserverBackend.depot_getMD5Sum(filename)
