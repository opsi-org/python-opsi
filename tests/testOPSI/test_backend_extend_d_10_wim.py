# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016-2019 uib GmbH <info@uib.de>

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

import pytest

from OPSI.Object import NetbootProduct, ProductOnDepot, UnicodeProductProperty
from .test_hosts import getConfigServer
from .test_util_wim import fakeWimPath  # required fixture
from .helpers import getLocalFQDN, mock, patchAddress, patchEnvironmentVariables


def testUpdatingWim(backendManager, fakeWimPath):
	backend = backendManager
	localFqdn = getLocalFQDN()

	with patchAddress(fqdn=localFqdn):
		with patchEnvironmentVariables(OPSI_HOSTNAME=localFqdn):
			fillBackend(backend)

			with mock.patch('OPSI.Util.WIM.os.path.exists', lambda path: True):
				backend.updateWIMConfig('testwindows')

			imagename = backend.productProperty_getObjects(propertyId="imagename", productId='testwindows')
			imagename = imagename[0]

			possibleImageNames = set([
				u'Windows 7 HOMEBASICN', u'Windows 7 HOMEPREMIUMN',
				u'Windows 7 PROFESSIONALN', u'Windows 7 STARTERN',
				u'Windows 7 ULTIMATEN'
			])
			assert possibleImageNames == set(imagename.possibleValues)
			assert imagename.defaultValues[0] in imagename.possibleValues

			language = backend.productProperty_getObjects(propertyId="system_language", productId='testwindows')
			language = language[0]
			assert ['de-DE'] == language.defaultValues
			assert ['de-DE'] == language.possibleValues


@pytest.mark.parametrize("objectId", ['', None])
def testUpdatingWimFailsWithInvalidObjectId(backendManager, objectId):
	with pytest.raises(ValueError):
		backendManager.updateWIMConfig(objectId)


def testUpdatingWimFailsWithInvalidProductId(backendManager):
	with pytest.raises(OSError):
		backendManager.updateWIMConfigFromPath('', '')


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
