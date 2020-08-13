# -*- coding: utf-8 -*-
#
# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
#
# Copyright (C) 2006-2019 uib GmbH <info@uib.de>
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import subprocess
import psutil

from OPSI.Logger import Logger
from OPSI.System.Posix import (
	CommandNotFoundException,
	Distribution, Harddisk, NetworkPerformanceCounter, SysInfo,
	SystemSpecificHook, addSystemHook, auditHardware,
	configureInterface, daemonize, execute, get_subprocess_environment, getActiveConsoleSessionId,
	getActiveSessionId, getBlockDeviceBusType,
	getBlockDeviceContollerInfo, getDHCPDRestartCommand, getDHCPResult,
	getDHCPServiceName, getDefaultNetworkInterfaceName, getDiskSpaceUsage,
	getEthernetDevices, getFQDN, getHarddisks, getHostname,
	getKernelParams, getNetworkDeviceConfig, getNetworkInterfaces,
	getSambaServiceName, getServiceNames, getSystemProxySetting, halt,
	hardwareExtendedInventory, hardwareInventory, hooks, ifconfig,
	isCentOS, isDebian, isOpenSUSE, isRHEL, isSLES,
	isUCS, isUbuntu, isXenialSfdiskVersion, locateDHCPDConfig,
	locateDHCPDInit, mount, reboot, removeSystemHook,
	runCommandInSession, setLocalSystemTime, shutdown, umount, which
)

logger = Logger()

__all__ = (
	'CommandNotFoundException',
	'Distribution', 'Harddisk', 'NetworkPerformanceCounter', 'SysInfo',
	'SystemSpecificHook', 'addSystemHook', 'auditHardware',
	'configureInterface', 'daemonize', 'execute', 'get_subprocess_environment', 'getActiveConsoleSessionId',
	'getActiveSessionId', 'getActiveSessionIds', 'getBlockDeviceBusType',
	'getBlockDeviceContollerInfo', 'getDHCPDRestartCommand', 'getDHCPResult',
	'getDHCPServiceName', 'getDefaultNetworkInterfaceName', 'getDiskSpaceUsage',
	'getEthernetDevices', 'getFQDN', 'getHarddisks', 'getHostname',
	'getKernelParams', 'getNetworkDeviceConfig', 'getNetworkInterfaces',
	'getSambaServiceName', 'getServiceNames', 'getSystemProxySetting', 'halt',
	'hardwareExtendedInventory', 'hardwareInventory', 'hooks', 'ifconfig',
	'isCentOS', 'isDebian', 'isOpenSUSE', 'isRHEL', 'isSLES',
	'isUCS', 'isUbuntu', 'isXenialSfdiskVersion', 'locateDHCPDConfig',
	'locateDHCPDInit', 'mount', 'reboot', 'removeSystemHook',
	'runCommandInSession', 'setLocalSystemTime', 'shutdown', 'umount', 'which'
)

def getActiveSessionIds(winApiBugCommand=None, data=None):
	"""
	Getting the IDs of the currently active sessions.

	.. versionadded:: 4.0.5


	:param data: Prefetched data to read information from.
	:type data: [str, ]
	:rtype: [int, ]
	"""
	sessions = []
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			if env.get("DISPLAY") and not env["DISPLAY"] in sessions:
				sessions.append(env["DISPLAY"])
		except psutil.AccessDenied as e:
			logger.debug(e)
	sessions = sorted(sessions, key=lambda s: int(re.sub(r"\D", "", s)))
	return sessions

def grant_session_access(username: str, session_id: str):
	session_username = None
	session_env = None
	for proc in psutil.process_iter():
		env = proc.environ()
		if env.get("DISPLAY") == session_id:
			if session_env is None or env.get("XAUTHORITY"):
				session_username = proc.username()
				session_env = env
	if not session_env.get("XAUTHORITY"):
		session_env["XAUTHORITY"] = os.path.join(session_env.get("HOME"), ".Xauthority")
	if not session_env:
		raise ValueError(f"Session {session_id} not found")
	
	sp_env = get_subprocess_environment(session_env)
	logger.debug("Using process env: %s", sp_env)

	# Allow user to connect to X
	xhost_cmd = ["sudo", "-u", session_username, "xhost", f"+si:localuser:{username}"]
	logger.info("Running command %s", xhost_cmd)
	process = subprocess.run(
		xhost_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		env=sp_env
	)
	out = process.stdout.decode("utf-8", "replace") if process.stdout else ""
	logger.debug("xhost output: %s", out)
