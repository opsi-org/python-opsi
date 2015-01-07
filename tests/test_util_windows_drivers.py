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
Testing WindowsDrivers.

:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import shutil
import tempfile
import unittest

from OPSI.Util.WindowsDrivers import integrateAdditionalWindowsDrivers
from OPSI.Object import AuditHardwareOnHost 

class WindowsDriversTestCase(unittest.TestCase):
	
	def _generateAuditHardwareOnHost(self, hardwareClass, hostId, vendor, model):
		auditHardwareOnHost = AuditHardwareOnHost(
			hardwareClass, hostId)
		auditHardwareOnHost.vendor = vendor
		auditHardwareOnHost.model = model
		
		return auditHardwareOnHost
		
	def _generateDirectories(self, vendor, model):
		rulesDir = os.path.join(self.temporary_folder, "byAudit")
		if not os.path.exists(rulesDir):
			os.mkdir(rulesDir)
		vendorDir = os.path.join(rulesDir, vendor)
		modelDir = os.path.join(vendorDir, model)
		
		os.mkdir(vendorDir)
		os.mkdir(modelDir)
	
	def _generateTestFiles(self, vendor, model, filename):
		dstFilename = os.path.join(self.temporary_folder, "byAudit", vendor, model, filename)
		with open(dstFilename, "w"):
			pass
			
		
		
	def setUp(self):
		self.temporary_folder = tempfile.mkdtemp()
		self.destinationDir = os.path.join(self.temporary_folder, "destination")
		
	def tearDown(self):
		if os.path.exists(self.temporary_folder):
			pass
			#shutil.rmtree(self.temporary_folder)
		
	def testByAudit(self):
		
		hardwareClass, hostId, vendor, model = ("COMPUTER_SYSTEM", "test.domain.local", "Dell Inc.", "Venue 11 Pro 7130 MS")

		testData1 = self._generateAuditHardwareOnHost(hardwareClass, hostId, vendor, model)
		self._generateDirectories(vendor, model)
		self._generateTestFiles(vendor, model, "test.inf")
				
		result = integrateAdditionalWindowsDrivers(self.temporary_folder, self.destinationDir, [], auditHardwareOnHosts = [ testData1 ])
		
		expectedResult = [
				{'devices': [],
				'directory': u'%s/1' % self.destinationDir,
				'driverNumber': 1,
				'infFile': u'%s/1/test.inf' % self.destinationDir}]
				
		self.assertEquals(expectedResult, result)
		
		
	def testByAuditWithUnderscoreAtTheEnd(self):
		hardwareClass, hostId, vendor, model = ("COMPUTER_SYSTEM", "test.domain.local", "Dell Inc_", "Venue 11 Pro 7130 MS")

		testData1 = self._generateAuditHardwareOnHost(hardwareClass, hostId, "Dell Inc.", model)
		self._generateDirectories(vendor, model)
		self._generateTestFiles(vendor, model, "test.inf")
				
		result = integrateAdditionalWindowsDrivers(self.temporary_folder, self.destinationDir, [], auditHardwareOnHosts = [ testData1 ])
		
		expectedResult = [
				{'devices': [],
				'directory': u'%s/1' % self.destinationDir,
				'driverNumber': 1,
				'infFile': u'%s/1/test.inf' % self.destinationDir}]
				
		self.assertEquals(expectedResult, result)
		
		
		
		
		
		
	
	
	
		
		
		
		
		
		
"""
auditHardwareOnHosts


byAudit OK
Additional
byAuditFallback - Mainboard
Statt Dell Inc. -> Dell Inc_
"""
