# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2018 uib GmbH <info@uib.de>

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
from OPSI.Exceptions import BackendError
from OPSI.Object import LocalbootProduct, ProductOnDepot

from .helpers import mock, patchAddress
from .test_util import fileAndHash  # test fixture


@pytest.fixture
def depotServerFQDN():
    return "depotserver.test.invalid"


@pytest.fixture
def depotserverBackend(extendedConfigDataBackend, tempDir, depotServerFQDN):
    extendedConfigDataBackend.host_createOpsiDepotserver(depotServerFQDN)

    depot = extendedConfigDataBackend.host_getObjects(id=depotServerFQDN)[0]
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

    with patchAddress(fqdn=depotServerFQDN):
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
    return any(os.path.isdir(listing) for listing in os.listdir(depotPath) if productId == listing)


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


@pytest.mark.requiresModulesFile  # because of SQLite...
@pytest.mark.parametrize("suppressCreation", [False, True])
def testInstallingPackageCreatesPackageContentFile(depotserverBackend, suppressCreation):
    pathToPackage = os.path.join(os.path.dirname(__file__), 'testdata', 'backend', 'testingproduct_23-42.opsi')
    depotserverBackend.depot_installPackage(pathToPackage, suppressPackageContentFileGeneration=suppressCreation)

    depot = depotserverBackend.host_getObjects(type="OpsiDepotserver")[0]
    depotPath = depot.depotLocalUrl.replace('file://', '')

    assert isProductFolderInDepot(depotPath, 'testingproduct')
    assert suppressCreation != os.path.exists(os.path.join(depotPath, 'testingproduct', 'testingproduct.files'))


@pytest.mark.requiresModulesFile  # because of SQLite...
def testInstallingWithLockedProductFails(depotserverBackend, depotServerFQDN):
    product = LocalbootProduct(
        id='testingproduct',
        productVersion=23,
        packageVersion=42
    )
    depotserverBackend.product_insertObject(product)

    lockedProductOnDepot = ProductOnDepot(
        productId='testingproduct',
        productType=product.getType(),
        productVersion=product.getProductVersion(),
        packageVersion=product.getPackageVersion(),
        depotId=depotServerFQDN,
        locked=True
    )
    depotserverBackend.productOnDepot_createObjects(lockedProductOnDepot)

    pathToPackage = os.path.join(os.path.dirname(__file__), 'testdata', 'backend', 'testingproduct_23-42.opsi')
    with pytest.raises(BackendError):
        depotserverBackend.depot_installPackage(pathToPackage)
