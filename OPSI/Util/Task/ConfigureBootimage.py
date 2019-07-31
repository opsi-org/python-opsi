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
import re

from OPSI.Exceptions import BackendMissingDataError

__all__ = ('patchServiceUrlInDefaultConfigs', )


def patchServiceUrlInDefaultConfigs(backend):
	"""
	Patches the clientconfig.configserver.url into the default.menu/grub.cfg

	:param backend: The backend used to read the configuration
	:type backend: ConfigDataBackend
	"""
	try:
		configServer = backend.config_getObjects(attributes=["defaultValues"], id='clientconfig.configserver.url')[0]
		configServer = configServer.defaultValues[0]
	except IndexError:
		raise BackendMissingDataError("Unable to get clientconfig.configserver.url")

	if configServer:
		defaultMenu, grubMenu = getMenuFiles()
		patchMenuFile(defaultMenu, 'append', configServer)
		patchMenuFile(grubMenu, 'linux', configServer)


def getMenuFiles():
	"""
	Returns the paths for for the default.menu and grub.cfg files.

	:returns: A two-item-tuple with absolute paths to first the \
default.menu and second grub.cfg.
	:rtype: (str, str)
	"""
	if os.path.exists('/tftpboot/linux/pxelinux.cfg/default.menu'):
		defaultMenu = u'/tftpboot/linux/pxelinux.cfg/default.menu'
		grubMenu = u'/tftpboot/grub/grub.cfg'
	else:
		defaultMenu = u'/var/lib/tftpboot/opsi/pxelinux.cfg/default.menu'
		grubMenu = u'/var/lib/tftpboot/grub/grub.cfg'

	return defaultMenu, grubMenu


def patchMenuFile(menufile, searchString, configServer):
	"""
	Patch the address to the `configServer` into `menufile`.

	To find out where to patch we look for lines that starts with the
	given `searchString` (excluding preceding whitespace).

	:param menufile: Path to the file to patch
	:type menufile: str
	:param searchString: Patches only lines starting with this string.
	:type searchString: str
	:param configServer: The address of the OpsiConfigserver to patch \
into the file.
	:type configServer: str
	"""
	newlines = []
	with open(menufile) as readMenu:
		for line in readMenu:
			if line.strip().startswith(searchString):
				if 'service=' in line:
					line = re.sub(r'service=\S+', '', line.rstrip())
				newlines.append('{} service={}\n'.format(line.rstrip(), configServer))
				continue

			newlines.append(line)

	with open(menufile, 'w') as writeMenu:
		writeMenu.writelines(newlines)
