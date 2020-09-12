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
import codecs
import tempfile

from OPSI.Logger import Logger
from OPSI.Types import forceUnicode, forceFilename
from OPSI.System import Posix
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
	locateDHCPDInit, reboot, removeSystemHook,
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
Posix.getActiveSessionIds = getActiveSessionIds

def grant_session_access(username: str, session_id: str):
	session_username = None
	session_env = None
	for proc in psutil.process_iter():
		env = proc.environ()
		if env.get("DISPLAY") == session_id:
			if session_env is None or env.get("XAUTHORITY"):
				session_username = proc.username()
				session_env = env
	if not session_env:
		raise ValueError(f"Session {session_id} not found")
	if not session_env.get("XAUTHORITY"):
		session_env["XAUTHORITY"] = os.path.join(session_env.get("HOME"), ".Xauthority")
	
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

	return sp_env
Posix.grant_session_access = grant_session_access

def is_mounted(devOrMountpoint):
	with codecs.open("/proc/mounts", "r", "utf-8") as f:
		for line in f.readlines():
			(dev, mountpoint) = line.split(" ", 2)[:2]
			if devOrMountpoint in (dev, mountpoint):
				return True
	return False
Posix.is_mounted = is_mounted

def mount(dev, mountpoint, **options):
	dev = forceUnicode(dev)
	mountpoint = forceFilename(mountpoint)
	if not os.path.isdir(mountpoint):
		os.makedirs(mountpoint)

	if is_mounted(mountpoint):
		logger.debug("Mountpoint '%s' already mounted, umounting before mount", mountpoint)
		umount(mountpoint)
	
	for (key, value) in options.items():
		options[key] = forceUnicode(value)

	fs = ""
	stdin_data = b""

	tmpFiles = []
	if dev.lower().startswith(('smb://', 'cifs://')):
		match = re.search(r'^(smb|cifs)://([^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = "-t cifs"
			parts = match.group(2).split('/')
			dev = "//%s/%s" % (parts[0], parts[1])
			if 'username' not in options:
				options['username'] = "guest"
			if 'password' not in options:
				options['password'] = ""
			if '\\' in options['username']:
				options['username'] = re.sub(r"\\+", r"\\", options['username'])
				(options['domain'], options['username']) = options['username'].split('\\', 1)

			tf = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="iso-8859-15")
			tf.write(f"username={options['username']}\npassword={options['password']}\n")
			tf.close()
			tmpFiles.append(tf.name)
			options['credentials'] = tf.name
			
			try:
				if not options['domain']:
					del options['domain']
			except KeyError:
				pass
			del options['username']
			del options['password']
		else:
			raise ValueError(f"Bad smb/cifs uri '{dev}'")

	elif dev.lower().startswith(('webdav://', 'webdavs://', 'http://', 'https://')):
		# We need enough free space in /var/cache/davfs2
		# Maximum transfer file size <= free space in /var/cache/davfs2
		match = re.search(r'^(http|webdav)(s*)(://[^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = "-t davfs"
			dev = f"http{match.group(2)}{match.group(3)}"
		else:
			raise ValueError(f"Bad webdav url '{dev}'")
		
		if 'username' not in options:
			options['username'] = ""
		if 'password' not in options:
			options['password'] = ""

		tf = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")
		tf.write("n_cookies 1\ncache_size 0\ntable_size 16384\nuse_locks 0\n")
		tf.close()
		tmpFiles.append(tf.name)
		options['conf'] = tf.name
		
		# Username, Password, Accept certificate for this session? [y,N]
		stdin_data = f"{options['username']}\n{options['password']}\ny\n".encode("utf-8")
		
		del options['username']
		del options['password']

	elif dev.lower().startswith("/"):
		pass

	elif dev.lower().startswith("file://"):
		dev = dev[7:]

	else:
		raise ValueError(f"Cannot mount unknown fs type '{dev}'")
	
	mountOptions = []
	for (key, value) in options.items():
		key = forceUnicode(key)
		value = forceUnicode(value)
		if value:
			mountOptions.append(f"{key}={value}")
		else:
			mountOptions.append(key)

	try:
		while True:
			try:
				if mountOptions:
					optString = '-o "{0}"'.format((u','.join(mountOptions)).replace('"', '\\"'))
				else:
					optString = ''
				proc_env = os.environ.copy()
				proc_env["LC_ALL"] = "C"
				execute("%s %s %s %s %s" % (which('mount'), fs, optString, dev, mountpoint), env=proc_env, stdin_data=stdin_data)
				break
			except Exception as e:
				if fs == "-t cifs" and "vers=2.0" not in mountOptions and "error(95)" in str(e):
					logger.warning("Failed to mount '%s': %s, retrying with option vers=2.0", dev, e)
					mountOptions.append("vers=2.0")
				else:
					logger.error("Failed to mount '%s': %s", dev, e)
					raise RuntimeError("Failed to mount '%s': %s" % (dev, e))
	finally:
		for f in tmpFiles:
			os.remove(f)
Posix.mount = mount
