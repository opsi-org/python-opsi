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
This tests what usually is found under
``/etc/opsi/backendManager/extend.de/10_wim.conf``.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

from contextlib import contextmanager

from OPSI.System import which
from OPSI.Object import UnicodeProductProperty, ProductOnDepot
from .Backends.File import FileBackendBackendManagerMixin
from .BackendTestMixins.Hosts import getConfigServer
from .BackendTestMixins.Products import getNetbootProduct
from .test_util_wim import fakeWIMEnvironment
from .helpers import getLocalFQDN, mock, unittest


class WimFunctionsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):

    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testUpdatingWimFailsWithInvalidObjectId(self):
        self.assertRaises(ValueError, self.backend.updateWIMConfig, '')
        self.assertRaises(ValueError, self.backend.updateWIMConfig, None)

    def testUpdatingWimFailsWithInvalidObjectId(self):
        self.assertRaises(OSError, self.backend.updateWIMConfigFromPath, '', None)

    def testUpdatingWim(self):
        print(self.backend.productOnDepot_getObjects())

        with fakeWIMEnvironment():
            fillBackend(self.backend)
            with mock.patch('OPSI.Util.WIM.os.path.exists', lambda _: True):
                # self.backend.updateWIMConfig('testWindows')
                pass


def fillBackend(backend):
    return


    backend.backend_createBase()

    configServer = getConfigServer()
    backend.host_insertObject(configServer)

    product = getNetbootProduct()
    product.id = 'testWindows'
    backend.product_insertObject(product)

    print(backend.product_getObjects())

    productOnDepot = ProductOnDepot(
        productId=product.id,
        productType=product.getType(),
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        depotId=configServer.id,
        locked=False
    )
    backend.productOnDepot_insertObject(productOnDepot)

    imagenameProductProperty = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"imagename",
        # description=u'i386 dir to use as installation source',
        possibleValues=["i386"],
        defaultValues=["i386"],
        editable=True,
        multiValue=False
    )
    systemLanguageProductProperty = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"system_language",
        # description=u'i386 dir to use as installation source',
        possibleValues=["i386"],
        defaultValues=["i386"],
        editable=True,
        multiValue=False
    )
    backend.productProperty_insertObject(imagenameProductProperty)
    backend.productProperty_insertObject(systemLanguageProductProperty)

    # productOnDepot1 = ProductOnDepot(
    #     productId=product.getId(),
    #     productType=product.getType(),
    #     productVersion=product.getProductVersion(),
    #     packageVersion=product.getPackageVersion(),
    #     depotId=depotserver1.getId(),
    #     locked=False
    # )


if __name__ == '__main__':
    unittest.main()
