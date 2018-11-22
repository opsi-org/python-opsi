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

import grp
import os
import pwd

import pytest

from OPSI.Backend.Depotserver import DepotserverBackend
from OPSI.Exceptions import BackendError
from OPSI.Object import LocalbootProduct, ProductOnDepot

from .helpers import mock, patchAddress
from .test_util import fileAndHash  # test fixture


@pytest.fixture
def depotDirectory(tempDir):
    return tempDir


@pytest.fixture
def depotServerFQDN():
    return "depotserver.test.invalid"


@pytest.fixture
def depotserverBackend(extendedConfigDataBackend, depotDirectory, depotServerFQDN):
    extendedConfigDataBackend.host_createOpsiDepotserver(depotServerFQDN)

    depot = extendedConfigDataBackend.host_getObjects(id=depotServerFQDN)[0]
    depot.depotLocalUrl = 'file://' + depotDirectory
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


@pytest.fixture
def testPackageFile():
    return os.path.join(os.path.dirname(__file__), 'testdata', 'backend', 'testingproduct_23-42.opsi')


def testInstallingPackageOnDepotserver(depotserverBackend, testPackageFile, depotDirectory):
    depotserverBackend.depot_installPackage(testPackageFile)

    products = depotserverBackend.product_getObjects()
    assert len(products) == 1

    product = products[0]
    assert product.id == 'testingproduct'
    assert product.productVersion == '23'
    assert product.packageVersion == '42'

    assert isProductFolderInDepot(depotDirectory, 'testingproduct')


def isProductFolderInDepot(depotPath, productId):
    return any(os.path.isdir(listing) for listing in os.listdir(depotPath) if productId == listing)


def testInstallingPackageOnDepotserverWithForcedProductId(depotserverBackend, testPackageFile, depotDirectory):
    wantedProductId = 'jumpinthefire'

    depotserverBackend.depot_installPackage(testPackageFile, forceProductId=wantedProductId)

    products = depotserverBackend.product_getObjects()
    assert len(products) == 1

    product = products[0]
    assert product.id == wantedProductId
    assert product.productVersion == '23'
    assert product.packageVersion == '42'

    assert isProductFolderInDepot(depotDirectory, wantedProductId)
    assert not isProductFolderInDepot(depotDirectory, 'testingproduct')

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


def testReadingMd5sum(depotserverBackend, fileAndHash):
    filename, expectedHash = fileAndHash
    assert expectedHash == depotserverBackend.depot_getMD5Sum(filename)


@pytest.mark.parametrize("suppressCreation", [False, True])
def testInstallingPackageCreatesPackageContentFile(depotserverBackend, suppressCreation, testPackageFile, depotDirectory):
    depotserverBackend.depot_installPackage(testPackageFile, suppressPackageContentFileGeneration=suppressCreation)

    assert isProductFolderInDepot(depotDirectory, 'testingproduct')
    assert suppressCreation != os.path.exists(os.path.join(depotDirectory, 'testingproduct', 'testingproduct.files'))


@pytest.mark.parametrize("forceInstallation", [False, True])
def testInstallingWithLockedProduct(depotserverBackend, depotServerFQDN, testPackageFile, forceInstallation, depotDirectory):
    product = LocalbootProduct(
        id='testingproduct',
        productVersion=23,
        packageVersion=41  # One lower than from the package file.
    )
    depotserverBackend.product_insertObject(product)

    lockedProductOnDepot = ProductOnDepot(
        productId=product.getId(),
        productType=product.getType(),
        productVersion=product.getProductVersion(),
        packageVersion=product.getPackageVersion(),
        depotId=depotServerFQDN,
        locked=True
    )
    depotserverBackend.productOnDepot_createObjects(lockedProductOnDepot)

    if not forceInstallation:
        with pytest.raises(BackendError):
            depotserverBackend.depot_installPackage(testPackageFile)

        # Checking that the package version does not get changed
        pod = depotserverBackend.productOnDepot_getObjects(productId=product.getId(), depotId=depotServerFQDN)[0]
        assert pod.locked is True
        assert '23' == pod.productVersion
        assert '41' == pod.packageVersion
    else:
        depotserverBackend.depot_installPackage(testPackageFile, force=True)

        pod = depotserverBackend.productOnDepot_getObjects(productId=product.getId(), depotId=depotServerFQDN)[0]
        assert pod.locked is False
        assert '23' == pod.productVersion
        assert '42' == pod.packageVersion

        assert isProductFolderInDepot(depotDirectory, product.id)


def testUninstallingProduct(depotserverBackend, depotServerFQDN, testPackageFile, depotDirectory):
    productId = 'testingproduct'
    depotserverBackend.depot_installPackage(testPackageFile, force=True)

    assert isProductFolderInDepot(depotDirectory, productId)

    depotserverBackend.depot_uninstallPackage(productId)

    assert not isProductFolderInDepot(depotDirectory, productId)
    assert not depotserverBackend.productOnDepot_getObjects(productId=productId, depotId=depotServerFQDN)
    assert not depotserverBackend.product_getObjects(id=productId)


@pytest.mark.parametrize("forceUninstall", [False, True])
def testUninstallingLockedProduct(depotserverBackend, depotServerFQDN, testPackageFile, depotDirectory, forceUninstall):
    productId = 'testingproduct'

    depotserverBackend.depot_installPackage(testPackageFile, force=True)
    assert isProductFolderInDepot(depotDirectory, productId)

    pod = depotserverBackend.productOnDepot_getObjects(productId=productId, depotId=depotServerFQDN)[0]
    pod.setLocked(True)
    depotserverBackend.productOnDepot_updateObject(pod)

    if not forceUninstall:
        with pytest.raises(BackendError):
            depotserverBackend.depot_uninstallPackage(productId)

        assert isProductFolderInDepot(depotDirectory, productId)
        assert depotserverBackend.productOnDepot_getObjects(productId=productId, depotId=depotServerFQDN)
        assert depotserverBackend.product_getObjects(id=productId)
    else:
        depotserverBackend.depot_uninstallPackage(productId, force=forceUninstall)

        assert not isProductFolderInDepot(depotDirectory, productId)
        assert not depotserverBackend.productOnDepot_getObjects(productId=productId, depotId=depotServerFQDN)
        assert not depotserverBackend.product_getObjects(id=productId)
