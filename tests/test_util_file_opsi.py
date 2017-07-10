#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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
Testing OPSI.Util.File.Opsi

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
from __future__ import absolute_import

import os
import unittest

from OPSI.Util import findFiles
from OPSI.Util.File.Opsi import (
	BackendDispatchConfigFile, OpsiConfFile, PackageContentFile,
	PackageControlFile)

from .helpers import workInTemporaryDirectory


class BackendDispatchConfigFileTestCase(unittest.TestCase):
	"""
	Testing reading in the dispatch.conf
	"""

	def testReadingAllUsedBackends(self):
		exampleConfig = '''
backend_.*         : file, mysql, opsipxeconfd, dhcpd
host_.*            : file, mysql, opsipxeconfd, dhcpd
productOnClient_.* : file, mysql, opsipxeconfd
configState_.*     : file, mysql, opsipxeconfd
license.*          : mysql
softwareLicense.*  : mysql
audit.*            : mysql
.*                 : mysql
'''

		dispatchConfig = BackendDispatchConfigFile('not_reading_file')

		self.assertEqual(
			set(('file', 'mysql', 'opsipxeconfd', 'dhcpd')),
			dispatchConfig.getUsedBackends(lines=exampleConfig.split('\n'))
		)

	def testParsingIgnoresCommentedLines(self):
		exampleConfig = '''
;backend_.*.*  : fail
	#audit.*            : fail
		.*                 : yolofile
'''

		dispatchConfig = BackendDispatchConfigFile('not_reading_file')
		usedBackends = dispatchConfig.getUsedBackends(lines=exampleConfig.split('\n'))

		self.assertTrue('fail' not in usedBackends)
		self.assertEqual(
			set(('yolofile',)),
			usedBackends
		)

	def testNotFailingOnInvalidLines(self):
		"""
		Reading invalid lines in a config must not lead to an exception.
		"""
		exampleConfig = '''
this does not work
'''

		dispatchConfig = BackendDispatchConfigFile('not_reading_file')
		dispatchConfig.parse(lines=exampleConfig.split('\n'))

	def testBackendsCanBeEmpty(self):
		exampleConfig = '''
no_backends_follow:\t
empty_backends:\t, ,
'''

		dispatchConfig = BackendDispatchConfigFile('not_reading_file')
		result = dispatchConfig.parse(lines=exampleConfig.split('\n'))

		self.assertEquals(1, len(result))
		regex, backends = result[0]
		self.assertEquals('empty_backends', regex)
		self.assertEquals([u''], backends)


class OpsiConfigFileTestCase(unittest.TestCase):
	"""
	Testing functions for /etc/opsi.conf
	"""

	EXAMPLE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'file', 'opsi', 'opsi.conf')

	def setUp(self):
		self.config = OpsiConfFile(filename=self.EXAMPLE_CONFIG_FILE)

	def tearDown(self):
		del self.config

	def testReadingFileAdminGroupReturnsLowercaseName(self):
		self.assertEquals('mypcpatch', self.config.getOpsiFileAdminGroup())

	def testReturningDefaultForFileAdminGroup(self):
		self.config.parse([''])
		self.assertEquals('pcpatch', self.config.getOpsiFileAdminGroup())

	def testReadingReadonlyGroups(self):
		self.assertEquals(['myopsireadonlys'], self.config.getOpsiGroups("readonly"))

	def testGettingDefaultForReadonlyGroups(self):
		self.config.parse([''])
		self.assertEquals(None, self.config.getOpsiGroups("readonly"))

	def testReadingPigzStatus(self):
		self.assertEquals(False, self.config.isPigzEnabled())

	def testGettingDefaultPigzStatus(self):
		self.config.parse([''])
		self.assertEquals(True, self.config.isPigzEnabled())


class OpsiControlFileTestCase(unittest.TestCase):

	# The file is the one that was causing a problem in
	# https://forum.opsi.org/viewtopic.php?f=7&t=7907
	EXAMPLE_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
		'testdata', 'util', 'file', 'opsi', 'control_with_german_umlauts')

	def testParsingControlFileWithGermanUmlautsInDescription(self):
		p = PackageControlFile(self.EXAMPLE_CONFIG_FILE)
		p.parse()

		product = p.getProduct()
		self.assertEquals(
			u'Startet die Druckerwarteschlange auf dem Client neu / oder überhaupt.',
			product.description
		)


def testPackageControlFileCreation():
	with workInTemporaryDirectory() as tempDir:
		fillDirectory(tempDir)
		clientDataFiles = findFiles(tempDir)

		filename = os.path.join(tempDir, 'test.files')
		contentFile = PackageContentFile(filename)
		contentFile.setProductClientDataDir(tempDir)
		contentFile.setClientDataFiles(clientDataFiles)
		contentFile.generate()

		assert os.path.exists(filename)
		assert os.path.getsize(filename) > 10


def fillDirectory(directory):
	assert os.path.exists(directory)

	with open(os.path.join(directory, 'simplefile'), 'w') as fileHandle:
		fileHandle.write('I am an very simple file\nFor real!')

	subDir = os.path.join(directory, 'subdir')
	os.mkdir(subDir)

	with open(os.path.join(subDir, 'fileinsub1'), 'w') as fileHandle:
		fileHandle.write('Subby one')

	with open(os.path.join(subDir, 'fileinsub2'), 'w') as fileHandle:
		fileHandle.write('Subby two')

	subSubDir = os.path.join(subDir, 'sub1')
	os.mkdir(subSubDir)

	with open(os.path.join(subSubDir, 'simplefile'), 'w') as fileHandle:
		fileHandle.write('Sub in a sub.\nThanks, no cheese!')
