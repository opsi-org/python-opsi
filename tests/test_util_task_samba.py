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

class SambaTest(unittest.TestCase):

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

	def testSambaConfigureUbuntuNoSamba4Share(self):

		def fakeDistribution():
			return ''

		with workInTemporaryDirectory() as tempDir:
			PathToSmbConf = os.path.join(tempDir, 'SMB_CONF')
			with open(PathToSmbConf, 'w') as fakeSambaConfig:
				fakeSambaConfig.write('[opt_pcbin] \n [opsi_depot] \n [opsi_depot_rw] \n [opsi_images] \n [opsi_config] \n [opsi_workbench]')


			#with mock.patch('OPSI.Util.Task.Samba.isSamba4', lambda:True):
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


def main():
	unittest.main()

if __name__ == '__main__':
	main()
