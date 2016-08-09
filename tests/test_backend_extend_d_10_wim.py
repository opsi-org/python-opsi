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
from OPSI.Object import NetbootProduct, ProductOnDepot, UnicodeProductProperty
from .Backends.File import FileBackendBackendManagerMixin
from .BackendTestMixins.Hosts import getConfigServer
from .test_util_wim import fakeWIMEnvironment
from .helpers import getLocalFQDN, mock, patchAddress, patchEnvironmentVariables, unittest


class WimFunctionsTestCase(unittest.TestCase, FileBackendBackendManagerMixin):

    def setUp(self):
        self.setUpBackend()

    def tearDown(self):
        self.tearDownBackend()

    def testUpdatingWimFailsWithInvalidObjectId(self):
        self.assertRaises(ValueError, self.backend.updateWIMConfig, '')
        self.assertRaises(ValueError, self.backend.updateWIMConfig, None)

    def testUpdatingWimFailsWithInvalidProductId(self):
        self.assertRaises(OSError, self.backend.updateWIMConfigFromPath, '', '')

    def testUpdatingWim(self):
        with patchAddress(fqdn=getLocalFQDN()):
            with patchEnvironmentVariables(OPSI_HOSTNAME=getLocalFQDN()):
                with fakeWIMEnvironment(self._fileTempDir):
                    fillBackend(self.backend)

                    with mock.patch('OPSI.Util.WIM.os.path.exists', lambda _: True):
                        self.backend.updateWIMConfig('testwindows')

                    imagename = self.backend.productProperty_getObjects(propertyId="imagename", productId='testwindows')
                    imagename = imagename[0]

                    possibleImageNames = set([
                        u'Windows 7 HOMEBASICN', u'Windows 7 HOMEPREMIUMN',
                        u'Windows 7 PROFESSIONALN', u'Windows 7 STARTERN',
                        u'Windows 7 ULTIMATEN'
                    ])
                    self.assertEquals(possibleImageNames, set(imagename.possibleValues))
                    self.assertTrue(imagename.defaultValues[0] in imagename.possibleValues)

                    language = self.backend.productProperty_getObjects(propertyId="system_language", productId='testwindows')
                    language = language[0]
                    self.assertTrue(set(['de-DE']), language.defaultValues)
                    self.assertTrue(set(['de-DE']), language.possibleValues)


def fillBackend(backend):
    configServer = getConfigServer()
    backend.host_insertObject(configServer)

    product = NetbootProduct(id='testWindows', productVersion=1, packageVersion=1)
    backend.product_insertObject(product)

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
        possibleValues=["NOT YOUR IMAGE", "NO NO NO"],
        defaultValues=["NOT YOUR IMAGE"],
        editable=True,
        multiValue=False
    )
    systemLanguageProductProperty = UnicodeProductProperty(
        productId=product.id,
        productVersion=product.productVersion,
        packageVersion=product.packageVersion,
        propertyId=u"system_language",
        possibleValues=["lol_NOPE"],
        defaultValues=["lol_NOPE", "rofl_MAO"],
        editable=True,
        multiValue=False
    )
    backend.productProperty_insertObject(imagenameProductProperty)
    backend.productProperty_insertObject(systemLanguageProductProperty)


if __name__ == '__main__':
    unittest.main()
