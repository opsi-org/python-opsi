#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util.Task.Samba

:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3


"""

				#isSamba4 mocken (true/false) check
				# getDistribution mocken (verschiedene Distributionen) check
				# Testteile
				# Shares editieren (wenn da, wie wird damit umgegangen?)
from __future__ import absolute_import
import random
import re
import os
import os.path
import mock
import unittest
import OPSI.Util.Task.Samba as Samba
from collections import defaultdict
from .helpers import workInTemporaryDirectory

class Samba4Test(unittest.TestCase):

	def testNoSmbd(self):

		def fakeWhich(command):
			return None

		def fakeExecute(command):
			return None

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertFalse(Samba.isSamba4())

	def testIsSamba4(self):

		def fakeExecute(command):
			return ['version 4.0.3']

		def fakeWhich(command):
			return command

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertTrue(Samba.isSamba4())

		def fakeExecute(command):
			return ['version ']

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertFalse(Samba.isSamba4())

class SambaConfigureTest(unittest.TestCase):

	def testSambaConfigureSuseSamba4(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				pass

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)
	def testSambaConfigureSuseNoSamba4(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				pass

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:False):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureUbuntuSamba4(self):

		def fakeDistribution():
			return 'Ubuntu 14.04.2 LTS'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				pass
			# Samba4=False
			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:False):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureUbuntuNoSamba4(self):

		def fakeDistribution():
			return 'Ubuntu 14.04.2 LTS'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				pass

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureSamba4Share(self):

		def fakeDistribution():
			return ''

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write('[opt_pcbin] \n [opsi_depot] \n [opsi_depot_rw] \n [opsi_images] \n [opsi_config] \n [opsi_workbench]')

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureNoSamba4Share(self):

		def fakeDistribution():
			return ''

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write('[opt_pcbin] \n [opsi_depot] \n [opsi_depot_rw] \n [opsi_images] \n [opsi_config] \n [opsi_workbench]')

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:False):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureSuseSamba4Share(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write('[opt_pcbin] \n [opsi_depot] \n [opsi_depot_rw] \n [opsi_images] \n [opsi_config] \n [opsi_workbench]')

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testSambaConfigureSuseNoSamba4Share(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write('[opt_pcbin] \n [opsi_depot] \n [opsi_depot_rw] \n [opsi_images] \n [opsi_config] \n [opsi_workbench]')

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:False):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
						Samba.configureSamba(PathToSmbConf)

			filled=False
			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				for line in fakeSambaConfig:
					if line.strip():
						filled = True
						break
			self.assertTrue(filled)

	def testOpsiDepotShareSamba4(self):
		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write(u"[opsi_depot]\n")
				fakeSambaConfig.write(u"   available = yes\n")
				fakeSambaConfig.write(u"   comment = opsi depot share (ro)\n")
				fakeSambaConfig.write(u"   path = /var/lib/opsi/depot\n")
				fakeSambaConfig.write(u"   oplocks = no\n")
				fakeSambaConfig.write(u"   follow symlinks = yes\n")
				fakeSambaConfig.write(u"   level2 oplocks = no\n")
				fakeSambaConfig.write(u"   writeable = no\n")
				fakeSambaConfig.write(u"   invalid users = root\n")

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					Samba.configureSamba(PathToSmbConf)

			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				found = False
				for line in fakeSambaConfig:
					print line
					if line.strip():
						if 'admin users' in line:
							found = True
							break

			self.assertTrue(found, 'Missing Admin Users in Share opsi_depot')

	def testCorrectOpsiDepotShareSamba4(self):
		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write(u"[opsi_depot]\n")
				fakeSambaConfig.write(u"   available = yes\n")
				fakeSambaConfig.write(u"   comment = opsi depot share (ro)\n")
				fakeSambaConfig.write(u"   path = /var/lib/opsi/depot\n")
				fakeSambaConfig.write(u"   oplocks = no\n")
				fakeSambaConfig.write(u"   follow symlinks = yes\n")
				fakeSambaConfig.write(u"   level2 oplocks = no\n")
				fakeSambaConfig.write(u"   writeable = no\n")
				fakeSambaConfig.write(u"   invalid users = root\n")

			with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
				with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
					Samba.configureSamba(PathToSmbConf)

			with open(PathToSmbConf, 'r') as fakeSambaConfig:
				found = False
				opsi_depot = False
				for line in fakeSambaConfig:
					line = line.strip()
					if '[opsi_depot]' in line:
						opsi_depot = True
					elif opsi_depot and 'admin users' in line:
						break
					elif opsi_depot and line.startswith('['):
						opsi_depot = False
				else:
					self.fail('Did not find "admin users" in opsi_depot share')

def main():
	unittest.main()

if __name__ == '__main__':
	main()
