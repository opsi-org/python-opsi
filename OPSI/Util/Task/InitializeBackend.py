# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2017 uib GmbH - http://www.uib.de/

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
First backend initialization.

This is the first-time setup of an opsi server instance.
To work propery an initial configuration needs to take place.

This holds backend-independent migrations.

:copyright: uib GmbH <info@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import os.path
from OPSI.Logger import Logger
from OPSI.Object import OpsiConfigserver
from OPSI.System.Posix import getLocalFqdn, getNetworkConfiguration
from OPSI.Types import forceList
from OPSI.Util.Task.ConfigureBackend.ConfigurationData import initializeConfigs
from OPSI.Util.Task.Rights import setPasswdRights

LOGGER = Logger()


def initializeBackends(ipAddress=None):
	"""
	Initial backend setup based on the current configuration.

	This will create required folders aswell as set up the current
	backend for use with opsi.

	:param ipAddress: Force the function to work with the given IP address.
	:type ipAddress: str
	"""
	_setupPasswdFile()

	from OPSI.Backend.BackendManager import BackendManager
	backend = BackendManager(
		dispatchConfigFile=u'/etc/opsi/backendManager/dispatch.conf',
		backendConfigDir=u'/etc/opsi/backends',
		extensionConfigDir=u'/etc/opsi/backendManager/extend.d',
		depotbackend=False
	)
	backend.backend_createBase()

	networkConfig = getNetworkConfiguration(ipAddress)
	fqdn = getLocalFqdn()

	LOGGER.notice(u"Try to find a Configserver.")
	configServer = backend.host_getObjects(type='OpsiConfigserver')
	if not configServer and not backend.host_getIdents(type='OpsiConfigserver', id=fqdn):
		depot = backend.host_getObjects(type='OpsiDepotserver', id=fqdn)
		if not depot:
			LOGGER.notice(u"Creating config server '%s'" % fqdn)
			serverConfig = _getServerConfig(fqdn, networkConfig)
			backend.host_createOpsiConfigserver(**serverConfig)
			configServer = backend.host_getObjects(type='OpsiConfigserver', id=fqdn)
		else:
			LOGGER.notice(u"Converting depot server '%s' to config server" % fqdn)
			configServer = OpsiConfigserver.fromHash(depot[0].toHash())
			backend.host_createObjects(configServer)

			# list expected in further processing
			configServer = [configServer]
	else:
		depot = backend.host_getObjects(type='OpsiDepotserver', id=fqdn)
		if not depot:
			LOGGER.notice(u"Creating depot server '%s'" % fqdn)
			serverConfig = _getServerConfig(fqdn, networkConfig)
			backend.host_createOpsiDepotserver(**serverConfig)

	if configServer:
		if configServer[0].id == fqdn:
			configServer = backend.host_getObjects(type='OpsiConfigserver')
			if not configServer:
				raise Exception(u"Config server '%s' not found" % fqdn)
			configServer = configServer[0]
			if networkConfig['ipAddress']:
				configServer.setIpAddress(networkConfig['ipAddress'])
			if networkConfig['hardwareAddress']:
				configServer.setHardwareAddress(networkConfig['hardwareAddress'])

			# make sure the config server is present in all backends or we get reference error later on
			backend.host_insertObject(configServer)

		# initializeConfigs does only handle a single object
		configServer = forceList(configServer)[0]

	initializeConfigs(backend=backend, configServer=configServer)
	backend.backend_exit()

	_setupDepotDirectory()
	_setupWorkbenchDirectory()


def _setupPasswdFile():
	"""
	Set up the opsi passwd file and set the correct rights.
	"""
	if not os.path.exists(u'/etc/opsi/passwd'):
		with codecs.open(u'/etc/opsi/passwd', 'w', 'utf-8'):
			pass

		setPasswdRights()


def _getServerConfig(fqdn, networkConfig):
	"""
	Prepare the configuration of the local server.

	:param networkConfig: Network configuration for the local host.
	:type networkConfig: dict
	:rtype: dict
	"""
	hostname = fqdn.split(u'.')[0]

	config = dict(
		id=fqdn,
		opsiHostKey=None,
		depotLocalUrl=u'file:///var/lib/opsi/depot',
		depotRemoteUrl=u'smb://%s/opsi_depot' % hostname,
		depotWebdavUrl=u'webdavs://%s:4447/depot' % fqdn,
		repositoryLocalUrl=u'file:///var/lib/opsi/repository',
		repositoryRemoteUrl=u'webdavs://%s:4447/repository' % fqdn,
		workbenchLocalUrl=u'file:///var/lib/opsi/workbench',
		workbenchRemoteUrl=u'smb://{}/opsi_workbench'.format(hostname),
		description=None,
		notes=None,
		hardwareAddress=networkConfig['hardwareAddress'],
		ipAddress=networkConfig['ipAddress'],
		inventoryNumber=None,
		networkAddress=u'{subnet}/{netmask}'.format(**networkConfig),
		maxBandwidth=0,
		isMasterDepot=True,
		masterDepotId=None,
	)

	LOGGER.debug("Server configuration is: {0!r}", config)
	return config


def _setupDepotDirectory():
	"""
	Set up the directory for the depot.
	"""
	depotDir = '/var/lib/opsi/depot'
	try:
		os.mkdir(depotDir)
	except OSError as error:
		if error.errno != 17:  # 17 is File exists
			LOGGER.warning(u"Failed to create depot directory '{0}': {1}", depotDir, error)

	if os.path.exists("/opt/pcbin/install"):
		LOGGER.warning(
			u"You have an old depot directory present. "
			u"Using /opt/pcbin/install is depracted, "
			u"please use /var/lib/opsi/depot instead."
		)


def _setupWorkbenchDirectory():
	"""
	Set up the directory for the workbench in case it is missing.

	The path is `/var/lib/opsi/workbench`.
	"""
	try:
		os.mkdir('/var/lib/opsi/workbench')
	except OSError as error:
		if error.errno != 17:  # 17 is File exists
			LOGGER.warning("Failed to create workbench directory: {0}", error)
