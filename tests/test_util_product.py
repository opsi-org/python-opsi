# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2017 uib GmbH <info@uib.de>

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
Testing the OPSI.Util.Product module.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import mock
import os
import re
import tempfile

import OPSI.Util.Product as Product

from .helpers import cd

import pytest


@pytest.mark.parametrize("text", [
	'.svn',
	pytest.mark.xfail('.svnotmatching'),
	'.git',
	pytest.mark.xfail('.gitignore'),
])
def testDirectoryExclusion(text):
	assert re.match(Product.EXCLUDE_DIRS_ON_PACK, text)


def testProductPackageFileRemovingFolderWithUnicodeFilenamesInsideFails(tempDir):
	"""
	As mentioned in http://bugs.python.org/issue3616 the attempt to
	remove a filename that contains unicode can fail.

	Sometimes products are created that feature files with filenames
	that do containt just that.
	We need to make shure that removing such fails does not fail and
	that we are able to remove them.
	"""
	tempPackageFilename = tempfile.NamedTemporaryFile(suffix='.opsi')

	ppf = Product.ProductPackageFile(tempPackageFilename.name)
	ppf.setClientDataDir(tempDir)

	fakeProduct = mock.Mock()
	fakeProduct.getId.return_value = 'umlauts'
	fakePackageControlFile = mock.Mock()
	fakePackageControlFile.getProduct.return_value = fakeProduct

	# Setting up evil file
	targetDir = os.path.join(tempDir, 'umlauts')
	os.makedirs(targetDir)

	with cd(targetDir):
		os.system(r"touch -- $(echo -e '--\0250--')")

	with mock.patch.object(ppf, 'packageControlFile', fakePackageControlFile):
		ppf.deleteProductClientDataDir()

	assert not os.path.exists(targetDir), "Product directory in depot should be deleted."


def testSettigUpProductPackageFileWithNonExistingFileFails():
	with pytest.raises(Exception):
		Product.ProductPackageFile('nonexisting.opsi')


def testCreatingProductPackageSourceRequiresExistingSourceFolder(tempDir):
	targetDir = os.path.join(tempDir, 'nope')

	with pytest.raises(Exception):
		Product.ProductPackageSource(targetDir)
