# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util.Task.ConfigureBootimage

:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import os.path

import pytest

import OPSI.Util.Task.ConfigureBootimage as ConfigureBootimage
from OPSI.Exceptions import BackendMissingDataError
from OPSI.Object import UnicodeConfig

from .helpers import mock


@pytest.mark.parametrize('fileExists, expectedDefaultMenu, expectedGrubMenu', [
	[True, u'/tftpboot/linux/pxelinux.cfg/default.menu', u'/tftpboot/grub/grub.cfg'],
	[False, u'/var/lib/tftpboot/opsi/pxelinux.cfg/default.menu', u'/var/lib/tftpboot/grub/grub.cfg'],
])
def testMenuFiles(fileExists, expectedDefaultMenu, expectedGrubMenu):
	with mock.patch('os.path.exists', lambda x: fileExists):
		defaultMenu, grubMenu = ConfigureBootimage.getMenuFiles()
		assert defaultMenu == expectedDefaultMenu
		assert grubMenu == expectedGrubMenu


def testPatchMenuFile(tempDir):
	filename = os.path.join(tempDir, 'default.menu')
	with open(filename, 'w') as writefile:
		writefile.write('label install\n')
		writefile.write('  menu label Start ^opsi bootimage\n')
		writefile.write('  text help\n')
		writefile.write('				 Start opsi linux bootimage from tftp server.\n')
		writefile.write('  endtext\n')
		writefile.write('  kernel install\n')
		writefile.write('  append initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0\n')
		writefile.write('\n')

	configServer = u'https://192.168.1.14:4447/rpc'
	ConfigureBootimage.patchMenuFile(filename, 'append', configServer)

	expectedDefault = [
		'label install\n',
		'  menu label Start ^opsi bootimage\n',
		'  text help\n',
		'				 Start opsi linux bootimage from tftp server.\n',
		'  endtext\n',
		'  kernel install\n',
		'  append initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0 service=https://192.168.1.14:4447/rpc\n',
		'\n'
	]

	with open(filename) as patchedFile:
		patchedDefault = patchedFile.readlines()

	assert patchedDefault == expectedDefault


def testPatchMenuFileReplacesExistingServiceConfiguration(tempDir):
	filename = os.path.join(tempDir, 'default.menu')
	with open(filename, 'w') as writefile:
		writefile.write('label install\n')
		writefile.write('  menu label Start ^opsi bootimage\n')
		writefile.write('  text help\n')
		writefile.write('				 Start opsi linux bootimage from tftp server.\n')
		writefile.write('  endtext\n')
		writefile.write('  kernel install\n')
		writefile.write('  append initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0 service=https://192.159.2.2/rpc\n')
		writefile.write('\n')

	configServer = u'https://192.168.1.14:4447/rpc'
	ConfigureBootimage.patchMenuFile(filename, 'append', configServer)

	expectedDefault = [
		'label install\n',
		'  menu label Start ^opsi bootimage\n',
		'  text help\n',
		'				 Start opsi linux bootimage from tftp server.\n',
		'  endtext\n',
		'  kernel install\n',
		'  append initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0 service=https://192.168.1.14:4447/rpc\n',
		'\n'
	]

	with open(filename) as patchedFile:
		patchedDefault = patchedFile.readlines()

	assert patchedDefault == expectedDefault


def testPatchServiceUrlInDefaultConfigs(backendManager, tempDir):
	testIp = '192.168.1.14'

	clientconfigConfigserverUrl = UnicodeConfig(
		id=u'clientconfig.configserver.url',
		possibleValues=[],
		defaultValues=[testIp]
	)
	backendManager.config_insertObject(clientconfigConfigserverUrl)

	def getTestMenuFiles():
		menu = os.path.join(tempDir, 'test.menu')
		grub = os.path.join(tempDir, 'test.grub')
		return menu, grub

	with mock.patch('OPSI.Util.Task.ConfigureBootimage.getMenuFiles', getTestMenuFiles):
		defaultMenu, grubMenu = ConfigureBootimage.getMenuFiles()

		with open(defaultMenu, 'w') as defaultWrite:
			defaultWrite.write('  kernel install\n')
			defaultWrite.write('  append initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0\n')
			defaultWrite.write('\n')

		with open(grubMenu, 'w') as grubWrite:
			grubWrite.write('		set gfxpayload=keep\n')
			grubWrite.write('		linux (pxe)/linux/install initrd=miniroot.bz2 video=vesa:ywrap,mtrr vga=791 quiet splash --no-log console=tty1 console=ttyS0\n')
			grubWrite.write('\n')

		ConfigureBootimage.patchServiceUrlInDefaultConfigs(backendManager)

		expectedServiceConfig = 'service=%s' % testIp
		with open(defaultMenu) as defaultReader:
			for line in defaultReader:
				if line.lstrip().startswith('append'):
					assert expectedServiceConfig in line
					break
			else:
				raise RuntimeError("default.menu not patched")

		with open(grubMenu) as grubReader:
			for line in grubReader:
				if line.lstrip().startswith('linux'):
					assert expectedServiceConfig in line
					break
			else:
				raise RuntimeError("default.menu not patched")


def testPatchServiceUrlInDefaultConfigsFailsIfUnconfigured(backendManager):
	with pytest.raises(BackendMissingDataError):
		ConfigureBootimage.patchServiceUrlInDefaultConfigs(backendManager)
