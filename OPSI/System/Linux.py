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

	credentialsFiles = []
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

			credentialsFile = "/tmp/.cifs-credentials.%s" % parts[0]
			if os.path.exists(credentialsFile):
				os.remove(credentialsFile)
			with open(credentialsFile, "w") as f:
				pass

			os.chmod(credentialsFile, 0o600)
			with codecs.open(credentialsFile, "w", "iso-8859-15") as f:
				f.write("username=%s\n" % options['username'])
				f.write("password=%s\n" % options['password'])
			options['credentials'] = credentialsFile
			credentialsFiles.append(credentialsFile)

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
			fs = u'-t davfs'
			dev = u'http' + match.group(2) + match.group(3)
		else:
			raise ValueError(u"Bad webdav url '%s'" % dev)

		if 'username' not in options:
			options['username'] = u''
		if 'password' not in options:
			options['password'] = u''
		if 'servercert' not in options:
			options['servercert'] = u''

		if options['servercert']:
			with open(u"/etc/davfs2/certs/trusted.pem", "w") as f:
				f.write(options['servercert'])
			os.chmod(u"/etc/davfs2/certs/trusted.pem", 0o644)

		with codecs.open(u"/etc/davfs2/secrets", "r", "utf8") as f:
			lines = f.readlines()

		with codecs.open(u"/etc/davfs2/secrets", "w", "utf8") as f:
			for line in lines:
				if re.search(r"^%s\s+" % dev, line):
					f.write(u"#")
				f.write(line)
			f.write(u'%s "%s" "%s"\n' % (dev, options['username'], options['password']))
		os.chmod(u"/etc/davfs2/secrets", 0o600)

		if options['servercert']:
			with open(u"/etc/davfs2/davfs2.conf", "r") as f:
				lines = f.readlines()

			with open(u"/etc/davfs2/davfs2.conf", "w") as f:
				for line in lines:
					if re.search(r"^servercert\s+", line):
						f.write("#")
					f.write(line)
				f.write(u"servercert /etc/davfs2/certs/trusted.pem\n")

		del options['username']
		del options['password']
		del options['servercert']

	elif dev.lower().startswith(u'/'):
		pass

	elif dev.lower().startswith(u'file://'):
		dev = dev[7:]

	else:
		raise ValueError(f"Cannot mount unknown fs type '{dev}'")

	mountOptions = []
	for (key, value) in options.items():
		key = forceUnicode(key)
		value = forceUnicode(value)
		if value:
			mountOptions.append("{0}={1}".format(key, value))
		else:
			mountOptions.append("{0}".format(key))

	try:
		while True:
			try:
				if mountOptions:
					optString = u'-o "{0}"'.format((u','.join(mountOptions)).replace('"', '\\"'))
				else:
					optString = u''
				execute(u"%s %s %s %s %s" % (which('mount'), fs, optString, dev, mountpoint))
				break
			except Exception as e:
				if fs == "-t cifs" and "vers=2.0" not in mountOptions and "error(95)" in str(e):
					logger.warning("Failed to mount '%s': %s, retrying with option vers=2.0", dev, e)
					mountOptions.append("vers=2.0")
				else:
					logger.error("Failed to mount '%s': %s", dev, e)
					raise RuntimeError("Failed to mount '%s': %s" % (dev, e))
	finally:
		for f in credentialsFiles:
			os.remove(f)
Posix.mount = mount
