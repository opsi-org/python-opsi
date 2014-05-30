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
Testing OPSI.Util.File.Opsi

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
from __future__ import absolute_import

import os
import unittest

from OPSI.Util.File.Opsi import BackendDispatchConfigFile, OpsiConfFile



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


class OpsiConfigFileTestCase(unittest.TestCase):
	EXAMPLE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'file', 'opsi', 'opsi.conf')
	"""
	Testing functions for /etc/opsi.conf
	"""
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

