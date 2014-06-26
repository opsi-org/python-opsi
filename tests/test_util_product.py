#! /usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014 uib GmbH <info@uib.de>

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

import mock
import os
import re
import shutil
import tempfile
import unittest

import OPSI.Util.Product as Product
import OPSI.Util.File.Archive as Archive


class DirectoryExclusionRegexTestCase(unittest.TestCase):
	def setUp(self):
		self.regex = re.compile(Product.EXCLUDE_DIRS_ON_PACK)

	def tearDown(self):
		del self.regex

	def testIgnoringSubversionDirectory(self):
		self.assertTrue(self.regex.match('.svn'))
		self.assertFalse(self.regex.match('.svnotmatching'))

	def testIgnoringGitDirectory(self):
		self.assertTrue(self.regex.match('.git'))
		self.assertFalse(self.regex.match('.gitignore'))


class ProductPackageFileTestCase(unittest.TestCase):
	def setUp(self):
		self.tempPackageFilename = tempfile.NamedTemporaryFile(suffix='.opsi')
		# self.tempPackageFilename = self.tempPackageFilename.name
		# self.tempPackage = Archive.Archive(self.tempPackageFilename, format="cpio")

		self.tempDepotDir = tempfile.mkdtemp()

	def tearDown(self):
		packageFile = self.tempPackageFilename.name
		if os.path.exists(packageFile):
			os.remove(packageFile)

		if os.path.exists(self.tempDepotDir):
			shutil.rmtree(self.tempDepotDir)

	def testRemovingFolderWithUnicodeFilenamesInsideFails(self):
		"""
		As mentioned in http://bugs.python.org/issue3616 the attempt to
		remove a filename that contains unicode can fail.

		Sometimes products are created that feature files with filenames
		that do containt just that.
		We need to make shure that removing such fails does not fail and
		that we are able to remove them.
		"""
		ppf = Product.ProductPackageFile(self.tempPackageFilename.name)
		ppf.setClientDataDir(self.tempDepotDir)

		fakeProduct = mock.Mock()
		fakeProduct.getId.return_value = 'umlauts'
		fakePackageControlFile = mock.Mock()
		fakePackageControlFile.getProduct.return_value = fakeProduct


		# Setting up evil file
		targetDir = os.path.join(self.tempDepotDir, 'umlauts')
		print("Target dir: {0}".format(targetDir))
		os.makedirs(os.path.join(self.tempDepotDir, 'umlauts'))
		os.system(r"touch -- $(echo -e '{0}/--\0250--')".format(targetDir))

		with mock.patch.object(ppf, 'packageControlFile', fakePackageControlFile):
			ppf.deleteProductClientDataDir()

		self.assertFalse(
			os.path.exists(targetDir),
			"Product directory in depot should be deleted."
		)

	def testSettigUpWithNonExistingFileFails(self):
		self.assertRaises(Exception, Product.ProductPackageFile, 'nonexisting.opsi')


if __name__ == '__main__':
	unittest.main()
