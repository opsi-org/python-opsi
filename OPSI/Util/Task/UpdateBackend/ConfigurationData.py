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
Updating backend data.

This holds backend-independent migrations.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Logger import Logger
from OPSI.System.Posix import isOpenSUSE, isSLES

__all__ = ('updateBackendData', )


LOGGER = Logger()


def updateBackendData(backend):
	setDefaultWorkbenchLocation(backend)


def setDefaultWorkbenchLocation(backend):
	"""
	Set the possibly missing workbench location on the server.

	The value is regarded as missing if it is not set to None.
	`workbenchLocalUrl` will be set to `file:///var/lib/opsi/workbench`
	on SUSE system and to `file:///home/opsiproducts` on others.
	`workbenchRemoteUrl` will use the same value for the depot address
	that is set in `depotRemoteUrl` and then will point to the samba
	share _opsi_workbench_.
	"""
	servers = backend.host_getObjects(type=["OpsiDepotserver", "OpsiConfigserver"])

	if isSLES() or isOpenSUSE():
		# On Suse
		localWorkbenchPath = u'file:///var/lib/opsi/workbench'
	else:
		# On non-SUSE systems the path was usually /home/opsiproducts
		localWorkbenchPath = u'file:///home/opsiproducts'

	changedServers = set()
	for server in servers:
		if server.getWorkbenchLocalUrl() is None:
			LOGGER.notice("Setting missing value for workbenchLocalUrl on {} to {}", server.id, localWorkbenchPath)
			server.setWorkbenchLocalUrl(localWorkbenchPath)
			changedServers.add(server)

		if server.getWorkbenchRemoteUrl() is None:
			depotAddress = getServerAddress(server.depotRemoteUrl)
			remoteWorkbenchPath = u'smb://{}/opsi_workbench'.format(depotAddress)
			LOGGER.notice("Setting missing value for workbenchRemoteUrl on {} to {}", server.id, remoteWorkbenchPath)
			server.setWorkbenchRemoteUrl(remoteWorkbenchPath)
			changedServers.add(server)

	if changedServers:
		backend.host_updateObjects(changedServers)


def getServerAddress(depotRemoteUrl):
	"""
	Get the address of the server from the `depotRemoteUrl`.

	:param depotRemoteUrl: the depotRemoteUrl of an OpsiDepotserver
	:type depotRemoteUrl: str
	:rtype: str
	"""
	_, addressAndPath = depotRemoteUrl.split(':')
	return addressAndPath.split('/')[2]
