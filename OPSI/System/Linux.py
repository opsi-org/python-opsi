# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Linux specific system functions
"""

import os
import re
import socket
import subprocess
import codecs
import tempfile
import psutil

from OPSI.Logger import Logger
from OPSI.Types import forceUnicode, forceFilename
from OPSI.System import Posix
from OPSI.System.Posix import (
	CommandNotFoundException,
	Distribution, Harddisk, NetworkPerformanceCounter, SysInfo,
	SystemSpecificHook, addSystemHook, auditHardware,
	configureInterface, daemonize, execute, get_subprocess_environment, getActiveConsoleSessionId,
	getActiveSessionId, getActiveSessionInformation, getBlockDeviceBusType,
	getBlockDeviceContollerInfo, getDHCPDRestartCommand, getDHCPResult,
	getDHCPServiceName, getDefaultNetworkInterfaceName, getDiskSpaceUsage,
	getEthernetDevices, getFQDN, getHarddisks, getHostname,
	getKernelParams, getNetworkDeviceConfig, getNetworkInterfaces,
	getSambaServiceName, getServiceNames, getSystemProxySetting, halt,
	hardwareExtendedInventory, hardwareInventory, hooks, ifconfig,
	isCentOS, isDebian, isOpenSUSE, isRHEL, isSLES,
	isUCS, isUbuntu, locateDHCPDConfig,
	locateDHCPDInit, reboot, removeSystemHook,
	runCommandInSession, setLocalSystemTime, shutdown, umount, which
)

logger = Logger()

__all__ = (
	'CommandNotFoundException',
	'Distribution', 'Harddisk', 'NetworkPerformanceCounter', 'SysInfo',
	'SystemSpecificHook', 'addSystemHook', 'auditHardware',
	'configureInterface', 'daemonize', 'execute', 'get_subprocess_environment', 'getActiveConsoleSessionId',
	'getActiveSessionId', 'getActiveSessionIds', 'getActiveSessionInformation', 'getSessionInformation',
	'getBlockDeviceBusType',
	'getBlockDeviceContollerInfo', 'getDHCPDRestartCommand', 'getDHCPResult',
	'getDHCPServiceName', 'getDefaultNetworkInterfaceName', 'getDiskSpaceUsage',
	'getEthernetDevices', 'getFQDN', 'getHarddisks', 'getHostname',
	'getKernelParams', 'getNetworkDeviceConfig', 'getNetworkInterfaces',
	'getSambaServiceName', 'getServiceNames', 'getSystemProxySetting', 'halt',
	'hardwareExtendedInventory', 'hardwareInventory', 'hooks', 'ifconfig',
	'isCentOS', 'isDebian', 'isOpenSUSE', 'isRHEL', 'isSLES',
	'isUCS', 'isUbuntu', 'locateDHCPDConfig',
	'locateDHCPDInit', 'mount', 'reboot', 'removeSystemHook',
	'runCommandInSession', 'setLocalSystemTime', 'shutdown', 'umount', 'which'
)

def getActiveSessionIds(protocol = None, states = None):  # pylint: disable=unused-argument
	"""
	Getting the IDs of the currently active sessions.

	.. versionadded:: 4.0.5


	:param data: Prefetched data to read information from.
	:type data: [str, ]
	:rtype: [int, ]
	"""
	if states is None:
		states = ["active", "disconnected"]
	sessions = []
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			# Filter out gdm/1024
			if (
				env.get("USER") and
				env.get("DISPLAY") and
				env["DISPLAY"] != ':1024' and
				env["DISPLAY"] not in sessions
			):
				sessions.append(env["DISPLAY"])
		except psutil.AccessDenied as err:
			logger.debug(err)
	sessions = sorted(sessions, key=lambda s: int(re.sub(r"\D", "", s)))
	return sessions
Posix.getActiveSessionIds = getActiveSessionIds

def getSessionInformation(sessionId):
	info = {
		"SessionId": sessionId,
		"DomainName": None,
		"UserName": None,
	}
	for proc in psutil.process_iter():
		try:
			env = proc.environ()
			if env.get("DISPLAY") == sessionId and env.get("USER"):
				info["DomainName"] = env.get("HOST", info["DomainName"])
				info["UserName"] = env.get("USER", info["UserName"])
				break
		except psutil.AccessDenied as err:
			logger.debug(err)
	if not info["DomainName"]:
		info["DomainName"] = socket.gethostname().upper()
	return info

Posix.getSessionInformation = getSessionInformation

def grant_session_access(username: str, session_id: str):
	session_username = None
	session_env = {}
	for proc in psutil.process_iter():
		env = proc.environ()
		if env.get("DISPLAY") == session_id:
			if env.get("XAUTHORITY"):
				session_username = proc.username()
				session_env = env
				break
			if env.get("USER") != "root":
				session_username = proc.username()
				session_env = env
	if not session_env:
		raise ValueError(f"Session {session_id} not found")

	if "LD_PRELOAD" in session_env:
		del session_env["LD_PRELOAD"]
	if "PATH" in session_env:
		# Keep current PATH
		del session_env["PATH"]

	sp_env = os.environ.copy()
	sp_env.update(session_env)
	sp_env = get_subprocess_environment(sp_env)
	logger.debug("Using process env: %s", sp_env)

	# Allow user to connect to X
	xhost_cmd = ["sudo", "-u", session_username, "xhost", f"+si:localuser:{username}"]
	logger.info("Running command %s", xhost_cmd)
	process = subprocess.run(
		xhost_cmd,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		env=sp_env,
		check=False
	)
	out = process.stdout.decode("utf-8", "replace") if process.stdout else ""
	logger.debug("xhost output: %s", out)

	return sp_env
Posix.grant_session_access = grant_session_access

def is_mounted(devOrMountpoint):
	with codecs.open("/proc/mounts", "r", "utf-8") as file:
		for line in file.readlines():
			(dev, mountpoint) = line.split(" ", 2)[:2]
			if devOrMountpoint in (dev, mountpoint):
				return True
	return False
Posix.is_mounted = is_mounted

def mount(dev, mountpoint, **options):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
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

			tf = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="iso-8859-15")  # pylint: disable=consider-using-with
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

		tf = tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8")  # pylint: disable=consider-using-with
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
			except Exception as err:  # pylint: disable=broad-except
				if fs == "-t cifs" and "vers=2.0" not in mountOptions and "error(95)" in str(err):
					logger.warning("Failed to mount '%s': %s, retrying with option vers=2.0", dev, err)
					mountOptions.append("vers=2.0")
				else:
					logger.error("Failed to mount '%s': %s", dev, err)
					raise RuntimeError("Failed to mount '%s': %s" % (dev, err)) from err
	finally:
		for file in tmpFiles:
			os.remove(file)
Posix.mount = mount
