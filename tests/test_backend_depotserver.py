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

import grp
import os
import pytest
from OPSI.Backend.Depotserver import DepotserverBackend

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
                groupName = g.gr_name
                groupData = grp.getgrnam(groupName)
                break
        else:
            pytest.skip("Unable to find group")

        with patchAddress(fqdn=fakeFQDN):
            with mock.patch('OPSI.Util.Product.grp.getgrnam', lambda x: groupData):
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
