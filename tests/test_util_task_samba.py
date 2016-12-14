#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016 uib GmbH <info@uib.de>

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

from __future__ import absolute_import

import os
import os.path
import mock
import unittest
import OPSI.Util.Task.Samba as Samba
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

	def testIsNotSamba4(self):

		def fakeExecute(command):
			return ['version 3.1']

		def fakeWhich(command):
			return command

		with mock.patch('OPSI.Util.Task.Samba.execute', fakeExecute):
			with mock.patch('OPSI.Util.Task.Samba.which', fakeWhich):
				self.assertFalse(Samba.isSamba4())


class SambaReadConfigTest(unittest.TestCase):

	def testEmptyConfigRead(self):

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w'):
				pass
			result = Samba._readConfig(PathToSmbConf)

		self.assertEqual([], result)

	def testTrueConfigRead(self):

		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				for line in config:
					fakeSambaConfig.write(line)
			result = Samba._readConfig(PathToSmbConf)

		self.assertEqual(config, result)


class SambaProcessConfigTest(unittest.TestCase):

	def testSambaConfigureSuseSamba4(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					newlines = Samba._processConfig([])

		suse = False
		for line in newlines:
			if 'path = /var/lib/opsi/workbench' in line:
					suse = True
					break
		self.assertTrue(suse)

	def testSambaConfigureSuseNoSamba4(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: False):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					newlines = Samba._processConfig([])

		suse = False
		for line in newlines:
			if 'path = /var/lib/opsi/workbench' in line:
					suse = True
					break
		self.assertTrue(suse)

	def testSambaConfigureUbuntuSamba4(self):

		def fakeDistribution():
			return 'Ubuntu 14.04.2 LTS'

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: False):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					result = Samba._processConfig([])

		filled = False
		nonSuse = False
		for line in result:
			if line.strip():
				filled = True
				if '/home/opsiproducts' in line:
					nonSuse = True
					break

		self.assertTrue(filled)
		self.assertTrue(nonSuse)

	def testSambaConfigureUbuntuNoSamba4(self):

		def fakeDistribution():
			return 'Ubuntu 14.04.2 LTS'

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					result = Samba._processConfig([])

		filled = False
		nonSuse = False
		for line in result:
			if line.strip():
				filled = True
				if '/home/opsiproducts' in line:
					nonSuse = True
					break

		self.assertTrue(filled)
		self.assertTrue(nonSuse)

	def testSambaConfigureSamba4Share(self):

		def fakeDistribution():
			return ''

		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					Samba._processConfig(config)

		filled = False
		for line in config:
			if line.strip():
				filled = True
				break
		self.assertTrue(filled)

	def testSambaConfigureNoSamba4Share(self):

		def fakeDistribution():
			return ''

		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: False):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					Samba._processConfig(config)

		filled = False
		for line in config:
			if line.strip():
				filled = True
				break
		self.assertTrue(filled)

	def testSambaConfigureSuseSamba4Share(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					Samba._processConfig(config)

		filled = False
		for line in config:
			if line.strip():
				filled = True
				break
		self.assertTrue(filled)

	def testSambaConfigureSuseNoSamba4Share(self):

		def fakeDistribution():
			return 'suse linux enterprise server'

		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: False):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				with mock.patch('OPSI.Util.Task.Samba.getDistribution', fakeDistribution):
					Samba._processConfig(config)

		filled = False
		for line in config:
			if line.strip():
				filled = True
				break
		self.assertTrue(filled)

	def testOpsiDepotShareSamba4(self):
		config = []
		config.append(u"[opsi_depot]\n")
		config.append(u"   available = yes\n")
		config.append(u"   comment = opsi depot share (ro)\n")
		config.append(u"   path = /var/lib/opsi/depot\n")
		config.append(u"   oplocks = no\n")
		config.append(u"   follow symlinks = yes\n")
		config.append(u"   level2 oplocks = no\n")
		config.append(u"   writeable = no\n")
		config.append(u"   invalid users = root\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				result = Samba._processConfig(config)

		found = False
		for line in result:
			if line.strip():
				if 'admin users' in line:
					found = True
					break

		self.assertTrue(found, 'Missing Admin Users in Share opsi_depot')

	def testCorrectOpsiDepotShareWithoutSamba4Fix(self):
		config = []
		config.append(u"[opsi_depot]\n")
		config.append(u"   available = yes\n")
		config.append(u"   comment = opsi depot share (ro)\n")
		config.append(u"   path = /var/lib/opsi/depot\n")
		config.append(u"   oplocks = no\n")
		config.append(u"   follow symlinks = yes\n")
		config.append(u"   level2 oplocks = no\n")
		config.append(u"   writeable = no\n")
		config.append(u"   invalid users = root\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				result = Samba._processConfig(config)

		opsi_depot = False
		for line in result:
			if line.strip():
				if '[opsi_depot]' in line:
					opsi_depot = True
				elif opsi_depot and 'admin users' in line:
					break
				elif opsi_depot and line.startswith('['):
					opsi_depot = False
				break
		else:
			self.fail('Did not find "admin users" in opsi_depot share')

	def testCorrectOpsiDepotShareWithSamba4Fix(self):
		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"   available = yes\n")
		config.append(u"   comment = opsi depot share (ro)\n")
		config.append(u"   path = /var/lib/opsi/depot\n")
		config.append(u"   oplocks = no\n")
		config.append(u"   follow symlinks = yes\n")
		config.append(u"   level2 oplocks = no\n")
		config.append(u"   writeable = no\n")
		config.append(u"   invalid users = root\n")
		config.append(u"   admin users = @%s\n" % Samba.FILE_ADMIN_GROUP)
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				result = Samba._processConfig(config)

		self.assertEqual(config, result)

	def test_processConfigRemoveComment(self):

		config = []
		config.append(u"; load opsi shares\n")
		config.append(u"include = /etc/samba/share.conf\n")
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				result = Samba._processConfig(config)

		deleted = True
		for line in result:
			if line.strip():
				if '; load opsi shares' in line:
					deleted = False
					break

		else:
			self.assertTrue(deleted)

	def test_processConfigNoRepoShare(self):
		config = []
		config.append(u"; load opsi shares\n")
		config.append(u"include = /etc/samba/share.conf\n")
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")

		with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda: True):
			with mock.patch('OPSI.Util.Task.Samba.os.mkdir'):
				result = Samba._processConfig(config)

		repository = False
		pathFound = False
		for line in result:
			if '[opsi_repository]' in line:
				repository = True
			elif repository:
				if line.strip().startswith('['):
					# next section
					break
				elif line.strip().startswith('path'):
					self.assertTrue('/var/lib/opsi/repository' in line)
					pathFound = True
					break

		self.failIf(not repository, "Missing entry 'opsi_repository'")
		self.failIf(not pathFound, "Missing 'path' in 'opsi_repository'")


class SambaWriteConfig(unittest.TestCase):

	def testEmptyConfigWrite(self):

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w'):
				pass
			Samba._writeConfig([], PathToSmbConf)
			with open(PathToSmbConf, 'r') as readConfig:
				result = readConfig.readlines()

		self.assertEqual([], result)

	def testTrueConfigWrite(self):
		config = []
		config.append(u"[opt_pcbin]\n")
		config.append(u"[opsi_depot]\n")
		config.append(u"[opsi_depot_rw]\n")
		config.append(u"[opsi_images]\n")
		config.append(u"[opsi_workbench]\n")
		config.append(u"[opsi_repository]\n")

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w'):
				pass
			Samba._writeConfig(config, PathToSmbConf)
			with open(PathToSmbConf, 'r') as readConfig:
				result = readConfig.readlines()

		self.assertEqual(config, result)

def main():
	unittest.main()

if __name__ == '__main__':
	main()
