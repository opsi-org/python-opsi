#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.System

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import shutil
import tempfile
import unittest

from OPSI.System import copy
from OPSI.Util.Message import ProgressSubject


class CopyFilesTestCase(unittest.TestCase):
	EXAMPLE_FILENAMES = ('file1', 'file2', 'file3')
	EXAMPLE_DIRECTORIES = ('dir1', 'dir2', 'dir3')

	def setUp(self):
		self.testDir = tempfile.mkdtemp()

		self.srcDir = os.path.join(self.testDir, 'src')
		self.dstDir = os.path.join(self.testDir, 'dst')
		os.makedirs(self.srcDir)
		os.makedirs(self.dstDir)

		self.progressSubject = ProgressSubject(id=u'copy_test', title=u'Copy test')

	def tearDown(self):
		if os.path.exists(self.testDir):
			shutil.rmtree(self.testDir)

		del self.progressSubject
		del self.srcDir
		del self.dstDir
		del self.testDir

	def _fillDirectoryWithFilesAndFolders(self):
		fileContent = 'x'*10*1024

		for filename in self.EXAMPLE_FILENAMES:
			pathToFile = os.path.join(self.srcDir, filename)
			with open(pathToFile, 'w') as outputFile:
				outputFile.write(fileContent)

		for dirname in self.EXAMPLE_DIRECTORIES:
			pathToDir = os.path.join(self.srcDir, dirname)
			os.mkdir(pathToDir)

			for filename in self.EXAMPLE_FILENAMES:
				pathToFile = os.path.join(pathToDir, filename)
				with open(pathToFile, 'w') as outputFile:
					outputFile.write(fileContent)

	def _makeSureFilesAndFoldersExistAtDestination(self):
		for filename in self.EXAMPLE_FILENAMES:
			pathToFile = os.path.join(self.dstDir, os.path.basename(self.srcDir), filename)
			self.assertTrue(os.path.isfile(pathToFile))

		for dirname in self.EXAMPLE_DIRECTORIES:
			pathToDir = os.path.join(self.dstDir, os.path.basename(self.srcDir), dirname)
			self.assertTrue(os.path.isdir(pathToDir))

			for filename in self.EXAMPLE_FILENAMES:
				pathToFile = os.path.join(pathToDir, filename)
				self.assertTrue(os.path.isfile(pathToFile))

	def _makeSureFilesAndFoldersExistAtDestinationWithoutLongPath(self):
		"""
		Checking method for files and folders that does nut include the basename
		of the source directory.
		"""
		for filename in self.EXAMPLE_FILENAMES:
			a = os.path.join(self.dstDir, filename)
			self.assertTrue(os.path.isfile(a))

		for dirname in self.EXAMPLE_DIRECTORIES:
			a = os.path.join(self.dstDir, dirname)
			self.assertTrue(os.path.isdir(a))

			for filename in self.EXAMPLE_FILENAMES:
				a2 = os.path.join(a, filename)
				self.assertTrue(os.path.isfile(a2))

	def testCopyingFromFileToFileOverwritesDestination(self):
		srcfile = os.path.join(self.srcDir, 'testfile')
		with open(srcfile, 'w') as f:
			f.write('new')

		dstfile = os.path.join(self.dstDir, 'testfile')
		with open(dstfile, 'w') as f:
			f.write('old')

		copy(srcfile, dstfile, self.progressSubject)

		with open(dstfile) as f:
			data = f.read()

		self.assertEquals('new', data)

	def testCopyingFromFileToDirectory(self):
		# src = file,  dst = dir            => copy into dst
		srcfile = os.path.join(self.srcDir, 'testfile')
		dstfile = os.path.join(self.dstDir, 'testfile2')

		with open(srcfile, 'w') as f:
			f.write('new')

		copy(srcfile, dstfile, self.progressSubject)

		with open(dstfile) as f:
			data = f.read()

		self.assertEquals('new', data)

	def testCopyingFromFileToNonExistingDestination(self):
		# src = file,  dst = not existent   => create dst directories, copy src to dst
		srcfile = os.path.join(self.srcDir, 'testfile')
		dstfile = os.path.join(self.dstDir, 'newdir', 'testfile')

		with open(srcfile, 'w') as f:
			f.write('new')

		copy(srcfile, dstfile, self.progressSubject)

		with open(dstfile) as f:
			data = f.read()

		self.assertEquals('new', data)

	def testCopyingFromDirectoryToFileRaisesException(self):
		# src = dir,   dst = file           => error
		testSrcDir = os.path.join(self.srcDir, 'testdir')
		os.makedirs(testSrcDir)

		testDstDir = os.path.join(self.dstDir, 'testdir')
		with open(testDstDir, 'w'):
			pass

		self.assertRaises(OSError, copy, testSrcDir, testDstDir, self.progressSubject)

	def testCopyingFromDirectoryToDirectoryCopiesContent(self):
		#src = dir,   dst = dir            => copy src dir into dst
		self._fillDirectoryWithFilesAndFolders()
		copy(self.srcDir, self.dstDir, self.progressSubject)
		self._makeSureFilesAndFoldersExistAtDestination()

		copy(self.srcDir, self.dstDir, self.progressSubject)

		for name in os.listdir(os.path.join(self.dstDir, os.path.basename(self.srcDir))):
			self.assertTrue(name in self.EXAMPLE_DIRECTORIES + self.EXAMPLE_FILENAMES)

		for dirname in self.EXAMPLE_DIRECTORIES:
			a = os.path.join(self.dstDir, os.path.basename(self.srcDir), dirname)
			for name in os.listdir(a):
				self.assertTrue(name in self.EXAMPLE_FILENAMES)

	def testCopyingFromDirectoryToNonExistingCreatesFolderAndCopiesContent(self):
		# src = dir,   dst = not existent   => create dst, copy content of src into dst
		self._fillDirectoryWithFilesAndFolders()

		shutil.rmtree(self.dstDir)
		copy(self.srcDir, self.dstDir, self.progressSubject)

		self._makeSureFilesAndFoldersExistAtDestinationWithoutLongPath()

	def testCopyingManyFilesIntoNonFileDestination(self):
		# src = dir/*, dst = not file       => create dst if not exists, copy content of src into dst
		self._fillDirectoryWithFilesAndFolders()

		copy(self.srcDir + '/*.*', self.dstDir, self.progressSubject)

		self._makeSureFilesAndFoldersExistAtDestinationWithoutLongPath()

	def testCopyingFilesWithWildcardPattern(self):
		self._fillDirectoryWithFilesAndFolders()

		copy(self.srcDir + '/*', self.dstDir, self.progressSubject)

		self._makeSureFilesAndFoldersExistAtDestinationWithoutLongPath()

	def testCopyingFilesWithWildcardPatternIncludingDot(self):
		self._fillDirectoryWithFilesAndFolders()

		copy(self.srcDir + '/*.*', self.dstDir, self.progressSubject)

		self._makeSureFilesAndFoldersExistAtDestinationWithoutLongPath()


class CopyFilesWithoutProgressSubjectTestCase(CopyFilesTestCase):
	"""
	Repeating the tests from CopyFilesTestCase without a progressSubject.
	"""
	def setUp(self):
		super(CopyFilesWithoutProgressSubjectTestCase, self).setUp()

		self.progressSubject = None


if __name__ == '__main__':
	unittest.main()
