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
import socket
from OPSI.Logger import Logger
from OPSI.Object import OpsiConfigserver
from OPSI.System.Posix import getEthernetDevices, getNetworkDeviceConfig
from OPSI.Types import forceList, forceHostId
from OPSI.Util import getfqdn
from OPSI.Util.Task.ConfigureBackend.ConfigurationData import initializeConfigs
from OPSI.Util.Task.Rights import setPasswdRights

OPSI_GLOBAL_CONF = u'/etc/opsi/global.conf'


logger = Logger()


def initializeBackends():
	if not os.path.exists(u'/etc/opsi/passwd'):
		with codecs.open(u'/etc/opsi/passwd', 'w', 'utf-8'):
			pass
		setPasswdRights()

	from OPSI.Backend.BackendManager import BackendManager
	backend = BackendManager(
		dispatchConfigFile=u'/etc/opsi/backendManager/dispatch.conf',
		backendConfigDir=u'/etc/opsi/backends',
		extensionConfigDir=u'/etc/opsi/backendManager/extend.d',
		depotbackend=False
	)
	backend.backend_createBase()

	sysConfig = getSysConfig()
	fqdn = sysConfig['fqdn']

	logger.notice(u"Try to find a Configserver.")
	configServer = backend.host_getObjects(type='OpsiConfigserver')
	if not configServer and not backend.host_getIdents(type='OpsiConfigserver', id=fqdn):
		depot = backend.host_getObjects(type='OpsiDepotserver', id=fqdn)
		if not depot:
			logger.notice(u"Creating config server '%s'" % fqdn)
			depotRemoteUrl = u'smb://%s/opsi_depot' % sysConfig['hostname']

			backend.host_createOpsiConfigserver(
				id=fqdn,
				opsiHostKey=None,
				depotLocalUrl=u'file:///var/lib/opsi/depot',
				depotRemoteUrl=depotRemoteUrl,
				depotWebdavUrl=u'webdavs://%s:4447/depot' % fqdn,
				# TODO: ip here?
				repositoryLocalUrl=u'file:///var/lib/opsi/repository',
				repositoryRemoteUrl=u'webdavs://%s:4447/repository' % fqdn,
				description=None,
				notes=None,
				hardwareAddress=sysConfig['hardwareAddress'],
				ipAddress=sysConfig['ipAddress'],
				inventoryNumber=None,
				networkAddress=u'%s/%s' % (sysConfig['subnet'], sysConfig['netmask']),
				maxBandwidth=0,
				isMasterDepot=True,
				masterDepotId=None,
				# TODO: add workbench here
			)
			configServer = backend.host_getObjects(type='OpsiConfigserver', id=fqdn)
		else:
			logger.notice(u"Converting depot server '%s' to config server" % fqdn)
			configServer = OpsiConfigserver.fromHash(depot[0].toHash())
			backend.host_createObjects(configServer)

			# list expected in further processing
			configServer = [configServer]
	else:
		depot = backend.host_getObjects(type='OpsiDepotserver', id=fqdn)
		if not depot:
			logger.notice(u"Creating depot server '%s'" % fqdn)
			depotRemoteUrl = u'smb://%s/opsi_depot' % sysConfig['hostname']  # TODO: ip?

			backend.host_createOpsiDepotserver(
				id=fqdn,
				opsiHostKey=None,
				depotLocalUrl=u'file:///var/lib/opsi/depot',
				depotRemoteUrl=depotRemoteUrl,
				depotWebdavUrl=u'webdavs://%s:4447/depot' % fqdn,
				repositoryLocalUrl=u'file:///var/lib/opsi/repository',
				repositoryRemoteUrl=u'webdavs://%s:4447/repository' % fqdn,
				description=None,
				notes=None,
				hardwareAddress=sysConfig['hardwareAddress'],
				ipAddress=sysConfig['ipAddress'],
				inventoryNumber=None,
				networkAddress=u'%s/%s' % (sysConfig['subnet'], sysConfig['netmask']),
				maxBandwidth=0,
				isMasterDepot=True,
				masterDepotId=None,
			)

	if configServer:
		if configServer[0].id == fqdn:
			configServer = backend.host_getObjects(type='OpsiConfigserver')
			if not configServer:
				raise Exception(u"Config server '%s' not found" % fqdn)
			configServer = configServer[0]
			if sysConfig['ipAddress']:
				configServer.setIpAddress(sysConfig['ipAddress'])
			if sysConfig['hardwareAddress']:
				configServer.setHardwareAddress(sysConfig['hardwareAddress'])

			# make sure the config server is present in all backends or we get reference error later on
			backend.host_insertObject(configServer)

		# initializeConfigs does only handle a single object
		configServer = forceList(configServer)[0]

	initializeConfigs(backend=backend, configServer=configServer)
	backend.backend_exit()

	depotDir = '/var/lib/opsi/depot'
	if not os.path.exists(depotDir):
		try:
			os.mkdir(depotDir)
			if os.path.exists("/opt/pcbin/install"):
				logger.warning(u"You have an old depot configuration. Using /opt/pcbin/install is depracted, please use /var/lib/opsi/depot instead.")
		except Exception as error:
			logger.warning(u"Failed to create depot directory '%s': %s" % (depotDir, error))

	# TODO: create workbench directory


def getSysConfig(ipAddress=None):
	sysConfig = {}

	logger.notice(u"Getting current system config")
	if ipAddress:
		sysConfig['ipAddress'] = ipAddress

	try:
		sysConfig['fqdn'] = forceHostId(getfqdn(conf=OPSI_GLOBAL_CONF))
	except:
		raise Exception(u"Failed to get fully qualified domain name, got '%s'" % getfqdn(conf=OPSI_GLOBAL_CONF))

	sysConfig['hostname'] = sysConfig['fqdn'].split(u'.')[0]
	if 'ipAddress' not in sysConfig:
		sysConfig['ipAddress'] = socket.gethostbyname(sysConfig['fqdn'])
		if sysConfig['ipAddress'].split(u'.')[0] in ('127', '169'):
			sysConfig['ipAddress'] = None
	sysConfig['hardwareAddress'] = None

	for device in getEthernetDevices():
		devconf = getNetworkDeviceConfig(device)
		if devconf['ipAddress'] and devconf['ipAddress'].split(u'.')[0] not in ('127', '169'):
			if not sysConfig['ipAddress']:
				sysConfig['ipAddress'] = devconf['ipAddress']
			if (sysConfig['ipAddress'] == devconf['ipAddress']):
				sysConfig['netmask'] = devconf['netmask']
				sysConfig['hardwareAddress'] = devconf['hardwareAddress']
				break

	if not sysConfig['ipAddress']:
		raise Exception(u"Failed to get a valid ip address for fqdn '%s'" % sysConfig['fqdn'])

	if not sysConfig.get('netmask'):
		sysConfig['netmask'] = u'255.255.255.0'

	sysConfig['broadcast'] = u''
	sysConfig['subnet'] = u''
	for i in range(4):
		if sysConfig['broadcast']:
			sysConfig['broadcast'] += u'.'
		if sysConfig['subnet']:
			sysConfig['subnet'] += u'.'

		sysConfig['subnet'] += u'%d' % (int(sysConfig['ipAddress'].split(u'.')[i]) & int(sysConfig['netmask'].split(u'.')[i]))
		sysConfig['broadcast'] += u'%d' % (int(sysConfig['ipAddress'].split(u'.')[i]) | int(sysConfig['netmask'].split(u'.')[i]) ^ 255)

	logger.notice(u"System information:")
	logger.notice(u"   ip address   : %s" % sysConfig['ipAddress'])
	logger.notice(u"   netmask      : %s" % sysConfig['netmask'])
	logger.notice(u"   subnet       : %s" % sysConfig['subnet'])
	logger.notice(u"   broadcast    : %s" % sysConfig['broadcast'])
	logger.notice(u"   fqdn         : %s" % sysConfig['fqdn'])
	logger.notice(u"   hostname     : %s" % sysConfig['hostname'])

	return sysConfig
