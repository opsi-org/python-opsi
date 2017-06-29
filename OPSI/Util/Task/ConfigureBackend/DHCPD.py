# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2017 uib GmbH <info@uib.de>

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
Functionality to automatically configure the DHCPD-backend.

.. versionadded:: 4.0.6.40

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import grp
import os
import pwd
import shutil
import time

from OPSI.Logger import Logger
from OPSI.System import execute
from OPSI.System.Posix import getDHCPDRestartCommand, locateDHCPDConfig
from OPSI.System.Posix import getNetworkConfiguration
from OPSI.System.Posix import isCentOS, isSLES, isRHEL
from OPSI.Util.File import DHCPDConfFile, DHCPDConf_Block, DHCPDConf_Parameter
from OPSI.Util.Task.Sudoers import patchSudoersFileToAllowRestartingDHCPD

DHCPD_CONF = locateDHCPDConfig(default=u'/etc/dhcp3/dhcpd.conf')
OPSICONFD_USER = u'opsiconfd'
ADMIN_GROUP = u'opsiadmin'

logger = Logger()


def configureDHCPD(configFile=DHCPD_CONF):
	if not os.path.exists(configFile):
		logger.warning("Can't find an dhcpd.conf. Aborting configuration.")
		return

	sysConfig = getNetworkConfiguration()
	logger.notice(u"Configuring dhcpd")

	dhcpdConf = DHCPDConfFile(configFile)
	dhcpdConf.parse()

	confChanged = False
	if dhcpdConf.getGlobalBlock().getParameters_hash().get('use-host-decl-names', False):
		logger.info(u"  use-host-decl-names already enabled")
	else:
		confChanged = True
		logger.notice(u"  enabling use-host-decl-names")
		dhcpdConf.getGlobalBlock().addComponent(
			DHCPDConf_Parameter(
				startLine=-1,
				parentBlock=dhcpdConf.getGlobalBlock(),
				key='use-host-decl-names',
				value=True
			)
		)

	subnets = dhcpdConf.getGlobalBlock().getBlocks('subnet', recursive=True)
	if not subnets:
		confChanged = True
		logger.notice(u"  No subnets found, adding subnet")
		dhcpdConf.getGlobalBlock().addComponent(
			DHCPDConf_Block(
				startLine=-1,
				parentBlock=dhcpdConf.getGlobalBlock(),
				type='subnet',
				settings=['subnet', sysConfig['subnet'], 'netmask', sysConfig['netmask']]))

	for subnet in dhcpdConf.getGlobalBlock().getBlocks('subnet', recursive=True):
		logger.info(u"  Found subnet %s/%s" % (subnet.settings[1], subnet.settings[3]))
		groups = subnet.getBlocks('group')
		if not groups:
			confChanged = True
			logger.notice(u"    No groups found, adding group")
			subnet.addComponent(
				DHCPDConf_Block(
					startLine=-1,
					parentBlock=subnet,
					type='group',
					settings=['group']
				)
			)

		for group in subnet.getBlocks('group'):
			logger.info(u"    Configuring group")
			params = group.getParameters_hash(inherit='global')

			if params.get('next-server'):
				logger.info(u"      next-server already set")
			else:
				confChanged = True
				group.addComponent(
					DHCPDConf_Parameter(
						startLine=-1,
						parentBlock=group,
						key='next-server',
						value=sysConfig['ipAddress']
					)
				)
				logger.notice(u"      next-server set to %s" % sysConfig['ipAddress'])

			if params.get('filename'):
				logger.info(u"      filename already set")
			else:
				confChanged = True
				filename = 'linux/pxelinux.0'
				if isSLES():
					filename = 'opsi/pxelinux.0'
				group.addComponent(
					DHCPDConf_Parameter(
						startLine=-1,
						parentBlock=group,
						key='filename',
						value=filename
					)
				)
				logger.notice(u"      filename set to %s" % filename)

	restartCommand = getDHCPDRestartCommand(default=u'/etc/init.d/dhcp3-server restart')
	if confChanged:
		logger.notice(u"  Creating backup of %s" % configFile)
		shutil.copy(configFile, configFile + u'.' + time.strftime("%Y-%m-%d_%H:%M"))

		logger.notice(u"  Writing new %s" % configFile)
		dhcpdConf.generate()

		logger.notice(u"  Restarting dhcpd")
		try:
			execute(restartCommand)
		except Exception as error:
			logger.warning(error)

	logger.notice(u"Configuring sudoers")
	patchSudoersFileToAllowRestartingDHCPD(restartCommand)

	opsiconfdUid = pwd.getpwnam(OPSICONFD_USER)[2]
	adminGroupGid = grp.getgrnam(ADMIN_GROUP)[2]
	os.chown(configFile, opsiconfdUid, adminGroupGid)
	os.chmod(configFile, 0o664)

	if isRHEL() or isCentOS():
		dhcpDir = os.path.dirname(configFile)
		if dhcpDir == '/etc':
			return

		logger.notice(
			'Detected Red Hat-family system. Providing rights on "{dir}" '
			'to group "{group}"'.format(dir=dhcpDir, group=ADMIN_GROUP)
		)
		os.chown(dhcpDir, -1, adminGroupGid)

	backendConfigFile = os.path.join('/etc', 'opsi', 'backends', 'dhcpd.conf')
	logger.notice('Configuring backend file {0}'.format(backendConfigFile))
	insertDHCPDRestartCommand(backendConfigFile, restartCommand)


def insertDHCPDRestartCommand(dhcpBackendConfigFile, restartCommand):
	"""
	Searches for the 'reloadConfigCommand' in the given file and replaces
	the value of it with `restartCommand`.

	Since the dhcpd.conf usually contains information that is evaluated
	during runtime it is not possible to just read the config and then
	patch the value we want as this would result in destroying the
	dynamic.
	"""
	with open(dhcpBackendConfigFile) as configFile:
		config = configFile.read()

	for line in config.split('\n'):
		if "reloadConfigCommand" in line and not line.startswith('#'):
			_, command = line.split(':', 1)

	command = command.strip()
	logger.debug("Found command: {0!r}".format(command))
	if command.startswith('u'):
		command = command[1:]

	if command.endswith(','):
		command = command[1:-2]
	else:
		command = command[1:-1]

	if command.startswith('sudo '):
		command = command[5:]
	logger.debug("Processed command to be: {0!r}".format(command))

	with open(dhcpBackendConfigFile, 'w') as configFile:
		configFile.write(config.replace(command, restartCommand))
