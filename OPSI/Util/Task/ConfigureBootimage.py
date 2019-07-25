# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2017-2019 uib GmbH - http://www.uib.de/

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
This writes the opsi configserver URL into the default.menu file

:copyright: uib GmbH <info@uib.de>
:author: Mathias Radtke <m.radtke@uib.de>
:license: GNU Affero General Public License version 3
"""
import os

from OPSI.Backend.Backend import temporaryBackendOptions


def patchConfigserserverurlInDefaultMenu(backend):
	"""
	Patches the clientconfig.configserver.url into the default.menu"
	"""

	from OPSI.Backend.BackendManager import BackendManager
	with BackendManager() as backend:
		with temporaryBackendOptions(backend, addConfigStateDefaults=True):
			try:
				configServer = backend.config_getObjects(attributes=["defaultValues"], id='clientconfig.configserver.url')[0]
				configServer = configServer.defaultValues[0]
			except IndexError:
				raise BackendMissingDataError("Unable to get clientconfig.configserver.url")
			if configServer:
				if os.path.exists('/tftpboot/linux/pxelinux.cfg/default.menu'):
					defaultMenu = '/tftpboot/linux/pxelinux.cfg/default.menu'
				else:
					defaultMenu = '/var/lib/tftpboot/opsi/pxelinux.cfg/default.menu'
				with open(defaultMenu, 'r+') as readMenu:
					newlines=[]
					for line in readMenu:
						if line.strip().startswith('append'):
							newlines.append('{} service={}\n'.format(line.strip(), configServer.rstrip()))
						newLines.append(line)

				with open(defaultMenu, 'w') as writeMenu:
					writeMenu.write(newLines)

				if os.path.exists('/tftpboot/grub/grub.cfg'):
					grubMenu = '/tftpboot/grub/grub.cfg'
				else:
					grubmenu = '/var/lib/tftpboot/grub/grub.cfg'
				with open(grubMenu) as readMenu:
					newlines=[]
					for line in readMenu:
						if line.strip().startswith('linux'):
							newlines.append('{} service={}\n'.format(line.rstrip(), configServer.rstrip()))
						newlines.append(line)

				with open(grubMenu, 'w') as writeMenu:
					writemenu.write(newlines)
