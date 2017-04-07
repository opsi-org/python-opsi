#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
#
# Copyright (C) 2006-2010, 2013-2017 uib GmbH <info@uib.de>
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
"""
opsi python library - Posix

Functions and classes for the use with a POSIX operating system.

:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import datetime
import fcntl
import locale
import os
import platform
import posix
import re
import socket
import sys
import subprocess
import threading
import time
import copy as pycopy
from itertools import islice
from signal import SIGKILL

from OPSI.Logger import Logger, LOG_NONE
from OPSI.Types import (forceDomain, forceInt, forceBool, forceUnicode,
	forceFilename, forceHostname, forceHostId, forceNetmask, forceIpAddress,
	forceIPAddress, forceHardwareVendorId, forceHardwareAddress,
	forceHardwareDeviceId, forceUnicodeLower)
from OPSI.Types import OpsiVersionError
from OPSI.Object import *
from OPSI.Util import objectToBeautifiedText, removeUnit

__all__ = (
	'Distribution', 'Harddisk', 'NetworkPerformanceCounter', 'SysInfo',
	'SystemSpecificHook', 'addSystemHook', 'auditHardware', 'daemonize',
	'execute', 'getActiveConsoleSessionId', 'getActiveSessionId',
	'getActiveSessionIds', 'getBlockDeviceBusType',
	'getBlockDeviceContollerInfo', 'getDHCPDRestartCommand', 'getDHCPResult',
	'getDHCPServiceName', 'getDefaultNetworkInterfaceName', 'getDiskSpaceUsage',
	'getEthernetDevices', 'getFQDN', 'getHarddisks', 'getHostname',
	'getKernelParams', 'getNetworkDeviceConfig', 'getNetworkInterfaces',
	'getSambaServiceName', 'getServiceNames', 'getSystemProxySetting', 'halt',
	'hardwareExtendedInventory', 'hardwareInventory', 'hooks', 'ifconfig',
	'isCentOS', 'isDebian', 'isOpenSUSE', 'isOpenSUSELeap', 'isRHEL', 'isSLES',
	'isUCS', 'isUbuntu', 'isXenialSfdiskVersion', 'locateDHCPDConfig',
	'locateDHCPDInit', 'mount', 'reboot', 'removeSystemHook',
	'runCommandInSession', 'setLocalSystemTime', 'shutdown', 'umount', 'which'
)

logger = Logger()

# Constants
GEO_OVERWRITE_SO = '/usr/local/lib/geo_override.so'
BIN_WHICH = '/usr/bin/which'
WHICH_CACHE = {}
DHCLIENT_LEASES_FILE = '/var/lib/dhcp/dhclient.leases'
DHCLIENT_LEASES_FILE_OLD = '/var/lib/dhcp3/dhclient.leases'

hooks = []
x86_64 = False
try:
	if "64bit" in platform.architecture():
		x86_64 = True
except Exception:
	pass


class CommandNotFoundException(RuntimeError):
	pass


class SystemSpecificHook(object):
	def __init__(self):
		pass

	def pre_reboot(self, wait):
		return wait

	def post_reboot(self, wait):
		return None

	def error_reboot(self, wait, exception):
		pass


	def pre_halt(self, wait):
		return wait

	def post_halt(self, wait):
		return None

	def error_halt(self, wait, exception):
		pass


	def pre_Harddisk_deletePartitionTable(self, harddisk):
		return None

	def post_Harddisk_deletePartitionTable(self, harddisk):
		return None

	def error_Harddisk_deletePartitionTable(self, harddisk, exception):
		pass


	def pre_Harddisk_writePartitionTable(self, harddisk):
		return None

	def post_Harddisk_writePartitionTable(self, harddisk):
		return None

	def error_Harddisk_writePartitionTable(self, harddisk, exception):
		pass


	def pre_Harddisk_readPartitionTable(self, harddisk):
		return None

	def post_Harddisk_readPartitionTable(self, harddisk):
		return None

	def error_Harddisk_readPartitionTable(self, harddisk, exception):
		pass


	def pre_Harddisk_setPartitionBootable(self, harddisk, partition, bootable):
		return (partition, bootable)

	def post_Harddisk_setPartitionBootable(self, harddisk, partition, bootable):
		return None

	def error_Harddisk_setPartitionBootable(self, harddisk, partition, bootable, exception):
		pass


	def pre_Harddisk_setPartitionId(self, harddisk, partition, id):
		return (partition, id)

	def post_Harddisk_setPartitionId(self, harddisk, partition, id):
		return None

	def error_Harddisk_setPartitionId(self, harddisk, partition, id, exception):
		pass


	def pre_Harddisk_readMasterBootRecord(self, harddisk):
		return None

	def post_Harddisk_readMasterBootRecord(self, harddisk, result):
		return result

	def error_Harddisk_readMasterBootRecord(self, harddisk, exception):
		pass


	def pre_Harddisk_writeMasterBootRecord(self, harddisk, system):
		return system

	def post_Harddisk_writeMasterBootRecord(self, harddisk, system):
		return None

	def error_Harddisk_writeMasterBootRecord(self, harddisk, system, exception):
		pass


	def pre_Harddisk_readPartitionBootRecord(self, harddisk, partition):
		return partition

	def post_Harddisk_readPartitionBootRecord(self, harddisk, partition, result):
		return result

	def error_Harddisk_readPartitionBootRecord(self, harddisk, partition, exception):
		pass


	def pre_Harddisk_writePartitionBootRecord(self, harddisk, partition, fsType):
		return (partition, fsType)

	def post_Harddisk_writePartitionBootRecord(self, harddisk, partition, fsType):
		return None

	def error_Harddisk_writePartitionBootRecord(self, harddisk, partition, fsType, exception):
		pass


	def pre_Harddisk_setNTFSPartitionStartSector(self, harddisk, partition, sector):
		return (partition, sector)

	def post_Harddisk_setNTFSPartitionStartSector(self, harddisk, partition, sector):
		return None

	def error_Harddisk_setNTFSPartitionStartSector(self, harddisk, partition, sector, exception):
		pass


	def pre_Harddisk_createPartition(self, harddisk, start, end, fs, type, boot, lba):
		return (start, end, fs, type, boot, lba)

	def post_Harddisk_createPartition(self, harddisk, start, end, fs, type, boot, lba):
		return None

	def error_Harddisk_createPartition(self, harddisk, start, end, fs, type, boot, lba, exception):
		pass


	def pre_Harddisk_deletePartition(self, harddisk, partition):
		return partition

	def post_Harddisk_deletePartition(self, harddisk, partition):
		return None

	def error_Harddisk_deletePartition(self, harddisk, partition, exception):
		pass


	def pre_Harddisk_mountPartition(self, harddisk, partition, mountpoint, **options):
		return (partition, mountpoint, options)

	def post_Harddisk_mountPartition(self, harddisk, partition, mountpoint, **options):
		return None

	def error_Harddisk_mountPartition(self, harddisk, partition, mountpoint, exception, **options):
		pass


	def pre_Harddisk_umountPartition(self, harddisk, partition):
		return partition

	def post_Harddisk_umountPartition(self, harddisk, partition):
		return None

	def error_Harddisk_umountPartition(self, harddisk, partition, exception):
		pass


	def pre_Harddisk_createFilesystem(self, harddisk, partition, fs):
		return (partition, fs)

	def post_Harddisk_createFilesystem(self, harddisk, partition, fs):
		return None

	def error_Harddisk_createFilesystem(self, harddisk, partition, fs, exception):
		pass


	def pre_Harddisk_resizeFilesystem(self, harddisk, partition, size, fs):
		return (partition, size, fs)

	def post_Harddisk_resizeFilesystem(self, harddisk, partition, size, fs):
		return None

	def error_Harddisk_resizeFilesystem(self, harddisk, partition, size, fs, exception):
		pass


	def pre_Harddisk_shred(self, harddisk, partition, iterations, progressSubject):
		return (partition, iterations, progressSubject)

	def post_Harddisk_shred(self, harddisk, partition, iterations, progressSubject):
		return None

	def error_Harddisk_shred(self, harddisk, partition, iterations, progressSubject, exception):
		pass


	def pre_Harddisk_fill(self, harddisk, partition, infile, progressSubject):
		return (partition, infile, progressSubject)

	def post_Harddisk_fill(self, harddisk, partition, infile, progressSubject):
		return None

	def error_Harddisk_fill(self, harddisk, partition, infile, progressSubject, exception):
		pass


	def pre_Harddisk_saveImage(self, harddisk, partition, imageFile, progressSubject):
		return (partition, imageFile, progressSubject)

	def post_Harddisk_saveImage(self, harddisk, partition, imageFile, progressSubject):
		return None

	def error_Harddisk_saveImage(self, harddisk, partition, imageFile, progressSubject, exception):
		pass


	def pre_Harddisk_restoreImage(self, harddisk, partition, imageFile, progressSubject):
		return (partition, imageFile, progressSubject)

	def post_Harddisk_restoreImage(self, harddisk, partition, imageFile, progressSubject):
		return None

	def error_Harddisk_restoreImage(self, harddisk, partition, imageFile, progressSubject, exception):
		pass


	def pre_auditHardware(self, config, hostId, progressSubject):
		return (config, hostId, progressSubject)

	def post_auditHardware(self, config, hostId, result):
		return result

	def error_auditHardware(self, config, hostId, progressSubject, exception):
		pass


def addSystemHook(hook):
	global hooks
	if hook not in hooks:
		hooks.append(hook)


def removeSystemHook(hook):
	global hooks
	if hook in hooks:
		hooks.remove(hook)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                               INFO                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getHostname():
	return forceHostname(socket.gethostname())


def getFQDN():
	return forceUnicodeLower(socket.getfqdn())


def getKernelParams():
	"""
	Reads the kernel cmdline and returns a dict
	containing all key=value pairs.
	keys are converted to lower case
	"""
	cmdline = ''
	try:
		logger.debug(u'Reading /proc/cmdline')
		with codecs.open("/proc/cmdline", "r", "utf-8") as f:
			cmdline = f.readline()

		cmdline = cmdline.strip()
	except IOError as e:
		raise Exception(u"Error reading '/proc/cmdline': %s" % e)

	params = {}
	for option in cmdline.split():
		keyValue = option.split(u"=")
		if len(keyValue) < 2:
			params[keyValue[0].strip().lower()] = u''
		else:
			params[keyValue[0].strip().lower()] = keyValue[1].strip()

	return params


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            NETWORK                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getEthernetDevices():
	"""
	Get the ethernet devices on the system.

	:return: For each device the name of the device.
	:returntype: [str]
	"""
	devices = []
	with open("/proc/net/dev") as f:
		for line in f:
			line = line.strip()
			if not line or ':' not in line:
				continue

			device = line.split(':')[0].strip()
			if device.startswith(('eth', 'ens', 'eno', 'tr', 'br', 'enp', 'enx')):
				logger.info(u"Found ethernet device: '{0}'".format(device))
				devices.append(device)

	return devices


def getNetworkInterfaces():
	"""
	Get information about the network interfaces on the system.

	:returntype: [{}]
	"""
	return [getNetworkDeviceConfig(device) for device in getEthernetDevices()]


def getNetworkDeviceConfig(device):
	if not device:
		raise Exception(u"No device given")

	result = {
		'device': device,
		'hardwareAddress': None,
		'ipAddress': None,
		'broadcast': None,
		'netmask': None,
		'gateway': None,
		'vendorId': None,
		'deviceId': None
	}

	for line in execute(u"{ifconfig} {device}".format(ifconfig=which(u'ifconfig'), device=device)):
		line = line.lower().strip()
		match = re.search('\s([\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}:[\da-f]{2}).*', line)
		if match:
			result['hardwareAddress'] = forceHardwareAddress(match.group(1))
			continue

		if line.startswith('inet '):
			logger.debug('Found inet line: {0}'.format(line))

			parts = line.split(':')
			if len(parts) == 4:
				result['ipAddress'] = forceIpAddress(parts[1].split()[0].strip())
				result['broadcast'] = forceIpAddress(parts[2].split()[0].strip())
				result['netmask'] = forceIpAddress(parts[3].split()[0].strip())
				continue

			match = re.search(
				"^\w+\s+(?P<ipAddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+"
				"\w+\s+(?P<netmask>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+"
				"\w+\s+(?P<broadcast>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$",
				line
			)
			if match:
				result['ipAddress'] = forceIpAddress(match.group('ipAddress'))
				result['broadcast'] = forceIpAddress(match.group('broadcast'))
				result['netmask'] = forceIpAddress(match.group('netmask'))
				continue

			logger.error(u"Unexpected ifconfig line '%s'" % line)

	for line in execute(u"{ip} route".format(ip=which(u'ip'))):
		line = line.lower().strip()
		match = re.search('via\s(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\sdev\s(\S+)\s*', line)
		if match and match.group(2).lower() == device.lower():
			result['gateway'] = forceIpAddress(match.group(1))

	try:
		with open('/sys/class/net/%s/device/vendor' % device) as f:
			x = f.read().strip()

		if x.startswith('0x'):
			x = eval(x)
		x = "%x" % int(x)
		result['vendorId'] = forceHardwareVendorId(((4-len(x))*'0') + x)

		with open('/sys/class/net/%s/device/device' % device) as f:
			x = f.read().strip()

		if x.startswith('0x'):
			x = eval(x)
		x = int(x)
		if result['vendorId'] == '1AF4':
			# FIXME: what is wrong with virtio devices?
			x += 0xfff
		x = "%x" % x
		result['deviceId'] = forceHardwareDeviceId(((4 - len(x)) * '0') + x)
	except Exception:
		logger.warning(u"Failed to get vendor/device id for network device %s" % device)
	return result


def getDefaultNetworkInterfaceName():
	for interface in getNetworkInterfaces():
		if interface['gateway']:
			logger.info(u"Default network interface found: %s" % interface['device'])
			return interface['device']
	logger.info(u"Default network interface not found")
	return None


class NetworkPerformanceCounter(threading.Thread):
	def __init__(self, interface):
		threading.Thread.__init__(self)
		if not interface:
			raise ValueError(u"No interface given")
		self.interface = interface
		self._lastBytesIn = 0
		self._lastBytesOut = 0
		self._lastTime = None
		self._bytesInPerSecond = 0
		self._bytesOutPerSecond = 0
		self._regex = re.compile('\s*(\S+)\:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')
		self._running = False
		self._stopped = False
		self.start()

	def __del__(self):
		self.stop()

	def stop(self):
		self._stopped = True

	def run(self):
		self._running = True
		while not self._stopped:
			self._getStatistics()
			time.sleep(1)

	def _getStatistics(self):
		with open('/proc/net/dev', 'r') as f:
			for line in f:
				line = line.strip()
				match = self._regex.search(line)
				if match and match.group(1) == self.interface:
					#       |   Receive                                                |  Transmit
					# iface: bytes    packets errs drop fifo frame compressed multicast bytes    packets errs drop fifo colls carrier compressed
					now = time.time()
					bytesIn = int(match.group(2))
					bytesOut = int(match.group(10))
					timeDiff = 1
					if self._lastTime:
						timeDiff = now - self._lastTime
					if self._lastBytesIn:
						self._bytesInPerSecond = (bytesIn - self._lastBytesIn)/timeDiff
						if self._bytesInPerSecond < 0:
							self._bytesInPerSecond = 0
					if self._lastBytesOut:
						self._bytesOutPerSecond = (bytesOut - self._lastBytesOut)/timeDiff
						if self._bytesOutPerSecond < 0:
							self._bytesOutPerSecond = 0
					self._lastBytesIn = bytesIn
					self._lastBytesOut = bytesOut
					self._lastTime = now
					break

	def getBytesInPerSecond(self):
		return self._bytesInPerSecond

	def getBytesOutPerSecond(self):
		return self._bytesOutPerSecond


def getDHCPResult(device, leasesFile=None):
	"""
	Get the settings of the current DHCP lease.

	It first tries to read the value from leases files and then tries
	to read the values from pump.

	.. versionchanged:: 4.0.5.1
	   Added parameter *leasesFile*.

	:param leasesFile: The file to read the leases from. If this is not \
given known places for this file will be tried.
	:type leasesFile: str
	:return: Settings of the lease. All keys are lowercase. Possible \
keys are: ``ip``, ``netmask``, ``bootserver``, ``nextserver``, \
``gateway``, ``bootfile``, ``hostname``, ``domain``.
	:returntype: dict
	"""
	if not device:
		raise Exception(u"No device given")

	if not leasesFile:
		if os.path.exists(DHCLIENT_LEASES_FILE_OLD):
			# old style dhcp.leases handling should be work
			# will be removed, if precise bootimage is in testing.
			leasesFile = DHCLIENT_LEASES_FILE_OLD
		else:
			leasesFile = DHCLIENT_LEASES_FILE

	dhcpResult = {}
	if os.path.exists(leasesFile):
		with open(leasesFile) as leasesFileHandler:
			try:
				currentInterface = None
				for line in leasesFileHandler:
					line = line.strip()
					if line.endswith(';'):
						line = line[:-1].strip()
					if line.startswith('interface '):
						currentInterface = line.split('"')[1]
					if device != currentInterface:
						continue

					if line.startswith('filename '):
						dhcpResult['bootfile'] = dhcpResult['filename'] = line.split('"')[1].strip()
					elif line.startswith('option domain-name '):
						dhcpResult['domain'] = dhcpResult['domain-name'] = line.split('"')[1].strip()
					elif line.startswith('option domain-name-servers '):
						dhcpResult['nameservers'] = dhcpResult['domain-name-servers'] = line.split(' ', 2)[-1]
					elif line.startswith('fixed-address '):
						dhcpResult['ip'] = dhcpResult['fixed-address'] = line.split(' ', 1)[-1]
					elif line.startswith('option host-name '):
						dhcpResult['hostname'] = dhcpResult['host-name'] = line.split('"')[1].strip()
					elif line.startswith('option subnet-mask '):
						dhcpResult['netmask'] = dhcpResult['subnet-mask'] = line.split(' ', 2)[-1]
					elif line.startswith('option routers '):
						dhcpResult['gateways'] = dhcpResult['routers'] = line.split(' ', 2)[-1]
					elif line.startswith('option netbios-name-servers '):
						dhcpResult['netbios-name-servers'] = line.split(' ', 2)[-1]
					elif line.startswith('option dhcp-server-identifier '):
						dhcpResult['bootserver'] = dhcpResult['dhcp-server-identifier'] = line.split(' ', 2)[-1]
					elif line.startswith('renew '):
						dhcpResult['renew'] = line.split(' ', 1)[-1]
					elif line.startswith('rebind '):
						dhcpResult['rebind'] = line.split(' ', 1)[-1]
					elif line.startswith('expire '):
						dhcpResult['expire'] = line.split(' ', 1)[-1]
			except Exception as error:
				logger.warning(error)
	else:
		logger.debug('Leases file {0} does not exist.'.format(leasesFile))
		logger.debug('Trying to use pump for getting dhclient info.')
		try:
			for line in execute(u'%s -s -i %s' % (which('pump'), device)):
				line = line.strip()
				keyValue = line.split(u":")
				if len(keyValue) < 2:
					# No ":" in pump output after "boot server" and
					# "next server"
					if line.lstrip().startswith(u'Boot server'):
						keyValue[0] = u'Boot server'
						keyValue.append(line.split()[2])
					elif line.lstrip().startswith(u'Next server'):
						keyValue[0] = u'Next server'
						keyValue.append(line.split()[2])
					else:
						continue
				# Some DHCP-Servers are returning multiple domain names
				# seperated by whitespace, so we split all values at
				# whitespace and take the first element
				dhcpResult[keyValue[0].replace(u' ', u'').lower()] = keyValue[1].strip().split()[0]
		except Exception as error:
			logger.warning(error)
	return dhcpResult


def ifconfig(device, address, netmask=None):
	cmd = u'%s %s %s' % (which('ifconfig'), device, forceIpAddress(address))
	if netmask:
		cmd += u' netmask %s' % forceNetmask(netmask)
	execute(cmd)


def getSystemProxySetting():
	#TODO Have to be implemented for posix machines
	logger.notice(u'Not Implemented yet')

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                   SESSION / DESKTOP HANDLING                                      -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def reboot(wait=10):
	for hook in hooks:
		wait = hook.pre_reboot(wait)

	try:
		wait = forceInt(wait)
		if wait > 0:
			execute(u'%s %d; %s -r -t 1' % (which('sleep'), wait, which('shutdown')), nowait=True)
		else:
			execute(u'%s -r -t 1' % which('shutdown'), nowait=True)
	except Exception as e:
		for hook in hooks:
			hook.error_reboot(wait, e)
		raise

	for hook in hooks:
		hook.post_reboot(wait)


def halt(wait=10):
	for hook in hooks:
		wait = hook.pre_halt(wait)

	try:
		wait = forceInt(wait)
		if wait > 0:
			execute(u'%s %d; %s -h now' % (which('sleep'), wait, which('shutdown')), nowait=True)
		else:
			execute(u'%s -h now' % which('shutdown'), nowait=True)
	except Exception as e:
		for hook in hooks:
			hook.error_halt(wait, e)
		raise

	for hook in hooks:
		hook.post_halt(wait)

shutdown = halt


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                        PROCESS HANDLING                                           -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def which(cmd):
	if cmd not in WHICH_CACHE:
		w = os.popen(u'%s "%s" 2>/dev/null' % (BIN_WHICH, cmd))
		path = w.readline().strip()
		w.close()
		if not path:
			raise CommandNotFoundException(u"Command {0!r} not found in PATH".format(cmd))

		logger.debug(u"Command {0!r} found at: {1!r}", cmd, path)
		WHICH_CACHE[cmd] = path

	return WHICH_CACHE[cmd]


def execute(cmd, nowait=False, getHandle=False, ignoreExitCode=[], exitOnStderr=False, captureStderr=True, encoding=None, timeout=0, shell=None, waitForEnding=None):
	"""
	Executes a command.

	:param nowait: If this is ``True`` the command will be executed and \
no waiting for it to finish will be done.
	:type nowait: bool
	:param getHandle: If this is ``True`` the handle the reference to \
the command output will be returned.
	:type getHandle: bool
	:param ignoreExitCode: Ignore exit codes of the program. This can \
be ``True`` to ignore all exit codes or a list of specific exit codes \
that should be ignored.
	:type ignoreExitCode: bool or list or tuple or set
	:param exitOnStderr: If this is ``True`` output on stderr will be \
interpreted as an failed execution and will throw an Exception.
	:type exitOnStderr: bool
	:param captureStderr: If this is ``True`` the output of *stderr* \
will be redirected to *stdout*.
	:type captureStderr: bool
	:param encoding: The encoding to be used to decode the output.
	:type encoding: str
	:param timeout: The time in seconds after that the execution will \
be aborted.
	:type timeout: int
	:param shell: Currently ignored. This is introduced to have the \
same keyword arguments as on Windows.
	:param waitForEnding: If this is set it will overwrite the setting \
for *nowait*. This is introduced to have the same keyword arguments as \
on Windows.
	:type waitForEnding: bool
	:return: If the command finishes and we wait for it to finish the \
output will be returned.
	:returntype: list
	"""
	nowait = forceBool(nowait)
	getHandle = forceBool(getHandle)
	exitOnStderr = forceBool(exitOnStderr)
	captureStderr = forceBool(captureStderr)
	timeout = forceInt(timeout)

	if shell is not None:
		logger.warning("Argument 'shell' is unsupported on Linux.")

	if waitForEnding is not None:
		logger.debug("Detected kwarg 'waitForEnding'. Overwriting nowait.")
		nowait = not forceBool(waitForEnding)

	exitCode = 0
	result = []

	startTime = time.time()
	try:
		logger.info(u"Executing: %s" % cmd)

		if nowait:
			os.spawnv(os.P_NOWAIT, which('bash'), [which('bash'), '-c', cmd])
			return []

		elif getHandle:
			if captureStderr:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)).stdout
			else:
				return (subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None)).stdout

		else:
			data = ''
			stderr = None
			if captureStderr:
				stderr = subprocess.PIPE
			proc = subprocess.Popen(
				cmd,
				shell=True,
				stdin=subprocess.PIPE,
				stdout=subprocess.PIPE,
				stderr=stderr,
			)

			if not encoding:
				encoding = proc.stdin.encoding
				if encoding == 'ascii':
					encoding = 'utf-8'
			if not encoding:
				encoding = locale.getpreferredencoding()
				if encoding == 'ascii':
					encoding = 'utf-8'
			logger.info(u"Using encoding '%s'" % encoding)

			flags = fcntl.fcntl(proc.stdout, fcntl.F_GETFL)
			fcntl.fcntl(proc.stdout, fcntl.F_SETFL, flags | os.O_NONBLOCK)

			if captureStderr:
				flags = fcntl.fcntl(proc.stderr, fcntl.F_GETFL)
				fcntl.fcntl(proc.stderr, fcntl.F_SETFL, flags | os.O_NONBLOCK)

			ret = None
			while ret is None:
				ret = proc.poll()
				try:
					chunk = proc.stdout.read()
					if len(chunk) > 0:
						data += chunk
				except IOError as e:
					if e.errno != 11:
						raise

				if captureStderr:
					try:
						chunk = proc.stderr.read()
						if len(chunk) > 0:
							if exitOnStderr:
								raise Exception(u"Command '%s' failed: %s" % (cmd, chunk))
							data += chunk
					except IOError as e:
						if e.errno != 11:
							raise

				if timeout > 0 and (time.time() - startTime >= timeout):
					_terminateProcess(proc)
					raise Exception(u"Command '%s' timed out atfer %d seconds" % (cmd, (time.time() - startTime)))

				time.sleep(0.001)

			exitCode = ret
			if data:
				lines = data.split('\n')
				for i, line in enumerate(lines):
					line = line.decode(encoding, 'replace')
					if i == len(lines) - 1 and not line:
						break
					logger.debug(u'>>> %s' % line)
					result.append(line)

	except (os.error, IOError) as e:
		# Some error occurred during execution
		raise Exception(u"Command '%s' failed:\n%s" % (cmd, e))

	logger.debug(u"Exit code: %s" % exitCode)
	if exitCode:
		if isinstance(ignoreExitCode, bool) and ignoreExitCode:
			pass
		elif isinstance(ignoreExitCode, (list, tuple, set)) and exitCode in ignoreExitCode:
			pass
		else:
			raise Exception(u"Command '%s' failed (%s):\n%s" % (cmd, exitCode, u'\n'.join(result)))
	return result


def _terminateProcess(process):
	"""
	Terminate a running process.

	:param process: The process to terminate.
	:type process: subprocess.Popen
	"""
	try:
		process.kill()
	except Exception as killException:
		logger.debug('Killing process {0} failed: {1}'.format(process.pid, killException))

		try:
			os.kill(process.pid, SIGKILL)
		except Exception as sigKillException:
			logger.debug('Sending SIGKILL to pid {0} failed: {1}'.format(process.pid, sigKillException))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            FILESYSTEMS                                            -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def isXenialSfdiskVersion():
	"""
	check for sfdisk version to adapt commands to changed output

	Returns `True` for versions equal 2.27.1 - the one used in Ubuntu Xenial.
	"""
	sfdiskVersionOutput = execute('%s --version' % which('sfdisk'))
	sfdiskVersion = sfdiskVersionOutput[0].split(' ')[3].strip()
	return bool(sfdiskVersion == '2.27.1')


def getHarddisks(data=None):
	"""
	Get the available harddisks from the machine.

	:param data: Data to parse through.
	:type data: [str, ]
	:return: The found harddisks.
	:returntype: [Harddisk, ]
	"""
	disks = []

	if data is None:
		# Get all available disks
		if os.path.exists("/dev/cciss"):
			result = []
			logger.notice("HP Smart Array detected, trying to workarround scan problem.")
			listing = os.listdir("/dev/cciss")
			for entry in listing:
				if len(entry) < 5:
					dev = entry
					if isXenialSfdiskVersion():
						size = forceInt(execute(u'%s --no-reread -s /dev/cciss/%s' % (which('sfdisk'), dev), ignoreExitCode=[1])[0])
					else:
						size = forceInt(execute(u'%s -L --no-reread -s -uB /dev/cciss/%s' % (which('sfdisk'), dev), ignoreExitCode=[1])[0])
					logger.debug(
						u"Found disk =>>> dev: '{device}', size: {size:0.2f} GB".format(
							device=dev,
							size=size / (1024 * 1024)
							)
						)
					hd = Harddisk("/dev/cciss/%s" % dev)
					disks.append(hd)
			if len(disks) <= 0:
				raise Exception(u'No harddisks found!')
			return disks
		else:
			if isXenialSfdiskVersion():
				result = execute(u'%s --no-reread -s ' % which('sfdisk'), ignoreExitCode=[1])
			else:
				result = execute(u'%s -L --no-reread -s -uB' % which('sfdisk'), ignoreExitCode=[1])
	else:
		result = data

	for line in result:
		if not line.lstrip().startswith(u'/dev'):
			continue

		(dev, size) = line.split(u':')
		size = forceInt(size.strip())
		logger.debug(
			u"Found disk =>>> dev: '{device}', size: {size:0.2f} GB".format(
				device=dev,
				size=size / (1024 * 1024)
			)
		)

		hd = Harddisk(dev)
		disks.append(hd)

	if len(disks) <= 0:
		raise Exception(u'No harddisks found!')

	return disks


def getDiskSpaceUsage(path):
	disk = os.statvfs(path)
	info = {}
	info['capacity'] = disk.f_bsize * disk.f_blocks
	info['available'] = disk.f_bsize * disk.f_bavail
	info['used'] = disk.f_bsize * (disk.f_blocks - disk.f_bavail)
	info['usage'] = float(disk.f_blocks - disk.f_bavail) / float(disk.f_blocks)
	logger.info(u"Disk space usage for path '%s': %s" % (path, info))
	return info


def mount(dev, mountpoint, **options):
	dev = forceUnicode(dev)
	mountpoint = forceFilename(mountpoint)
	if not os.path.isdir(mountpoint):
		os.makedirs(mountpoint)

	for (key, value) in options.items():
		options[key] = forceUnicode(value)

	fs = u''

	credentialsFiles = []
	if dev.lower().startswith(('smb://', 'cifs://')):
		match = re.search('^(smb|cifs)://([^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = u'-t cifs'
			parts = match.group(2).split('/')
			dev = u'//%s/%s' % (parts[0], parts[1])
			if 'username' not in options:
				options['username'] = u'guest'
			if 'password' not in options:
				options['password'] = u''
			if '\\' in options['username']:
				(options['domain'], options['username']) = options['username'].split('\\', 1)

			credentialsFile = u"/tmp/.cifs-credentials.%s" % parts[0]
			if os.path.exists(credentialsFile):
				os.remove(credentialsFile)
			with open(credentialsFile, "w") as f:
				pass

			os.chmod(credentialsFile, 0o600)
			with codecs.open(credentialsFile, "w", "iso-8859-15") as f:
				f.write(u"username=%s\n" % options['username'])
				f.write(u"password=%s\n" % options['password'])
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
			raise Exception(u"Bad smb/cifs uri '%s'" % dev)

	elif dev.lower().startswith(('webdav://', 'webdavs://', 'http://', 'https://')):
		# We need enough free space in /var/cache/davfs2
		# Maximum transfer file size <= free space in /var/cache/davfs2
		match = re.search('^(http|webdav)(s*)(://[^/]+\/.+)$', dev, re.IGNORECASE)
		if match:
			fs = u'-t davfs'
			dev = u'http' + match.group(2) + match.group(3)
		else:
			raise Exception(u"Bad webdav url '%s'" % dev)

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
				if re.search("^%s\s+" % dev, line):
					f.write(u"#")
				f.write(line)
			f.write(u'%s "%s" "%s"\n' % (dev, options['username'], options['password']))
		os.chmod(u"/etc/davfs2/secrets", 0o600)

		if options['servercert']:
			with open(u"/etc/davfs2/davfs2.conf", "r") as f:
				lines = f.readlines()

			with open(u"/etc/davfs2/davfs2.conf", "w") as f:
				for line in lines:
					if re.search("^servercert\s+", line):
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
		raise Exception(u"Cannot mount unknown fs type '%s'" % dev)

	mountOptions = []
	for (key, value) in options.items():
		key = forceUnicode(key)
		value = forceUnicode(value)
		if value:
			mountOptions.append("{0}={1}".format(key, value))
		else:
			mountOptions.append("{0}".format(key))

	if mountOptions:
		optString = u'-o "{0}"'.format((u','.join(mountOptions)).replace('"', '\\"'))
	else:
		optString = u''

	try:
		execute(u"%s %s %s %s %s" % (which('mount'), fs, optString, dev, mountpoint))
	except Exception as e:
		logger.error(u"Failed to mount '%s': %s" % (dev, e))
		raise Exception(u"Failed to mount '%s': %s" % (dev, e))
	finally:
		for f in credentialsFiles:
			os.remove(f)


def umount(devOrMountpoint):
	try:
		execute(u"%s %s" % (which('umount'), devOrMountpoint))
	except Exception as e:
		logger.error(u"Failed to umount '%s': %s" % (devOrMountpoint, e))
		raise Exception(u"Failed to umount '%s': %s" % (devOrMountpoint, e))


def getBlockDeviceBusType(device):
	"""
	:return: 'IDE', 'SCSI', 'SATA', 'RAID' or None (not found)
	:returntype: str or None
	"""
	device = forceFilename(device)

	(devs, type) = ([], None)
	if os.path.islink(device):
		d = os.readlink(device)
		if not d.startswith(u'/'):
			d = os.path.join(os.path.dirname(device), d)
		device = d

	for line in execute(u'%s --disk --cdrom' % which('hwinfo')):
		if re.search('^\s+$', line):
			(devs, type) = ([], None)
			continue

		match = re.search('^\s+Device Files*:(.*)$', line)
		if match:
			if match.group(1).find(u',') != -1:
				devs = match.group(1).split(u',')
			elif match.group(1).find(u'(') != -1:
				devs = match.group(1).replace(u')', u' ').split(u'(')
			else:
				devs = [match.group(1)]

			devs = [currentDev.strip() for currentDev in devs]

		match = re.search('^\s+Attached to:\s+[^\(]+\((\S+)\s*', line)
		if match:
			type = match.group(1)

		if devs and device in devs and type:
			logger.info(u"Bus type of device '%s' is '%s'" % (device, type))
			return type


def getBlockDeviceContollerInfo(device, lshwoutput=None):
	device = forceFilename(device)
	if lshwoutput and isinstance(lshwoutput, list):
		lines = lshwoutput
	else:
		lines = execute(u'%s -short -numeric' % which('lshw'))
	# example:
	# ...
	# /0/100                      bridge     440FX - 82441FX PMC [Natoma] [8086:1237]
	# /0/100/1                    bridge     82371SB PIIX3 ISA [Natoma/Triton II] [8086:7000]
	# /0/100/1.1      scsi0       storage    82371SB PIIX3 IDE [Natoma/Triton II] [8086:7010]
	# /0/100/1.1/0    /dev/sda    disk       10GB QEMU HARDDISK
	# /0/100/1.1/0/1  /dev/sda1   volume     10236MiB Windows NTFS volume
	# /0/100/1.1/1    /dev/cdrom  disk       SCSI CD-ROM
	# ...
	storageControllers = {}

	for line in lines:
		match = re.search('^(/\S+)\s+(\S+)\s+storage\s+(\S+.*)\s\[([a-fA-F0-9]{1,4})\:([a-fA-F0-9]{1,4})\]$', line)
		if match:
			vendorId = match.group(4)
			while len(vendorId) < 4:
				vendorId = '0' + vendorId
			deviceId = match.group(5)
			while len(deviceId) < 4:
				deviceId = '0' + deviceId
			storageControllers[match.group(1)] = {
				'hwPath':      forceUnicode(match.group(1)),
				'device':      forceUnicode(match.group(2)),
				'description': forceUnicode(match.group(3)),
				'vendorId':    forceHardwareVendorId(vendorId),
				'deviceId':    forceHardwareDeviceId(deviceId)
			}
			continue

		parts = line.split(None, 3)
		if len(parts) < 4:
			continue
		if parts[1].lower() == device:
			for hwPath in storageControllers.keys():
				if parts[0].startswith(hwPath + u'/'):
					return storageControllers[hwPath]

	# emulated storage controller dirty-hack, for outputs like:
	# ...
	# /0/100/1f.2               storage        82801JD/DO (ICH10 Family) SATA AHCI Controller [8086:3A02]
	# /0/100/1f.3               bus            82801JD/DO (ICH10 Family) SMBus Controller [8086:3A60]
	# /0/1          scsi0       storage
	# /0/1/0.0.0    /dev/sda    disk           500GB ST3500418AS
	# /0/1/0.0.0/1  /dev/sda1   volume         465GiB Windows FAT volume
	# ...
	# In this case return the first AHCI controller, that will be found
	storageControllers = {}

	for line in lines:
		match = re.search('^(/\S+)\s+storage\s+(\S+.*[Aa][Hh][Cc][Ii].*)\s\[([a-fA-F0-9]{1,4})\:([a-fA-F0-9]{1,4})\]$', line)
		if match:
			vendorId = match.group(3)
			while len(vendorId) < 4:
				vendorId = '0' + vendorId
			deviceId = match.group(4)
			while len(deviceId) < 4:
				deviceId = '0' + deviceId
			storageControllers[match.group(1)] = {
				'hwPath':      forceUnicode(match.group(1)),
				'device':      device,
				'description': forceUnicode(match.group(2)),
				'vendorId':    forceHardwareVendorId(vendorId),
				'deviceId':    forceHardwareDeviceId(deviceId)
			}
			if storageControllers:
				for hwPath in storageControllers.keys():
					return storageControllers[hwPath]
		else:
			# Quick Hack: for entry like this:
			# /0/100/1f.2              storage        82801 SATA Controller [RAID mode] [8086:2822]
			# This Quick hack is for Bios-Generations, that will only
			# have a choice for "RAID + AHCI", this devices will be shown as
			# RAID mode-Devices
			match = re.search('^(/\S+)\s+storage\s+(\S+.*[Rr][Aa][Ii][Dd].*)\s\[([a-fA-F0-9]{1,4})\:([a-fA-F0-9]{1,4})\]$', line)
			if match:
				vendorId = match.group(3)
				while len(vendorId) < 4:
					vendorId = '0' + vendorId
				deviceId = match.group(4)
				while len(deviceId) < 4:
					deviceId = '0' + deviceId
				storageControllers[match.group(1)] = {
					'hwPath':      forceUnicode(match.group(1)),
					'device':      device,
					'description': forceUnicode(match.group(2)),
					'vendorId':    forceHardwareVendorId(vendorId),
					'deviceId':    forceHardwareDeviceId(deviceId)
				}
				if storageControllers:
					for hwPath in storageControllers.keys():
						return storageControllers[hwPath]

	return None


class Harddisk:

	def __init__(self, device):
		self.device = forceFilename(device)
		self.model = u''
		self.signature = None
		self.biosDevice = None
		self.totalCylinders = 0
		self.cylinders = 0
		self.heads = 0
		self.sectors = 0
		self.bytesPerSector = 512
		self.label = None
		self.size = -1
		self.partitions = []
		self.ldPreload = None
		self.dosCompatibility = True
		self.blockAlignment = False
		self.rotational = True

		self.useBIOSGeometry()
		self.readPartitionTable()
		self.readRotational()

	def setDosCompatibility(self, comp=True):
		self.dosCompatibility = bool(comp)

	def setBlockAlignment(self, align=False):
		self.blockAlignment = bool(align)

	def getBusType(self):
		return getBlockDeviceBusType(self.device)

	def getControllerInfo(self):
		return getBlockDeviceContollerInfo(self.device)

	def useBIOSGeometry(self):
		# Make sure your kernel supports edd (CONFIG_EDD=y/m) and module is loaded if not compiled in
		try:
			execute(u'%s edd' % which('modprobe'))
		except Exception as e:
			logger.error(e)
			return

		# geo_override.so will affect all devices !
		if not x86_64:
			logger.info(u"Using geo_override.so for all disks.")
			self.ldPreload = GEO_OVERWRITE_SO
		else:
			logger.info(u"Don't load geo_override.so on 64bit architecture.")

	def readRotational(self):
		"""
		Checks if a disk is rotational.

		The result of the check is saved in the attribute *rotational*.

		.. versionadded:: 4.0.4.2
		"""
		try:
			deviceparts = self.device.split("/")
			if len(deviceparts) > 3:
				if deviceparts[2].lower() == "cciss":
					logger.info(u"Special device (cciss) detected")
					devicename = "!".join(deviceparts[1:])
					if not os.path.exists('/sys/block/{0}/queue/rotational'.format(devicename)):
						raise Exception("rotational file '/sys/block/{0}/queue/rotational' not found!".format(devicename))
				else:
					logger.error(u"Unknown device, fallback to default: rotational")
					return
			else:
				devicename = self.device.split("/")[2]

			for line in execute(u'cat /sys/block/{0}/queue/rotational'.format(devicename)):
				try:
					self.rotational = forceBool(int(line.strip()))
					break
				except Exception:
					pass
		except Exception as error:
			logger.error(
				'Checking if the device {name} is rotational failed: '
				'{error}'.format(name=self.device, error=error)
			)

	def getSignature(self):
		hd = posix.open(str(self.device), posix.O_RDONLY)
		posix.lseek(hd, 440, 0)
		x = posix.read(hd, 4)
		posix.close(hd)

		logger.debug(u"Read signature from device '%s': %s,%s,%s,%s" \
				% (self.device, ord(x[0]), ord(x[1]), ord(x[2]), ord(x[3])))

		self.signature = 0
		self.signature += ord(x[3]) << 24
		self.signature += ord(x[2]) << 16
		self.signature += ord(x[1]) << 8
		self.signature += ord(x[0])
		logger.debug(u"Device Signature: '%s'" % hex(self.signature))

	def setDiskLabelType(self, label):
		label = forceUnicodeLower(label)
		if label not in (u"bsd", u"gpt", u"loop", u"mac", u"mips", u"msdos", u"pc98", u"sun"):
			raise Exception(u"Unknown disk label '%s'" % label)
		self.label = label

	def setPartitionId(self, partition, id):
		for hook in hooks:
			(partition, id) = hook.pre_Harddisk_setPartitionId(self, partition, id)
		try:
			partition = forceInt(partition)
			id = forceUnicodeLower(id)

			if (partition < 1) or (partition > 4):
				raise Exception(u"Partition has to be int value between 1 and 4")

			if not re.search('^[a-f0-9]{2}$', id):
				if id in (u'linux', u'ext2', u'ext3', u'ext4', u'xfs', u'reiserfs', u'reiser4'):
					id = u'83'
				elif id == u'linux-swap':
					id = u'82'
				elif id == u'fat32':
					id = u'0c'
				elif id == u'ntfs':
					id = u'07'
				else:
					raise Exception(u"Partition type '%s' not supported!" % id)
			id = eval('0x' + id)
			offset = 0x1be + (partition-1) * 16 + 4
			with open(self.device, 'rb+') as f:
				f.seek(offset)
				f.write(chr(id))
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_setPartitionId(self, partition, id, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_setPartitionId(self, partition, id)

	def setPartitionBootable(self, partition, bootable):
		for hook in hooks:
			(partition, bootable) = hook.pre_Harddisk_setPartitionBootable(self, partition, bootable)
		try:
			partition = forceInt(partition)
			bootable = forceBool(bootable)
			if (partition < 1) or (partition > 4):
				raise Exception("Partition has to be int value between 1 and 4")

			offset = 0x1be + (partition-1)*16 + 4
			with open(self.device, 'rb+') as f:
				f.seek(offset)
				if bootable:
					f.write(chr(0x80))
				else:
					f.write(chr(0x00))
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_setPartitionBootable(self, partition, bootable, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_setPartitionBootable(self, partition, bootable)

	def readPartitionTable(self):
		for hook in hooks:
			hook.pre_Harddisk_readPartitionTable(self)

		try:
			self.partitions = []
			os.putenv("LC_ALL", "C")
			if self.ldPreload:  # We want this as a context manager!
				os.putenv("LD_PRELOAD", self.ldPreload)
			if isXenialSfdiskVersion():
				result = execute(u'{sfdisk} --no-reread -s {device}'.format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			else:
				result = execute(u'{sfdisk} -L --no-reread -s -uB {device}'.format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			for line in result:
				try:
					self.size = int(line.strip()) * 1024
				except Exception:
					pass

			logger.info(u"Size of disk '%s': %s Byte / %s MB" % (self.device, self.size, (self.size/(1024*1024))))
			if isXenialSfdiskVersion():
				result = execute(u"{sfdisk} --no-reread -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			else:
				result = execute(u"{sfdisk} -L --no-reread -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			partTablefound = None
			for line in result:
				if line.startswith("/dev"):
					partTablefound = True
					break
			if not partTablefound:
				logger.notice(u"unrecognized partition table type, writing empty partitiontable")
				if isXenialSfdiskVersion():
					execute('{echo} -e "0,0\n\n\n\n" | {sfdisk} --no-reread -D {device}'.format(echo=which('echo'), sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
					result = execute("{sfdisk} --no-reread -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
				else:
					execute('{echo} -e "0,0\n\n\n\n" | {sfdisk} -L --no-reread -D {device}'.format(echo=which('echo'), sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
					result = execute("{sfdisk} -L --no-reread -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])

			self._parsePartitionTable(result)

			if isXenialSfdiskVersion():
				result = execute(u"{sfdisk} --no-reread -uS -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			else:
				result = execute(u"{sfdisk} -L --no-reread -uS -l {device}".format(sfdisk=which('sfdisk'), device=self.device), ignoreExitCode=[1])
			self._parseSectorData(result)

			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_readPartitionTable(self, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_readPartitionTable(self)

	def _parsePartitionTable(self, sfdiskListingOutput):
		"""
		Parses the partition table and sets the corresponding attributes
		on this object.

		:param sfdiskListingOutput: The output from ``sfdisk -l /dev/foo``
		:type sfdiskListingOutput: [str, ]
		"""

		for line in sfdiskListingOutput:
			line = line.strip()

			if line.lower().startswith('disk'):
				if isXenialSfdiskVersion():

					geometryOutput = execute(u"{sfdisk} -g {device}".format(sfdisk=which('sfdisk'), device=self.device))
					for line in geometryOutput:
						match = re.search('\s+(\d+)\s+cylinders,\s+(\d+)\s+heads,\s+(\d+)\s+sectors', line)
						if not match:
							raise Exception(u"Unable to get geometry for disk '%s'" % self.device)
						self.cylinders = forceInt(match.group(1))
						self.heads = forceInt(match.group(2))
						self.sectors = forceInt(match.group(3))
						self.totalCylinders = self.cylinders
				else:
					match = re.search('\s+(\d+)\s+cylinders,\s+(\d+)\s+heads,\s+(\d+)\s+sectors', line)
					if not match:
						raise Exception(u"Unable to get geometry for disk '%s'" % self.device)

					self.cylinders = forceInt(match.group(1))
					self.heads = forceInt(match.group(2))
					self.sectors = forceInt(match.group(3))
					self.totalCylinders = self.cylinders

			elif line.lower().startswith(u'units'):
				if isXenialSfdiskVersion():
					match = re.search('sectors\s+of\s+\d\s+.\s+\d+\s+.\s+(\d+)\s+bytes', line)

				else:
					match = re.search('cylinders\s+of\s+(\d+)\s+bytes', line)

				if not match:
					raise Exception(u"Unable to get bytes/cylinder for disk '%s'" % self.device)
				self.bytesPerCylinder = forceInt(match.group(1))
				self.totalCylinders = int(self.size / self.bytesPerCylinder)
				logger.info(u"Total cylinders of disk '%s': %d, %d bytes per cylinder" % (self.device, self.totalCylinders, self.bytesPerCylinder))

			elif line.startswith(self.device):
				if isXenialSfdiskVersion():
					match = re.search('(%sp*)(\d+)\s+(\**)\s*(\d+)[\+\-]*\s+(\d*)[\+\-]*\s+(\d+)[\+\-]*\s+(\d+)[\+\-]*.?\d*\S+\s+(\S+)\s*(.*)' % self.device, line)

					if not match:
						raise Exception(u"Unable to read partition table of disk '%s'" % self.device)
				else:
					match = re.search('(%sp*)(\d+)\s+(\**)\s*(\d+)[\+\-]*\s+(\d*)[\+\-]*\s+(\d+)[\+\-]*\s+(\d+)[\+\-]*\s+(\S+)\s+(.*)' % self.device, line)

					if not match:
						raise Exception(u"Unable to read partition table of disk '%s'" % self.device)

				if match.group(5):
					boot = False
					if match.group(3) == u'*':
						boot = True

					fs = u'unknown'
					fsType = forceUnicodeLower(match.group(8))
					if fsType in (u"w95", u"b", u"c", u"e"):
						fs = u'fat32'
					elif fsType in (u"hpfs/ntfs/exfat", u"hfps/ntfs", u"7"):
						fs = u'ntfs'

					deviceName = forceFilename(match.group(1) + match.group(2))
					try:
						logger.debug("Trying using Blkid")
						fsres = execute(u'%s -o value -s TYPE %s' % (which('blkid'), deviceName))
						if fsres:
							for line in fsres:
								line = line.strip()
								if not line:
									continue
								logger.debug(u"Found filesystem: %s with blkid tool, using now this filesystemtype." % line)
								fs = line
					except Exception:
						pass

					partitionData = {
							'device': deviceName,
							'number': forceInt(match.group(2)),
							'cylStart': forceInt(match.group(4)),
							'cylEnd': forceInt(match.group(5)),
							'cylSize': forceInt(match.group(6)),
							'start': forceInt(match.group(4)) * self.bytesPerCylinder,
							'end': (forceInt(match.group(5))+1) * self.bytesPerCylinder,
							'size': forceInt(match.group(6)) * self.bytesPerCylinder,
							'type': fsType,
							'fs': fs,
							'boot': boot
						}

					self.partitions.append(partitionData)

					logger.debug(
						u"Partition found =>>> number: %s, "
						u"start: %s MB (%s cyl), end: %s MB (%s cyl), "
						u"size: %s MB (%s cyl), "
						u"type: %s, fs: %s, boot: %s" % (
							partitionData['number'],
							partitionData['start'] / (1024 * 1024),
							partitionData['cylStart'],
							partitionData['end'] / (1024 * 1024),
							partitionData['cylEnd'],
							partitionData['size'] / (1024 * 1024),
							partitionData['cylSize'],
							match.group(8),
							fs,
							boot
						)
					)

					if partitionData['device']:
						logger.debug(u"Waiting for device '%s' to appear" % partitionData['device'])
						timeout = 15
						while timeout > 0:
							if os.path.exists(partitionData['device']):
								break
							time.sleep(1)
							timeout -= 1
						if os.path.exists(partitionData['device']):
							logger.debug(u"Device '%s' found" % partitionData['device'])
						else:
							logger.warning(u"Device '%s' not found" % partitionData['device'])

	def _parseSectorData(self, outputFromSfDiskListing):
		"""
		Parses the sector data of the disk and extends the existing
		partition data.

		:param outputFromSfDiskListing: Output of ``sfdisk -uS -l /dev/foo``
		:type outputFromSfDiskListing: [str, ]
		"""
		for line in outputFromSfDiskListing:
			line = line.strip()

			if line.startswith(self.device):
				if isXenialSfdiskVersion():
					match = re.match('%sp*(\d+)\s+(\**)\s*(\d+)[\+\-]*\s+(\d*)[\+\-]*\s+(\d+)[\+\-]*\s+(\d+)[\+\-]*.?\d*\S+\s+(\S+)\s*(.*)' % self.device, line)
				else:
					match = re.search('%sp*(\d+)\s+(\**)\s*(\d+)[\+\-]*\s+(\d*)[\+\-]*\s+(\d+)[\+\-]*\s+(\S+)\s+(.*)' % self.device, line)
				if not match:
					raise Exception(u"Unable to read partition table (sectors) of disk '%s'" % self.device)

				if match.group(4):
					for p, partition in enumerate(self.partitions):
						if forceInt(partition['number']) == forceInt(match.group(1)):
							partition['secStart'] = forceInt(match.group(3))
							partition['secEnd'] = forceInt(match.group(4))
							partition['secSize'] = forceInt(match.group(5))
							self.partitions[p] = partition
							logger.debug(
								u"Partition sector values =>>> number: %s, "
								u"start: %s sec, end: %s sec, size: %s sec " \
								% (
									partition['number'],
									partition['secStart'],
									partition['secEnd'],
									partition['secSize']
							   )
							)
							break

			elif line.lower().startswith('units'):
				if isXenialSfdiskVersion():
					match = re.search('sectors\s+of\s+\d\s+.\s+\d+\s+.\s+(\d+)\s+bytes', line)

				else:
					match = re.search('sectors\s+of\s+(\d+)\s+bytes', line)
				if not match:
					raise Exception(u"Unable to get bytes/sector for disk '%s'" % self.device)
				self.bytesPerSector = forceInt(match.group(1))
				self.totalSectors = int(self.size / self.bytesPerSector)
				logger.info(u"Total sectors of disk '%s': %d, %d bytes per cylinder" % (self.device, self.totalSectors, self.bytesPerSector))

	def writePartitionTable(self):
		logger.debug(u"Writing partition table to disk %s" % self.device)
		for hook in hooks:
			hook.pre_Harddisk_writePartitionTable(self)
		try:
			cmd = u'%s -e "' % which('echo')
			for p in range(4):
				try:
					part = self.getPartition(p + 1)
					if self.blockAlignment:
						logger.debug(u"   number: %s, start: %s MB (%s sec), end: %s MB (%s sec), size: %s MB (%s sec), " \
								% (part['number'],
									(part['start']/(1000*1000)), part['secStart'],
									(part['end']/(1000*1000)), part['secEnd'],
									(part['size']/(1000*1000)), part['secSize']) \
								+ "type: %s, fs: %s, boot: %s" \
								% (part['type'], part['fs'], part['boot']))

						cmd += u'%s,%s,%s' % (part['secStart'], part['secSize'], part['type'])
					else:
						logger.debug(u"   number: %s, start: %s MB (%s cyl), end: %s MB (%s cyl), size: %s MB (%s cyl), " \
									% (part['number'],
										(part['start']/(1000*1000)), part['cylStart'],
										(part['end']/(1000*1000)), part['cylEnd'],
										(part['size']/(1000*1000)), part['cylSize']) \
									+ "type: %s, fs: %s, boot: %s" \
									% (part['type'], part['fs'], part['boot']))

						cmd += u'%s,%s,%s' % (part['cylStart'], part['cylSize'], part['type'])
					if part['boot']:
						cmd += u',*'
				except Exception as e:
					logger.debug(u"Partition %d not found: %s" % ((p+1), e))
					cmd += u'0,0'

				cmd += u'\n'
			dosCompat = u''
			if self.dosCompatibility:
				dosCompat = u'-D '
			if self.blockAlignment:
				cmd += u'" | %s -L --no-reread -uS -f %s' % (which('sfdisk'), self.device)
			else:
				if isXenialSfdiskVersion():
					cmd += u'" | %s -L --no-reread %s' % (which('sfdisk'), self.device)
				else:
					cmd += u'" | %s -L --no-reread -uC %s%s' % (which('sfdisk'), dosCompat, self.device)
			if self.ldPreload:
				os.putenv("LD_PRELOAD", self.ldPreload)

			#changing execution to os.system
			execute(cmd, ignoreExitCode=[1])
			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")
			self._forceReReadPartionTable()
			time.sleep(2)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_writePartitionTable(self, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_writePartitionTable(self)

	def _forceReReadPartionTable(self):
		if self.ldPreload:
			os.putenv("LD_PRELOAD", self.ldPreload)
		logger.info(u"Forcing kernel to reread partition table of '%s'." % self.device)
		try:
			execute(u'%s %s' % (which('partprobe'), self.device))
		except Exception:
			logger.error(u"Forcing kernel reread partion table failed, waiting 5 sec. and try again")
			try:
				time.sleep(5)
				execute(u'%s %s' % (which('partprobe'), self.device), ignoreExitCode=[1])
			except Exception:
				logger.error(u"Reread Partiontabel failed the second time, given up.")
				raise
		if self.ldPreload:
			os.unsetenv("LD_PRELOAD")

	def deletePartitionTable(self):
		logger.info(u"Deleting partition table on '%s'" % self.device)
		for hook in hooks:
			hook.pre_Harddisk_deletePartitionTable(self)
		try:
			with open(self.device, 'rb+') as f:
				f.write(chr(0) * 512)

			self._forceReReadPartionTable()
			self.label = None
			self.partitions = []
			self.readPartitionTable()
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_deletePartitionTable(self, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_deletePartitionTable(self)

	def shred(self, partition=0, iterations=25, progressSubject=None):
		for hook in hooks:
			(partition, iterations, progressSubject) = hook.pre_Harddisk_shred(self, partition, iterations, progressSubject)

		try:
			partition = forceInt(partition)
			iterations = forceInt(iterations)

			dev = self.device
			if partition != 0:
				dev = self.getPartition(partition)['device']

			cmd = u"%s -v -n %d %s 2>&1" % (which('shred'), iterations, dev)

			lineRegex = re.compile('\s(\d+)\/(\d+)\s\(([^\)]+)\)\.\.\.(.*)$')
			posRegex = re.compile('([^\/]+)\/(\S+)\s+(\d+)%')
			handle = execute(cmd, getHandle=True)
			position = u''
			error = u''
			if progressSubject:
				progressSubject.setEnd(100)

			for line in iter(lambda: handle.readline().strip(), ''):
				logger.debug(u"From shred =>>> %s" % line)
				# shred: /dev/xyz: Pass 1/25 (random)...232MiB/512MiB 45%
				match = re.search(lineRegex, line)
				if match:
					iteration = forceInt(match.group(1))
					dataType = match.group(3)
					logger.debug(u"Iteration: %d, data-type: %s" % (iteration, dataType))
					match = re.search(posRegex, match.group(4))
					if match:
						position = match.group(1) + '/' + match.group(2)
						percent = forceInt(match.group(3))
						logger.debug(u"Position: %s, percent: %d" % (position, percent))
						if progressSubject and (percent != progressSubject.getState()):
							progressSubject.setState(percent)
							progressSubject.setMessage(u"Pass %d/%d (%s), position: %s" \
									% (iteration, iterations, dataType, position))
				else:
					error = line

			ret = handle.close()
			logger.debug(u"Exit code: %s" % ret)

			if ret:
				raise Exception(u"Command '%s' failed: %s" % (cmd, error))

		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_shred(self, partition, iterations, progressSubject, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_shred(self, partition, iterations, progressSubject)

	def zeroFill(self, partition=0, progressSubject=None):
		self.fill(forceInt(partition), u'/dev/zero', progressSubject)

	def randomFill(self, partition=0, progressSubject=None):
		self.fill(forceInt(partition), u'/dev/urandom', progressSubject)

	def fill(self, partition=0, infile=u'', progressSubject=None):
		for hook in hooks:
			(partition, infile, progressSubject) = hook.pre_Harddisk_fill(self, partition, infile, progressSubject)

		try:
			partition = forceInt(partition)
			if not infile:
				raise Exception(u"No input file given")
			infile = forceFilename(infile)

			xfermax = 0
			dev = self.device
			if partition != 0:
				dev = self.getPartition(partition)['device']
				xfermax = int(round(float(self.getPartition(partition)['size']) / 1024))
			else:
				xfermax = int(round(float(self.size) / 1024))

			if progressSubject:
				progressSubject.setEnd(100)

			cmd = u"%s -m %sk %s %s 2>&1" % (which('dd_rescue'), xfermax, infile, dev)

			handle = execute(cmd, getHandle=True)
			done = False

			skip = 0
			rate = 0
			position = 0
			timeout = 0
			while not done:
				inp = handle.read(1024)
				# dd_rescue: (info): ipos:    720896.0k, opos:    720896.0k, xferd:    720896.0k
				# 		   errs:      0, errxfer:         0.0k, succxfer:    720896.0k
				# 	     +curr.rate:    21843kB/s, avg.rate:    23526kB/s, avg.load: 17.4%
				if inp:
					timeout = 0
					skip += 1
					if u'Summary' in inp:
						done = True

				elif timeout >= 10:
					raise Exception(u"Failed (timed out)")

				else:
					timeout += 1
					continue

				if skip < 10:
					time.sleep(0.1)
					continue
				else:
					skip = 0

				if progressSubject:
					match = re.search('avg\.rate:\s+(\d+)kB/s', inp)
					if match:
						rate = match.group(1)
					match = re.search('ipos:\s+(\d+)\.\d+k', inp)
					if match:
						position = forceInt(match.group(1))
						percent = (position * 100) / xfermax
						logger.debug(u"Position: %s, xfermax: %s, percent: %s" % (position, xfermax, percent))
						if percent != progressSubject.getState():
							progressSubject.setState(percent)
							progressSubject.setMessage(u"Pos: %s MB, average transfer rate: %s kB/s" % (round((position) / 1024), rate))

			if progressSubject:
				progressSubject.setState(100)
			time.sleep(3)
			if handle:
				handle.close
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_fill(self, partition, infile, progressSubject, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_fill(self, partition, infile, progressSubject)

	def readMasterBootRecord(self):
		for hook in hooks:
			hook.pre_Harddisk_readMasterBootRecord(self)
		mbr = None
		try:
			with open(self.device, 'rb') as f:
				mbr = f.read(512)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_readMasterBootRecord(self, e)
			raise

		for hook in hooks:
			mbr = hook.post_Harddisk_readMasterBootRecord(self, mbr)
		return mbr

	def writeMasterBootRecord(self, system=u'auto'):
		for hook in hooks:
			system = hook.pre_Harddisk_writeMasterBootRecord(self, system)

		try:
			system = forceUnicodeLower(system)

			try:
				logger.debug("Try to determine ms-sys version")
				cmd = u"%s -v" % (which('ms-sys'))
				res = execute(cmd)
				if res:
					ms_sys_version = res[0][14:].strip()
			except Exception:
				ms_sys_version = u"2.1.3"

			mbrType = u'-w'

			if system in (u'win2000', u'winxp', u'win2003', u'nt5'):
				mbrType = u'--mbr'
			elif system in (u'vista', u'win7', u'nt6'):
				if ms_sys_version != "2.1.3":
					if system == u'vista':
						mbrType = u'--mbrvista'
					else:
						mbrType = u'--mbr7'
				else:
					mbrType = u'--mbrnt60'
			elif system in (u'win9x', u'win95', u'win98'):
				mbrType = u'--mbr95b'
			elif system in (u'dos', u'winnt'):
				mbrType = u'--mbrdos'

			logger.info(u"Writing master boot record on '%s' (system: %s)" % (self.device, system))

			cmd = u"%s %s %s" % (which('ms-sys'), mbrType, self.device)
			try:
				if self.ldPreload:
					os.putenv("LD_PRELOAD", self.ldPreload)
				execute(cmd)
				if self.ldPreload:
					os.unsetenv("LD_PRELOAD")
			except Exception as e:
				logger.error(u"Failed to write mbr: %s" % e)
				raise Exception(u"Failed to write mbr: %s" % e)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_writeMasterBootRecord(self, system, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_writeMasterBootRecord(self, system)

	def readPartitionBootRecord(self, partition=1):
		for hook in hooks:
			partition = hook.pre_Harddisk_readPartitionBootRecord(self, partition)
		pbr = None
		try:
			with open(self.getPartition(partition)['device'], 'rb') as f:
				pbr = f.read(512)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_readPartitionBootRecord(self, partition, e)
			raise

		for hook in hooks:
			pbr = hook.post_Harddisk_readPartitionBootRecord(self, partition, pbr)
		return pbr

	def writePartitionBootRecord(self, partition=1, fsType=u'auto'):
		for hook in hooks:
			(partition, fsType) = hook.pre_Harddisk_writePartitionBootRecord(self, partition, fsType)

		try:
			partition = forceInt(partition)
			fsType = forceUnicodeLower(fsType)

			logger.info(u"Writing partition boot record on '%s' (fs-type: %s)" % (self.getPartition(partition)['device'], fsType))

			if fsType == u'auto':
				fsType = u'-w'
			else:
				fsType = u'--%s' % fsType

			time.sleep(10)

			cmd = u"%s -p %s %s" % (which('ms-sys'), fsType, self.getPartition(partition)['device'])
			try:
				if self.ldPreload:
					os.putenv("LD_PRELOAD", self.ldPreload)
				result = execute(cmd)
				if self.ldPreload:
					os.unsetenv("LD_PRELOAD")
				if u'successfully' not in result[0]:
					raise Exception(result)
			except Exception as e:
				logger.error(u"Cannot write partition boot record: %s" % e)
				raise Exception(u"Cannot write partition boot record: %s" % e)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_writePartitionBootRecord(self, partition, fsType, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_writePartitionBootRecord(self, partition, fsType)

	def setNTFSPartitionStartSector(self, partition, sector=0):
		for hook in hooks:
			(partition, sector) = hook.pre_Harddisk_setNTFSPartitionStartSector(self, partition, sector)

		try:
			partition = forceInt(partition)
			sector = forceInt(sector)
			if not sector:
				sector = self.getPartition(partition)['secStart']
				if not sector:
					err = u"Failed to get partition start sector of partition '%s'" % (self.getPartition(partition)['device'])
					logger.error(err)
					raise Exception(err)

			logger.info(
				u"Setting Partition start sector to {0} in NTFS boot record "
				u"on partition '{1}'".format(
					sector,
					self.getPartition(partition)['device']
				)
			)

			x = [0, 0, 0, 0]
			x[0] = int((sector & 0x000000FF))
			x[1] = int((sector & 0x0000FF00) >> 8)
			x[2] = int((sector & 0x00FF0000) >> 16)
			x[3] = int((sector & 0xFFFFFFFF) >> 24)

			hd = posix.open(self.getPartition(partition)['device'], posix.O_RDONLY)
			posix.lseek(hd, 0x1c, 0)
			start = posix.read(hd, 4)
			logger.debug(
				u"NTFS Boot Record currently using {0} {1} {2} {3} "
				u"as partition start sector".format(
					hex(ord(start[0])), hex(ord(start[1])),
					hex(ord(start[2])), hex(ord(start[3])))
			)
			posix.close(hd)

			logger.debug(u"Manipulating NTFS Boot Record!")
			hd = posix.open(self.getPartition(partition)['device'], posix.O_WRONLY)
			logger.info(u"Writing new value %s %s %s %s at 0x1c" % (hex(x[0]), hex(x[1]), hex(x[2]), hex(x[3])))
			posix.lseek(hd, 0x1c, 0)
			for i in x:
				posix.write(hd, chr(i))
			posix.close(hd)

			hd = posix.open(self.getPartition(partition)['device'], posix.O_RDONLY)
			posix.lseek(hd, 0x1c, 0)
			start = posix.read(hd, 4)
			logger.debug(
				u"NTFS Boot Record now using {0} {1} {2} {3} as partition "
				u"start sector".format(
					hex(ord(start[0])), hex(ord(start[1])),
					hex(ord(start[2])), hex(ord(start[3])))
			)
			posix.close(hd)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_setNTFSPartitionStartSector(self, partition, sector, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_setNTFSPartitionStartSector(self, partition, sector)

	def getPartitions(self):
		return self.partitions

	def getPartition(self, number):
		number = forceInt(number)
		for part in self.partitions:
			if part['number'] == number:
				return part
		raise Exception(u'Partition %s does not exist' % number)

	def createPartition(self, start, end, fs, type=u'primary', boot=False, lba=False, number=None):
		for hook in hooks:
			(start, end, fs, type, boot, lba) = hook.pre_Harddisk_createPartition(self, start, end, fs, type, boot, lba)
		try:
			start = forceUnicodeLower(start)
			end = forceUnicodeLower(end)
			fs = forceUnicodeLower(fs)
			type = forceUnicodeLower(type)
			boot = forceBool(boot)
			lba = forceBool(lba)

			partId = u'00'
			if re.search('^[a-f0-9]{2}$', fs):
				partId = fs
			else:
				if fs in (u'ext2', u'ext3', u'ext4', u'xfs', u'reiserfs', u'reiser4', u'linux'):
					partId = u'83'
				elif fs == u'linux-swap':
					partId = u'82'
				elif fs == u'fat32':
					partId = u'c'
				elif fs == u'ntfs':
					partId = u'7'
				else:
					raise Exception("Filesystem '%s' not supported!" % fs)

			if type != u'primary':
				raise Exception("Type '%s' not supported!" % type)

			unit = 'cyl'
			if self.blockAlignment:
				unit = 'sec'
			start = start.replace(u' ', u'')
			end = end.replace(u' ', u'')

			if start.endswith((u'm', u'mb')):
				match = re.search('^(\d+)\D', start)
				if self.blockAlignment:
					start = int(round((int(match.group(1)) * 1024 * 1024) / self.bytesPerSector))
				else:
					start = int(round((int(match.group(1)) * 1024 * 1024) / self.bytesPerCylinder))
			elif start.endswith((u'g', u'gb')):
				match = re.search('^(\d+)\D', start)
				if self.blockAlignment:
					start = int(round((int(match.group(1)) * 1024 * 1024 * 1024) / self.bytesPerSector))
				else:
					start = int(round((int(match.group(1)) * 1024 * 1024 * 1024) / self.bytesPerCylinder))
			elif start.lower().endswith(u'%'):
				match = re.search('^(\d+)\D', start)
				if self.blockAlignment:
					start = int(round((float(match.group(1)) / 100) * self.totalSectors))
				else:
					start = int(round((float(match.group(1)) / 100) * self.totalCylinders))
			elif start.lower().endswith(u's'):
				match = re.search('^(\d+)\D', start)
				start = int(match.group(1))
				if not self.blockAlignment:
					start = int(round(((float(start) * self.bytesPerSector) / self.bytesPerCylinder)))
			elif start.lower().endswith(u'c'):
				# Cylinder!
				start = int(start)
				if self.blockAlignment:
					start = int(round(((float(start) * self.bytesPerCylinder) / self.bytesPerSector)))
			else:
				# Cylinder!
				start = int(start)
				if self.blockAlignment:
					start = int(round(((float(start) * self.bytesPerCylinder) / self.bytesPerSector)))

			if end.endswith((u'm', u'mb')):
				match = re.search('^(\d+)\D', end)
				if self.blockAlignment:
					end = int(round((int(match.group(1)) * 1024 * 1024) / self.bytesPerSector))
				else:
					end = int(round((int(match.group(1)) * 1024 * 1024) / self.bytesPerCylinder))
			elif end.endswith((u'g', u'gb')):
				match = re.search('^(\d+)\D', end)
				if self.blockAlignment:
					end = int(round((int(match.group(1)) * 1024 * 1024 * 1024) / self.bytesPerSector))
				else:
					end = int(round((int(match.group(1)) * 1024 * 1024 * 1024) / self.bytesPerCylinder))
			elif end.lower().endswith(u'%'):
				match = re.search('^(\d+)\D', end)
				if self.blockAlignment:
					end = int(round((float(match.group(1)) / 100) * self.totalSectors))
				else:
					end = int(round((float(match.group(1)) / 100) * self.totalCylinders))
			elif end.lower().endswith(u's'):
				match = re.search('^(\d+)\D', end)
				end = int(match.group(1))
				if not self.blockAlignment:
					end = int(round(((float(end) * self.bytesPerSector) / self.bytesPerCylinder)))
			elif end.lower().endswith(u'c'):
				# Cylinder!
				end = int(end)
				if self.blockAlignment:
					end = int(round(((float(end) * self.bytesPerCylinder) / self.bytesPerSector)))
			else:
				# Cylinder!
				end = int(end)
				if self.blockAlignment:
					end = int(round(((float(end) * self.bytesPerCylinder) / self.bytesPerSector)))

			if unit == 'cyl':
				if start < 0:
					# Lowest possible cylinder is 0
					start = 0
				if end >= self.totalCylinders:
					# Highest possible cylinder is total cylinders - 1
					end = self.totalCylinders - 1
			else:
				modulo = start % 2048
				if modulo:
					start = start + 2048 - modulo

				modulo = end % 2048
				end = end + 2048 - (end % 2048) - 1

				if start < 2048:
					start = 2048

				if end >= self.totalSectors:
					# Highest possible sectors is total sectors - 1
					end = self.totalSectors-1

			# if no number given - count
			if not number:
				number = len(self.partitions) + 1

			for part in self.partitions:
				if unit == 'sec':
					partitionStart = part['secStart']
				else:
					partitionStart = part['cylStart']
				if end <= partitionStart:
					if part['number'] - 1 <= number:
						# Insert before
						number = part['number'] - 1

			try:
				prev = self.getPartition(number - 1)
				if unit == 'sec':
					if start <= prev['secEnd']:
						# Partitions overlap
						start = prev['secEnd'] + 1
				else:
					if start <= prev['cylEnd']:
						# Partitions overlap
						start = prev['cylEnd'] + 1
			except Exception:
				pass

			try:
				next = self.getPartition(number + 1)
				nextstart = next['cylStart']
				if unit == 'sec':
					nextstart = next['secStart']

				if end >= nextstart:
					# Partitions overlap
					end = nextstart - 1
			except Exception:
				pass

			if isXenialSfdiskVersion():
				if start < 2048:
					start = 2048

			if unit == 'sec':
				logger.info(u"Creating partition on '%s': number: %s, type '%s', filesystem '%s', start: %s sec, end: %s sec." \
							% (self.device, number, type, fs, start, end))

				if number < 1 or number > 4:
					raise Exception(u'Cannot create partition %s' % number)

				self.partitions.append(
					{
						'number': number,
						'secStart': start,
						'secEnd': end,
						'secSize': end - start + 1,
						'start': start * self.bytesPerSector,
						'end': end * self.bytesPerSector,
						'size': (end - start + 1) * self.bytesPerSector,
						'type': partId,
						'fs': fs,
						'boot': boot,
						'lba': lba
					}
				)
			else:
				logger.info(u"Creating partition on '%s': number: %s, type '%s', filesystem '%s', start: %s cyl, end: %s cyl." \
							% (self.device, number, type, fs, start, end))

				if number < 1 or number > 4:
					raise Exception(u'Cannot create partition %s' % number)

				self.partitions.append(
					{
						'number': number,
						'cylStart': start,
						'cylEnd': end,
						'cylSize': end - start + 1,
						'start': start * self.bytesPerCylinder,
						'end': end * self.bytesPerCylinder,
						'size': (end - start + 1) * self.bytesPerCylinder,
						'type': partId,
						'fs': fs,
						'boot': boot,
						'lba': lba
					}
				)

			self.writePartitionTable()
			self.readPartitionTable()
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_createPartition(self, start, end, fs, type, boot, lba, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_createPartition(self, start, end, fs, type, boot, lba)

	def deletePartition(self, partition):
		for hook in hooks:
			partition = hook.pre_Harddisk_deletePartition(self, partition)
		try:
			partition = forceInt(partition)

			logger.info("Deleting partition '%s' on '%s'" % (partition, self.device))

			partitions = []
			exists = False
			deleteDev = None
			for part in self.partitions:
				if part.get('number') == partition:
					exists = True
					deleteDev = part.get('device')
				else:
					partitions.append(part)

			if not exists:
				logger.warning(u"Cannot delete non existing partition '%s'." % partition)
				return

			self.partitions = partitions

			self.writePartitionTable()
			self.readPartitionTable()
			if deleteDev:
				logger.debug(u"Waiting for device '%s' to disappear" % deleteDev)
				timeout = 5
				while timeout > 0:
					if not os.path.exists(deleteDev):
						break
					time.sleep(1)
					timeout -= 1
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_deletePartition(self, partition, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_deletePartition(self, partition)

	def mountPartition(self, partition, mountpoint, **options):
		for hook in hooks:
			(partition, mountpoint, options) = hook.pre_Harddisk_mountPartition(self, partition, mountpoint, **options)
		try:
			partition = forceInt(partition)
			mountpoint = forceFilename(mountpoint)
			mount(self.getPartition(partition)['device'], mountpoint, **options)
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_mountPartition(self, partition, mountpoint, e, **options)
			raise

		for hook in hooks:
			hook.post_Harddisk_mountPartition(self, partition, mountpoint, **options)

	def umountPartition(self, partition):
		for hook in hooks:
			partition = hook.pre_Harddisk_umountPartition(self, partition)
		try:
			partition = forceInt(partition)
			umount(self.getPartition(partition)['device'])
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_umountPartition(self, partition, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_umountPartition(self, partition)

	def createFilesystem(self, partition, fs=None):
		for hook in hooks:
			(partition, fs) = hook.pre_Harddisk_createFilesystem(self, partition, fs)

		try:
			partition = forceInt(partition)
			if not fs:
				fs = self.getPartition(partition)['fs']
			fs = forceUnicodeLower(fs)

			if fs not in (u'fat32', u'ntfs', u'linux-swap', u'ext2', u'ext3', u'ext4', u'reiserfs', u'reiser4', u'xfs'):
				raise Exception(u"Creation of filesystem '%s' not supported!" % fs)

			logger.info(u"Creating filesystem '%s' on '%s'." % (fs, self.getPartition(partition)['device']))

			retries = 1
			while retries <= 6:
				if os.path.exists(self.getPartition(partition)['device']):
					break
				retries += 1
				if retries == 3:
					logger.debug(u"Forcing kernel to reread the partitiontable again")
					self._forceReReadPartionTable()
				time.sleep(2)

			if fs == u'fat32':
				cmd = u"mkfs.vfat -F 32 %s" % self.getPartition(partition)['device']
			elif fs == u'linux-swap':
				cmd = u"mkswap %s" % self.getPartition(partition)['device']
			else:
				options = u''
				if fs in (u'ext2', u'ext3', u'ext4', u'ntfs'):
					options = u'-F'
					if fs == u'ntfs':
						# quick format
						options += u' -Q'
				elif fs in (u'xfs', u'reiserfs', u'reiser4'):
					options = u'-f'
				cmd = u"mkfs.%s %s %s" % (fs, options, self.getPartition(partition)['device'])

			if self.ldPreload:
				os.putenv("LD_PRELOAD", self.ldPreload)
			execute(cmd)
			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")
			self.readPartitionTable()
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_createFilesystem(self, partition, fs, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_createFilesystem(self, partition, fs)

	def resizeFilesystem(self, partition, size=0, fs=None):
		for hook in hooks:
			(partition, size, fs) = hook.pre_Harddisk_resizeFilesystem(self, partition, size, fs)
		try:
			partition = forceInt(partition)
			size = forceInt(size)
			bytesPerSector = forceInt(self.bytesPerSector)
			if not fs:
				fs = self.getPartition(partition)['fs']
			fs = forceUnicodeLower(fs)
			if fs not in (u'ntfs',):
				raise Exception(u"Resizing of filesystem '%s' not supported!" % fs)

			if size <= 0:
				if bytesPerSector > 0 and self.blockAlignment:
					size = self.getPartition(partition)['secSize'] * bytesPerSector
				else:
					size = self.getPartition(partition)['size'] - 10*1024*1024

			if size <= 0:
				raise Exception(u"New filesystem size of %0.2f MB is not possible!" % (float(size)/(1024*1024)))

			if self.ldPreload:
				os.putenv("LD_PRELOAD", self.ldPreload)

			if fs.lower() == 'ntfs':
				cmd = u"echo 'y' | %s --force --size %s %s" % (which('ntfsresize'), size, self.getPartition(partition)['device'])
				execute(cmd)

			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_resizeFilesystem(self, partition, size, fs, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_resizeFilesystem(self, partition, size, fs)

	def saveImage(self, partition, imageFile, progressSubject=None):
		for hook in hooks:
			(partition, imageFile, progressSubject) = hook.pre_Harddisk_saveImage(self, partition, imageFile, progressSubject)

		saveImageResult = {'TotalTime': 'n/a', 'AveRate': 'n/a', 'AveUnit': 'n/a'}

		try:
			partition = forceInt(partition)
			imageFile = forceUnicode(imageFile)

			part = self.getPartition(partition)
			if not part:
				raise Exception(u'Partition %s does not exist' % partition)

			if self.ldPreload:
				os.putenv("LD_PRELOAD", self.ldPreload)

			pipe = u''
			if imageFile.startswith(u'|'):
				pipe = imageFile
				imageFile = u'-'

			logger.info(u"Saving partition '%s' to partclone image '%s'" % (part['device'], imageFile))

			# "-f" will write images of "dirty" volumes too
			# Better run chkdsk under windows before saving image!
			cmd = u'%s --rescue --clone --force --source %s --overwrite %s %s' % (which('partclone.' + part['fs']), part['device'], imageFile, pipe)

			if progressSubject:
				progressSubject.setEnd(100)

			handle = execute(cmd, getHandle=True)
			done = False

			timeout = 0
			buf = [u'']
			lastMsg = u''
			started = False
			while not done:
				inp = handle.read(128)

				if inp:
					inp = inp.decode("latin-1")
					timeout = 0

					b = inp.splitlines()
					if inp.endswith((u'\n', u'\r')):
						b.append(u'')

					buf = [buf[-1] + b[0]] + b[1:]

					for currentBuffer in islice(buf, len(buf) - 1):
						try:
							logger.debug(u" -->>> %s" % currentBuffer)
						except Exception:
							pass

						if u'Partclone fail' in currentBuffer:
							raise Exception(u"Failed: %s" % '\n'.join(buf))
						if u'Partclone successfully' in currentBuffer:
							done = True
						if u'Total Time' in currentBuffer:
							match = re.search('Total\sTime:\s(\d+:\d+:\d+),\sAve.\sRate:\s*(\d*.\d*)([GgMm]B/min)', currentBuffer)
							if match:
								rate = match.group(2)
								unit = match.group(3)
								if unit.startswith(("G", "g")):
									rate = float(rate) * 1024
									unit = 'MB/min'
								saveImageResult = {
									'TotalTime': match.group(1),
									'AveRate': str(rate),
									'AveUnit': unit
								}

						if not started:
							if u'Calculating bitmap' in currentBuffer:
								logger.info(u"Save image: Scanning filesystem")
								if progressSubject:
									progressSubject.setMessage(u"Scanning filesystem")
							elif currentBuffer.count(':') == 1 and 'http:' not in currentBuffer:
								(k, v) = currentBuffer.split(':')
								k = k.strip()
								v = v.strip()
								logger.info(u"Save image: %s: %s" % (k, v))
								if progressSubject:
									progressSubject.setMessage(u"%s: %s" % (k, v))
								if 'used' in k.lower():
									if progressSubject:
										progressSubject.setMessage(u"Creating image")
									started = True
									continue
						else:
							match = re.search('Completed:\s*([\d\.]+)%', currentBuffer)
							if match:
								percent = int("%0.f" % float(match.group(1)))
								if progressSubject and percent != progressSubject.getState():
									logger.debug(u" -->>> %s" % currentBuffer)
									progressSubject.setState(percent)

					lastMsg = buf[-2]
					buf[:-1] = []
				elif timeout >= 100:
					raise Exception(u"Failed: %s" % lastMsg)
				else:
					timeout += 1
					continue

			time.sleep(3)
			if handle:
				handle.close()

			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")
		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_saveImage(self, partition, imageFile, progressSubject, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_saveImage(self, partition, imageFile, progressSubject)

		return saveImageResult

	def restoreImage(self, partition, imageFile, progressSubject=None):
		for hook in hooks:
			(partition, imageFile, progressSubject) = hook.pre_Harddisk_restoreImage(self, partition, imageFile, progressSubject)

		try:
			partition = forceInt(partition)
			imageFile = forceUnicode(imageFile)

			imageType = None
			fs = None

			pipe = u''
			if imageFile.endswith(u'|'):
				pipe = imageFile
				imageFile = u'-'

			try:
				head = u''
				if pipe:
					proc = subprocess.Popen(
						pipe[:-1] + u" 2>/dev/null",
						shell=True,
						stdin=subprocess.PIPE,
						stdout=subprocess.PIPE,
						stderr=None,
					)
					pid = proc.pid

					head = proc.stdout.read(128)
					logger.debug(u"Read 128 Bytes from pipe '%s': %s" % (pipe, head.decode('ascii', 'replace')))

					proc.stdout.close()
					proc.stdin.close()

					while proc.poll() is None:
						pids = os.listdir("/proc")
						for p in pids:
							if not os.path.exists(os.path.join("/proc", p, "status")):
								continue
							with open(os.path.join("/proc", p, "status")) as f:
								for line in f:
									if line.startswith("PPid:"):
										ppid = line.split()[1].strip()
										if ppid == str(pid):
											logger.info(u"Killing process %s" % p)
											os.kill(int(p), SIGKILL)

						logger.info(u"Killing process %s" % pid)
						os.kill(pid, SIGKILL)
						time.sleep(1)
				else:
					with open(imageFile, 'r') as image:
						head = image.read(128)
						logger.debug(u"Read 128 Bytes from file '%s': %s" % (imageFile, head.decode('ascii', 'replace')))

				if 'ntfsclone-image' in head:
					logger.notice(u"Image type is ntfsclone")
					imageType = u'ntfsclone'
				elif 'partclone-image' in head:
					logger.notice(u"Image type is partclone")
					imageType = u'partclone'
			except Exception:
				raise

			if imageType not in (u'ntfsclone', u'partclone'):
				raise Exception(u"Unknown image type.")

			if self.ldPreload:
				os.putenv("LD_PRELOAD", self.ldPreload)

			if imageType == u'partclone':
				logger.info(u"Restoring partclone image '%s' to '%s'" % \
							(imageFile, self.getPartition(partition)['device']))

				cmd = u'%s %s --source %s --overwrite %s' % \
								(pipe, which('partclone.restore'), imageFile, self.getPartition(partition)['device'])

				if progressSubject:
					progressSubject.setEnd(100)
					progressSubject.setMessage(u"Scanning image")

				handle = execute(cmd, getHandle=True)
				done = False

				timeout = 0
				buf = [u'']
				lastMsg = u''
				started = False
				while not done:
					inp = handle.read(128)

					if inp:
						inp = inp.decode("latin-1")
						timeout = 0

						b = inp.splitlines()
						if inp.endswith((u'\n', u'\r')):
							b.append(u'')

						buf = [buf[-1] + b[0]] + b[1:]

						for currentBuffer in islice(buf, len(buf) - 1):
							try:
								logger.debug(u" -->>> %s" % currentBuffer)
							except Exception:
								pass

							if u'Partclone fail' in currentBuffer:
								raise Exception(u"Failed: %s" % '\n'.join(buf))
							if u'Partclone successfully' in currentBuffer:
								done = True
							if not started:
								if currentBuffer.count(':') == 1 and 'http:' in currentBuffer:
									(k, v) = currentBuffer.split(':')
									k = k.strip()
									v = v.strip()
									logger.info(u"Save image: %s: %s" % (k, v))
									if progressSubject:
										progressSubject.setMessage(u"%s: %s" % (k, v))
									if 'file system' in k.lower():
										fs = v.lower()
									elif 'used' in k.lower():
										if progressSubject:
											progressSubject.setMessage(u"Restoring image")
										started = True
										continue
							else:
								match = re.search('Completed:\s*([\d\.]+)%', currentBuffer)
								if match:
									percent = int("%0.f" % float(match.group(1)))
									if progressSubject and percent != progressSubject.getState():
										logger.debug(u" -->>> %s" % currentBuffer)
										progressSubject.setState(percent)

						lastMsg = buf[-2]
						buf[:-1] = []

					elif timeout >= 100:
						if progressSubject:
							progressSubject.setMessage(u"Failed: %s" % lastMsg)
						raise Exception(u"Failed: %s" % lastMsg)
					else:
						timeout += 1
						continue

				time.sleep(3)
				if handle:
					handle.close()
			else:
				fs = 'ntfs'
				logger.info(u"Restoring ntfsclone-image '%s' to '%s'" % \
							(imageFile, self.getPartition(partition)['device']))

				cmd = u'%s %s --restore-image --overwrite %s %s' % \
								(pipe, which('ntfsclone'), self.getPartition(partition)['device'], imageFile)

				if progressSubject:
					progressSubject.setEnd(100)
					progressSubject.setMessage(u"Restoring image")

				handle = execute(cmd, getHandle=True)
				done = False

				timeout = 0
				buf = [u'']
				lastMsg = u''
				while not done:
					inp = handle.read(128)

					if inp:
						inp = inp.decode("latin-1")
						timeout = 0

						b = inp.splitlines()
						if inp.endswith((u'\n', u'\r')):
							b.append(u'')

						buf = [buf[-1] + b[0]] + b[1:]

						for currentBuffer in islice(buf, len(buf) - 1):
							if 'Syncing' in currentBuffer:
								logger.info(u"Restore image: Syncing")
								if progressSubject:
									progressSubject.setMessage(u"Syncing")
								done = True
							match = re.search('\s(\d+)[\.\,]\d\d\spercent', currentBuffer)
							if match:
								percent = int(match.group(1))
								if progressSubject and percent != progressSubject.getState():
									logger.debug(u" -->>> %s" % currentBuffer)
									progressSubject.setState(percent)
							else:
								logger.debug(u" -->>> %s" % currentBuffer)

						lastMsg = buf[-2]
						buf[:-1] = []
					elif timeout >= 100:
						if progressSubject:
							progressSubject.setMessage(u"Failed: %s" % lastMsg)
						raise Exception(u"Failed: %s" % lastMsg)
					else:
						timeout += 1
						continue

				time.sleep(3)
				if handle:
					handle.close()

			if fs == 'ntfs':
				self.setNTFSPartitionStartSector(partition)
				if progressSubject:
					progressSubject.setMessage(u"Resizing filesystem to partition size")
				self.resizeFilesystem(partition, fs=u'ntfs')

			if self.ldPreload:
				os.unsetenv("LD_PRELOAD")

		except Exception as e:
			for hook in hooks:
				hook.error_Harddisk_restoreImage(self, partition, imageFile, progressSubject, e)
			raise

		for hook in hooks:
			hook.post_Harddisk_restoreImage(self, partition, imageFile, progressSubject)


def isCentOS():
	"""
	Returns `True` if this is running on CentOS.
	Returns `False` if otherwise.
	"""
	return _checkForDistribution('CentOS')


def isDebian():
	"""
	Returns `True` if this is running on Debian.
	Returns `False` if otherwise.
	"""
	return _checkForDistribution('Debian')


def isOpenSUSE():
	"""
	Returns `True` if this is running on openSUSE.
	Returns `False` if otherwise.
	For OpenSUSE Leap please use isOpenSUSELeap()
	"""
	return _checkForDistribution('opensuse')


def isOpenSUSELeap():
	"""
	Returns `True` if this is running on OpenSUSE Leap.
	Returns `False` if otherwise.
	"""
	if isOpenSUSE():
		leap = Distribution()
		if leap.version >= (42, 1):
			return True

	return False


def isRHEL():
	"""
	Returns `True` if this is running on Red Hat Enterprise Linux.
	Returns `False` if otherwise.
	"""
	return _checkForDistribution('Red Hat Enterprise Linux')


def isSLES():
	"""
	Returns `True` if this is running on Suse Linux Enterprise Server.
	Returns `False` if otherwise.
	"""
	return _checkForDistribution('suse linux enterprise server')


def isUbuntu():
	"""
	Returns `True` if this is running on Ubuntu.
	Returns `False` if otherwise.
	"""
	return _checkForDistribution('Ubuntu')


def isUCS():
	"""
	Returns `True` if this is running on Univention Corporate Server.
	Returns `False` if otherwise.
	"""
	return (_checkForDistribution('Univention')
			or u'univention' in Distribution().distributor.lower())


def _checkForDistribution(name):
	try:
		sysinfo = SysInfo()
		return name.lower() in sysinfo.distribution.lower()
	except Exception as error:
		logger.debug("Failed to check for Distribution: {0}", error)
		return False


class Distribution(object):

	def __init__(self, distribution_information=None):
		if distribution_information is None:
			distribution_information = platform.linux_distribution()

		self.distribution, self._version, self.id = distribution_information
		self.distribution = self.distribution.strip()

		osType, self.hostname, self.kernel, self.detailedVersion, self.arch, processor = platform.uname()

		self.distributor = self._getDistributor()

	@property
	def version(self):
		if 'errata' in self._version:
			version = self._version.strip('"').split("-")[0]
			return tuple([int(x) for x in version.split('.')])
		else:
			return tuple([int(x) for x in self._version.split(".")])

	@staticmethod
	def _getDistributor():
		"""
		Get information about the distributor.

		Returns an empty string if no information can be obtained.
		"""
		try:
			lsbReleaseOutput = execute('lsb_release -i')
			distributor = lsbReleaseOutput[0].split(':')[1].strip()
		except Exception:
			distributor = ''

		return distributor

	def __str__(self):
		return ("%s %s %s" % (self.distribution, self._version, self.id)).strip()

	def __unicode__(self):
		return unicode(self.__str__())

	def __repr__(self):
		return (u"Distribution(distribution_information=({distro!r}, "
				"{version!r}, {id!r}))".format(
					distro=self.distribution,
					version=self._version,
					id=self.id
					)
				)


class SysInfo(object):

	def __init__(self):
		self.dist = Distribution()

	@property
	def hostname(self):
		return forceHostname(socket.gethostname().split(".")[0])

	@property
	def fqdn(self):
		return forceUnicodeLower(socket.getfqdn())

	@property
	def domainname(self):
		return forceDomain(".".join(self.fqdn.split(".")[1:]))

	@property
	def distribution(self):
		return self.dist.distribution

	@property
	def sysVersion(self):
		return self.dist.version

	@property
	def distributionId(self):
		return self.dist.id

	@property
	def ipAddress(self):
		return forceIPAddress(socket.gethostbyname(self.hostname))

	@property
	def hardwareAddress(self):
		for device in getEthernetDevices():
			devconf = getNetworkDeviceConfig(device)
			if devconf['ipAddress'] and not devconf['ipAddress'].startswith(('127', '169')):
				if self.ipAddress == devconf['ipAddress']:
					return forceHardwareAddress(devconf['hardwareAddress'])
		return None

	@property
	def netmask(self):
		for device in getEthernetDevices():
			devconf = getNetworkDeviceConfig(device)
			if devconf['ipAddress'] and not devconf['ipAddress'].startswith(('127', '169')):
				if self.ipAddress == devconf['ipAddress']:
					return forceNetmask(devconf['netmask'])
		return u'255.255.255.0'

	@property
	def broadcast(self):
		return u".".join(u"%d" % (int(self.ipAddress.split(u'.')[i]) | int(self.netmask.split(u'.')[i]) ^ 255) for i in range(len(self.ipAddress.split('.'))))

	@property
	def subnet(self):
		return u".".join(u"%d" % (int(self.ipAddress.split(u'.')[i]) & int(self.netmask.split(u'.')[i])) for i in range(len(self.ipAddress.split('.'))))

	@property
	def opsiVersion(self):
		try:
			with open("/etc/opsi/version") as versionFile:
				version = versionFile.read()

			return version.strip()
		except Exception:
			raise OpsiVersionError("Unable to determine opsi version")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                       HARDWARE INVENTORY                                          -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def auditHardware(config, hostId, progressSubject=None):
	for hook in hooks:
		(config, hostId, progressSubject) = hook.pre_auditHardware(config, hostId, progressSubject)

	try:
		hostId = forceHostId(hostId)

		AuditHardwareOnHost.setHardwareConfig(config)
		auditHardwareOnHosts = []

		info = hardwareInventory(config)
		info = hardwareExtendedInventory(config, info)
		for (hardwareClass, devices) in info.items():
			if hardwareClass == 'SCANPROPERTIES':
				continue
			for device in devices:
				data = {'hardwareClass': hardwareClass}
				for (attribute, value) in device.items():
					data[str(attribute)] = value
				data['hostId'] = hostId
				auditHardwareOnHosts.append(AuditHardwareOnHost.fromHash(data))
	except Exception as e:
		for hook in hooks:
			hook.error_auditHardware(config, hostId, progressSubject, e)
		raise

	for hook in hooks:
		auditHardwareOnHosts = hook.post_auditHardware(config, hostId, auditHardwareOnHosts)

	return auditHardwareOnHosts


def hardwareExtendedInventory(config, opsiValues={}, progressSubject=None):
	if not config:
		logger.error(u"hardwareInventory: no config given")
		return {}

	for hwClass in config:
		if not hwClass.get('Class') or not hwClass['Class'].get('Opsi'):
			continue

		opsiName = hwClass['Class']['Opsi']

		logger.debug(u"Processing class '%s'" % (opsiName))

		valuesregex = re.compile("(.*)#(.*)#")
		for item in hwClass['Values']:
			pythonline = item.get('Python')
			if not pythonline:
				continue
			condition = item.get("Condition")
			if condition:
				val = condition.split("=")[0]
				r = condition.split("=")[1]
				if val and r:
					conditionregex = re.compile(r)
					conditionmatch = None

					logger.info("Condition found, try to check the Condition")
					for currentValue in opsiValues[opsiName]:
						value = currentValue.get(val, "")
						if value:
							conditionmatch = re.search(conditionregex, value)
							break

					if not value:
						logger.warning("The Value of your condition '%s' doesn't exists, please check your opsihwaudit.conf." % condition)

					if not conditionmatch:
						continue
				match = re.search(valuesregex, pythonline)
				if match:
					result = None
					srcfields = match.group(2)
					fieldsdict = eval(srcfields)
					attr = ''
					for (key, value) in fieldsdict.items():
						for i in range(len(opsiValues.get(key, []))):
							attr = opsiValues.get(key)[i].get(value, '')
						if attr:
							break
					if attr:
						pythonline = pythonline.replace("#%s#" % srcfields, "'%s'" % attr)
						result = eval(pythonline)

					if isinstance(result, unicode):
						result = result.encode('utf-8')
					if opsiName not in opsiValues:
						opsiValues[opsiName].append({})
					for i in range(len(opsiValues[opsiName])):
						opsiValues[opsiName][i][item['Opsi']] = result

	return opsiValues


def hardwareInventory(config, progressSubject=None):
	import xml.dom.minidom

	if not config:
		logger.error(u"hardwareInventory: no config given")
		return {}

	opsiValues = {}

	def getAttribute(dom, tagname, attrname):
		nodelist = dom.getElementsByTagName(tagname)
		if nodelist:
			return nodelist[0].getAttribute(attrname).strip()
		else:
			return u""

	def getElementsByAttributeValue(dom, tagName, attributeName, attributeValue):
		return [element for element in dom.getElementsByTagName(tagName) if re.search(attributeValue, element.getAttribute(attributeName))]

	# Read output from lshw
	xmlOut = u'\n'.join(execute(u"%s -xml 2>/dev/null" % which("lshw")))
	xmlOut = re.sub('[%c%c%c%c%c%c%c%c%c%c%c%c%c]' % (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0xbd, 0xbf, 0xef, 0xdd), u'.', xmlOut)
	dom = xml.dom.minidom.parseString(xmlOut.encode('utf-8'))

	# Read output from lspci
	lspci = {}
	busId = None
	devRegex = re.compile('([\d\.:a-f]+)\s+([\da-f]+):\s+([\da-f]+):([\da-f]+)\s*(\(rev ([^\)]+)\)|)')
	subRegex = re.compile('\s*Subsystem:\s+([\da-f]+):([\da-f]+)\s*')
	for line in execute(u"%s -vn" % which("lspci")):
		if not line.strip():
			continue
		match = re.search(devRegex, line)
		if match:
			busId = match.group(1)
			lspci[busId] = {
				'vendorId': forceHardwareVendorId(match.group(3)),
				'deviceId': forceHardwareDeviceId(match.group(4)),
				'subsystemVendorId': '',
				'subsystemDeviceId': '',
				'revision': match.group(6) or ''
			}
			continue
		match = re.search(subRegex, line)
		if match:
			lspci[busId]['subsystemVendorId'] = forceHardwareVendorId(match.group(1))
			lspci[busId]['subsystemDeviceId'] = forceHardwareDeviceId(match.group(2))
	logger.debug2(u"Parsed lspci info:")
	logger.debug2(objectToBeautifiedText(lspci))

	# Read hdaudio information from alsa
	hdaudio = {}
	if os.path.exists('/proc/asound'):
		for card in os.listdir('/proc/asound'):
			if not re.search('^card\d$', card):
				continue
			logger.debug(u"Found hdaudio card '%s'" % card)
			for codec in os.listdir('/proc/asound/' + card):
				if not re.search('^codec#\d$', codec):
					continue
				if not os.path.isfile('/proc/asound/' + card + '/' + codec):
					continue
				with open('/proc/asound/' + card + '/' + codec) as f:
					logger.debug(u"   Found hdaudio codec '%s'" % codec)
					hdaudioId = card + codec
					hdaudio[hdaudioId] = {}
					for line in f:
						if line.startswith(u'Codec:'):
							hdaudio[hdaudioId]['codec'] = line.split(':', 1)[1].strip()
						elif line.startswith(u'Address:'):
							hdaudio[hdaudioId]['address'] = line.split(':', 1)[1].strip()
						elif line.startswith(u'Vendor Id:'):
							vid = line.split('x', 1)[1].strip()
							hdaudio[hdaudioId]['vendorId'] = forceHardwareVendorId(vid[0:4])
							hdaudio[hdaudioId]['deviceId'] = forceHardwareDeviceId(vid[4:8])
						elif line.startswith(u'Subsystem Id:'):
							sid = line.split('x', 1)[1].strip()
							hdaudio[hdaudioId]['subsystemVendorId'] = forceHardwareVendorId(sid[0:4])
							hdaudio[hdaudioId]['subsystemDeviceId'] = forceHardwareDeviceId(sid[4:8])
						elif line.startswith(u'Revision Id:'):
							hdaudio[hdaudioId]['revision'] = line.split('x', 1)[1].strip()
				logger.debug(u"      Codec info: '%s'" % hdaudio[hdaudioId])

	# Read output from lsusb
	lsusb = {}
	busId = None
	devId = None
	indent = -1
	currentKey = None
	status = False

	devRegex = re.compile('^Bus\s+(\d+)\s+Device\s+(\d+)\:\s+ID\s+([\da-fA-F]{4})\:([\da-fA-F]{4})\s*(.*)$')
	descriptorRegex = re.compile('^(\s*)(.*)\s+Descriptor\:\s*$')
	deviceStatusRegex = re.compile('^(\s*)Device\s+Status\:\s+(\S+)\s*$')
	deviceQualifierRegex = re.compile('^(\s*)Device\s+Qualifier\s+.*\:\s*$')
	keyRegex = re.compile('^(\s*)([^\:]+)\:\s*$')
	keyValueRegex = re.compile('^(\s*)(\S+)\s+(.*)$')

	try:
		for line in execute(u"%s -v" % which("lsusb")):
			if not line.strip() or (line.find(u'** UNAVAILABLE **') != -1):
				continue
			# line = line.decode('ISO-8859-15', 'replace').encode('utf-8', 'replace')
			match = re.search(devRegex, line)
			if match:
				busId = str(match.group(1))
				devId = str(match.group(2))
				descriptor = None
				indent = -1
				currentKey = None
				status = False
				logger.debug(u"Device: %s:%s" % (busId, devId))
				# TODO: better key building.
				lsusb[busId + ":" + devId] = {
					'device': {},
					'configuration': {},
					'interface': {},
					'endpoint': [],
					'hid device': {},
					'hub': {},
					'qualifier': {},
					'status': {}
				}
				continue

			if status:
				lsusb[busId + ":" + devId]['status'].append(line.strip())
				continue

			match = re.search(deviceStatusRegex, line)
			if match:
				status = True
				lsusb[busId + ":" + devId]['status'] = [match.group(2)]
				continue

			match = re.search(deviceQualifierRegex, line)
			if match:
				descriptor = 'qualifier'
				logger.debug(u"Qualifier")
				currentKey = None
				indent = -1
				continue

			match = re.search(descriptorRegex, line)
			if match:
				descriptor = match.group(2).strip().lower()
				logger.debug(u"Descriptor: %s" % descriptor)
				if isinstance(lsusb[busId + ":" + devId][descriptor], list):
					lsusb[busId + ":" + devId][descriptor].append({})
				currentKey = None
				indent = -1
				continue

			if not descriptor:
				logger.error(u"No descriptor")
				continue

			if descriptor not in lsusb[busId + ":" + devId]:
				logger.error(u"Unknown descriptor '%s'" % descriptor)
				continue

			(key, value) = ('', '')
			match = re.search(keyRegex, line)
			if match:
				key = match.group(2)
				indent = len(match.group(1))
			else:
				match = re.search(keyValueRegex, line)
				if match:
					if indent >= 0 and len(match.group(1)) > indent:
						key = currentKey
						value = match.group(0).strip()
					else:
						(key, value) = (match.group(2), match.group(3).strip())
						indent = len(match.group(1))

			logger.debug(u"key: '%s', value: '%s'" % (key, value))

			if not key or not value:
				continue

			currentKey = key
			if isinstance(lsusb[busId + ":" + devId][descriptor], list):
				if key not in lsusb[busId + ":" + devId][descriptor][-1]:
					lsusb[busId + ":" + devId][descriptor][-1][key] = []
				lsusb[busId + ":" + devId][descriptor][-1][key].append(value)
			else:
				if key not in lsusb[busId + ":" + devId][descriptor]:
					lsusb[busId + ":" + devId][descriptor][key] = []
				lsusb[busId + ":" + devId][descriptor][key].append(value)

		logger.debug2(u"Parsed lsusb info:")
		logger.debug2(objectToBeautifiedText(lsusb))
	except Exception as e:
		logger.error(e)

	# Read output from dmidecode
	dmidecode = {}
	dmiType = None
	header = True
	option = None
	optRegex = re.compile('(\s+)([^:]+):(.*)')
	for line in execute(which("dmidecode")):
		try:
			if not line.strip():
				continue
			if line.startswith(u'Handle'):
				dmiType = None
				header = False
				option = None
				continue
			if header:
				continue
			if not dmiType:
				dmiType = line.strip()
				if dmiType.lower() == u'end of table':
					break
				if dmiType not in dmidecode:
					dmidecode[dmiType] = []
				dmidecode[dmiType].append({})
			else:
				match = re.search(optRegex, line)
				if match:
					option = match.group(2).strip()
					value = match.group(3).strip()
					dmidecode[dmiType][-1][option] = removeUnit(value)
				elif option:
					if not isinstance(dmidecode[dmiType][-1][option], list):
						if dmidecode[dmiType][-1][option]:
							dmidecode[dmiType][-1][option] = [dmidecode[dmiType][-1][option]]
						else:
							dmidecode[dmiType][-1][option] = []
					dmidecode[dmiType][-1][option].append(removeUnit(line.strip()))
		except Exception as e:
			logger.error(u"Error while parsing dmidecode output '%s': %s" % (line.strip(), e))
	logger.debug2(u"Parsed dmidecode info:")
	logger.debug2(objectToBeautifiedText(dmidecode))

	# Build hw info structure
	for hwClass in config:
		if not hwClass.get('Class') or not hwClass['Class'].get('Opsi') or not hwClass['Class'].get('Linux'):
			continue

		opsiClass = hwClass['Class']['Opsi']
		linuxClass = hwClass['Class']['Linux']

		logger.debug(u"Processing class '%s' : '%s'" % (opsiClass, linuxClass))

		if linuxClass.startswith('[lshw]'):
			# Get matching xml nodes
			devices = []
			for hwclass in linuxClass[6:].split('|'):
				hwid = ''
				filter = None
				if ':' in hwclass:
					(hwclass, hwid) = hwclass.split(':', 1)
					if ':' in hwid:
						(hwid, filter) = hwid.split(':', 1)

				logger.debug(u"Class is '%s', id is '%s', filter is: %s" % (hwClass, hwid, filter))

				devs = getElementsByAttributeValue(dom, 'node', 'class', hwclass)
				for dev in devs:
					if dev.hasChildNodes():
						for child in dev.childNodes:
							if child.nodeName == "businfo":
								busInfo = child.firstChild.data.strip()
								if busInfo.startswith('pci@'):
									logger.debug(u"Getting pci bus info for '%s'" % busInfo)
									pciBusId = busInfo.split('@')[1]
									if pciBusId.startswith('0000:'):
										pciBusId = pciBusId[5:]
									pciInfo = lspci.get(pciBusId, {})
									for (key, value) in pciInfo.items():
										elem = dom.createElement(key)
										elem.childNodes.append(dom.createTextNode(value))
										dev.childNodes.append(elem)
								break
				if hwid:
					filtered = []
					for dev in devs:
						if re.search(hwid, dev.getAttribute('id')):
							if not filter:
								filtered.append(dev)
							else:
								(attr, method) = filter.split('.', 1)
								if dev.getAttribute(attr):
									if eval("dev.getAttribute(attr).%s" % method):
										filtered.append(dev)
								elif dev.hasChildNodes():
									for child in dev.childNodes:
										if (child.nodeName == attr) and child.hasChildNodes():
											if eval("child.firstChild.data.strip().%s" % method):
												filtered.append(dev)
												break
										try:
											if child.hasAttributes() and child.getAttribute(attr):
												if eval("child.getAttribute(attr).%s" % method):
													filtered.append(dev)
													break
										except Exception:
											pass
					devs = filtered

				logger.debug2("Found matching devices: %s" % devs)
				devices.extend(devs)

			# Process matching xml nodes
			for i in range(len(devices)):
				if opsiClass not in opsiValues:
					opsiValues[opsiClass] = []
				opsiValues[opsiClass].append({})

				if not hwClass.get('Values'):
					break

				for attribute in hwClass['Values']:
					elements = [devices[i]]
					if not attribute.get('Opsi') or not attribute.get('Linux'):
						continue

					logger.debug2(u"Processing attribute '%s' : '%s'" % (attribute['Linux'], attribute['Opsi']))
					for attr in attribute['Linux'].split('||'):
						attr = attr.strip()
						method = None
						data = None
						for part in attr.split('/'):
							if '.' in part:
								(part, method) = part.split('.', 1)
							nextElements = []
							for element in elements:
								for child in element.childNodes:
									try:
										if child.nodeName == part:
											nextElements.append(child)
										elif child.hasAttributes() and (child.getAttribute('class') == part or child.getAttribute('id').split(':')[0] == part):
											nextElements.append(child)
									except Exception:
										pass
							if not nextElements:
								logger.warning(u"Attribute part '%s' not found" % part)
								break
							elements = nextElements

						if not data:
							if not elements:
								opsiValues[opsiClass][i][attribute['Opsi']] = ''
								logger.warning(u"No data found for attribute '%s' : '%s'" % (attribute['Linux'], attribute['Opsi']))
								continue

							for element in elements:
								if element.getAttribute(attr):
									data = element.getAttribute(attr).strip()
								elif element.getAttribute('value'):
									data = element.getAttribute('value').strip()
								elif element.hasChildNodes():
									data = element.firstChild.data.strip()
						if method and data:
							try:
								logger.debug(u"Eval: %s.%s" % (data, method))
								data = eval("data.%s" % method)
							except Exception as e:
								logger.error(u"Failed to excecute '%s.%s': %s" % (data, method, e))
						logger.debug2(u"Data: %s" % data)
						opsiValues[opsiClass][i][attribute['Opsi']] = data
						if data:
							break

		# Get hw info from dmidecode
		elif linuxClass.startswith('[dmidecode]'):
			opsiValues[opsiClass] = []
			for hwclass in linuxClass[11:].split('|'):
				(filterAttr, filterExp) = (None, None)
				if ':' in hwclass:
					(hwclass, filter) = hwclass.split(':', 1)
					if '.' in filter:
						(filterAttr, filterExp) = filter.split('.', 1)

				for dev in dmidecode.get(hwclass, []):
					if filterAttr and dev.get(filterAttr) and not eval("str(dev.get(filterAttr)).%s" % filterExp):
						continue
					device = {}
					for attribute in hwClass['Values']:
						if not attribute.get('Linux'):
							continue

						for aname in attribute['Linux'].split('||'):
							aname = aname.strip()
							method = None
							if '.' in aname:
								(aname, method) = aname.split('.', 1)
							if method:
								try:
									logger.debug(u"Eval: %s.%s" % (dev.get(aname, ''), method))
									device[attribute['Opsi']] = eval("dev.get(aname, '').%s" % method)
								except Exception as e:
									device[attribute['Opsi']] = u''
									logger.error(u"Failed to excecute '%s.%s': %s" % (dev.get(aname, ''), method, e))
							else:
								device[attribute['Opsi']] = dev.get(aname)
							if device[attribute['Opsi']]:
								break
					opsiValues[hwClass['Class']['Opsi']].append(device)

		# Get hw info from alsa hdaudio info
		elif linuxClass.startswith('[hdaudio]'):
			opsiValues[opsiClass] = []
			for (hdaudioId, dev) in hdaudio.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux') or attribute['Linux'] not in dev:
						continue

					try:
						device[attribute['Opsi']] = dev[attribute['Linux']]
					except Exception as e:
						logger.warning(e)
						device[attribute['Opsi']] = u''
				opsiValues[opsiClass].append(device)

		# Get hw info from lsusb
		elif linuxClass.startswith('[lsusb]'):
			opsiValues[opsiClass] = []
			for (busId, dev) in lsusb.items():
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('Linux'):
						continue

					try:
						value = pycopy.deepcopy(dev)
						for key in attribute['Linux'].split('/'):
							method = None
							if '.' in key:
								(key, method) = key.split('.', 1)
							if not isinstance(value, dict) or key not in value:
								logger.error(u"Key '%s' not found" % key)
								value = u''
								break
							value = value[key]
							if isinstance(value, list):
								value = u', '.join(value)
							if method:
								value = eval("value.%s" % method)

						device[attribute['Opsi']] = value
					except Exception as e:
						logger.warning(e)
						device[attribute['Opsi']] = u''
				opsiValues[opsiClass].append(device)

	opsiValues['SCANPROPERTIES'] = [{"scantime": time.strftime("%Y-%m-%d %H:%M:%S")}]
	logger.debug(u"Result of hardware inventory:\n" + objectToBeautifiedText(opsiValues))
	return opsiValues


def daemonize():
	# Fork to allow the shell to return and to call setsid
	try:
		pid = os.fork()
		if pid > 0:
			# Parent exits
			sys.exit(0)
	except OSError as e:
		raise Exception(u"First fork failed: %e" % e)

	# Do not hinder umounts
	os.chdir("/")
	# Create a new session
	os.setsid()

	# Fork a second time to not remain session leader
	try:
		pid = os.fork()
		if pid > 0:
			sys.exit(0)
	except OSError as e:
		raise Exception(u"Second fork failed: %e" % e)

	logger.setConsoleLevel(LOG_NONE)

	# Close standard output and standard error.
	os.close(0)
	os.close(1)
	os.close(2)

	# Open standard input (0)
	if hasattr(os, "devnull"):
		os.open(os.devnull, os.O_RDWR)
	else:
		os.open("/dev/null", os.O_RDWR)

	# Duplicate standard input to standard output and standard error.
	os.dup2(0, 1)
	os.dup2(0, 2)
	sys.stdout = logger.getStdout()
	sys.stderr = logger.getStderr()


def locateDHCPDConfig(default=None):
	locations = (
		u"/etc/dhcpd.conf",  # suse / redhat / centos
		u"/etc/dhcp/dhcpd.conf",  # newer debian / ubuntu
		u"/etc/dhcp3/dhcpd.conf"  # older debian / ubuntu
	)

	for filename in locations:
		if os.path.exists(filename):
			return filename

	if default is not None:
		return default

	raise RuntimeError(u"Could not locate dhcpd.conf.")


def locateDHCPDInit(default=None):
	"""
	Returns the init command for the DHCPD.

	It will try to get the init script from ``/etc/init.d``.
	If no init commands are found and `default` is given it will return
	the	default.
	If no default is given it will throw an :py:exc:`RuntimeError`.

	:param default: If no init script is found fall back to this \
instead of throwing an error.
	:returntype: str
	"""
	locations = (
		u"/etc/init.d/dhcpd",  # suse / redhat / centos
		u"/etc/init.d/isc-dhcp-server",  # newer debian / ubuntu
		u"/etc/init.d/dhcp3-server"  # older debian / ubuntu
	)

	for filename in locations:
		if os.path.exists(filename):
			return filename

	if default is not None:
		return default

	raise RuntimeError(u"Could not locate dhcpd init file.")


def getDHCPDRestartCommand(default=None):
	"""
	Returns a command that can be used to restart the used DHCPD.

	The command will include the full path to tools used, i.e. service.

	If no command can be automatically determined and `default` is given
	this will be returned. If `default` is not given an ``RuntimeError``
	will be risen.
	"""
	serviceName = getDHCPServiceName()
	if serviceName:
		try:
			return u"{service} {name} restart".format(
				name=serviceName,
				service=which('service')
			)
		except Exception as err:
			logger.debug(
				"Ooops, getting the path to service failed: {0}".format(err)
			)

	locations = (
		u"/etc/init.d/dhcpd",  # suse / redhat / centos
		u"/etc/init.d/isc-dhcp-server",  # newer debian / ubuntu
		u"/etc/init.d/dhcp3-server"  # older debian / ubuntu
	)

	for filename in locations:
		if os.path.exists(filename):
			return u"{initscript} restart".format(initscript=filename)

	if default is not None:
		logger.debug(
			u"Could not find dhcpd restart command but default is given. "
			u"Making use of default: {0}".format(default)
		)
		return default

	raise RuntimeError(u"Could not find DHCPD restart command.")


def getDHCPServiceName():
	"""
	Tries to read the name of the used dhcpd.
	Returns `None` if no known service was detected.
	"""
	knownServices = (
		u"dhcpd", u"univention-dhcp", u"isc-dhcp-server", u"dhcp3-server"
	)

	try:
		for servicename in getServiceNames():
			if servicename in knownServices:
				return servicename
	except Exception:
		pass


def getSambaServiceName(default=None, staticFallback=True):
	"""
	Get the name for the samba service.

	:param default: If not value was detected use this as default.
	:type default: str
	:param staticFallback: If this is ``True`` it will use a static \
lookup to determine what value needs to be returned in case no \
service name was detected by the automatic approach.
	:type staticFallback: bool
	"""
	def getFixServiceName():
		distroName = distro.distribution.strip().lower()
		if distroName == u'debian':
			if distro.version[0] == 6:
				return "samba"
			else:
				return "smbd"
		elif distroName == u'ubuntu':
			return "smbd"
		elif distroName in (u'opensuse', u'centos', u'red hat enterprise linux server'):
			return "smb"

	distro = Distribution()
	if distro.distribution.strip() == u'SUSE Linux Enterprise Server':
		return u"smb"

	possibleNames = (u"samba", u"smb", u"smbd")

	for servicename in getServiceNames():
		if servicename in possibleNames:
			return servicename

	if staticFallback:
		servicename = getFixServiceName()
		if servicename is not None:
			return servicename

	if default is not None:
		return default

	raise RuntimeError(u"Could not get samba service name.")


def getServiceNames(_serviceStatusOutput=None):
	"""
	Get the names of services on the system.

	This script tries to pull the information from ``systemctl`` if
	present. If ``systemctl`` is not present it will fall back to use
	``service``.

	:param _serviceStatusOutput: The output of `service --status-all`.\
Used for testing.
	:type _serviceStatusOutput: [str, ]
	:returntype: set

	.. versionadded:: 4.0.5.11


	.. note:

	  RHEL / CentOS 7 will display insufficent information when using
	  the ``service``-command and we work around this preferring ``systemctl``.


	.. note::

	  Does not work on Suse Linux Enterprise Server (SLES) 11SP3.
	"""
	if not _serviceStatusOutput:
		try:
			_serviceStatusOutput = execute(u"{0} list-unit-files".format(which("systemctl")))
		except Exception:
			_serviceStatusOutput = execute(u"{0} --status-all".format(which("service")))

	patterns = [
		'\[.*\]\s+(?P<servicename>.+)',  # Debian
		'(?P<servicename>.+) \(PID',  # RHEL 6
		'(?P<servicename>.+) w',  # RHEL 6, part 2
		r'(?P<servicename>([\w-]|@)+)\.service',  # systemd-based
	]
	patterns = [re.compile(pattern) for pattern in patterns]

	services = set()

	for line in _serviceStatusOutput:
		for pattern in patterns:
			match = pattern.search(line.strip())
			if match:
				services.add(match.group('servicename').strip())
				break

	logger.debug(u"Found the following services: {0}".format(services))
	return services


def getActiveSessionIds(winApiBugCommand=None, data=None):
	"""
	Getting the IDs of the currently active sessions.

	.. versionadded:: 4.0.5
	:param data: Prefetched data to read information from.
	:type data: [str, ]
	:returntype: [int, ]

	"""
	if data is None:
		data = execute(u"who -p -u")

	sessionIds = []
	for line in data:
		parts = re.split('\s+', line)
		if len(parts) == 7:
			sessionIds.append(int(parts[-2]))
		elif len(parts) == 6:
			sessionIds.append(int(parts[-1]))
		else:
			raise ValueError("Can't get session ID from line: {0}".format(line))

	return sessionIds


def getActiveSessionId():
	"""
	Returns the currently active session ID.

	.. versionadded:: 4.0.5
	:returntype: int

	"""
	ownPid = os.getpid()
	return os.getsid(ownPid)


def getActiveConsoleSessionId():
	"""
	Get the currently used console session id.

	.. warning::

	   This is currently only faked to have the function available for
	   the opsi-linux-client-agent!

	"""
	# TODO: real implementation possible?
	return 0


def runCommandInSession(command, sessionId=None, desktop=None, duplicateFrom=None, waitForProcessEnding=True, timeoutSeconds=0):
	"""
	Run an command.

	The arguments `sessionId`, `desktop` and `duplicateFrom` currently
	do not have any effect and are only provided to have a method
	signature matching the one from the corresponding Windows module.

	.. versionadded:: 4.0.5.2


	:param waitForProcessEnding: If this is `False` the command will be \
started and we will not wait for it to finish.
	:type waitForProcessEnding: bool
	:param timeoutSeconds: If this is set we will wait this many seconds \
until the execution of the process is terminated.
	:returntype: (subprocess.Popen, None, int, None) if \
`waitForProcessEnding` is False, otherwise (None, None, None, None)
	"""
	sleepDuration = 0.1

	command = forceUnicode(command)
	waitForProcessEnding = forceBool(waitForProcessEnding)
	timeoutSeconds = forceInt(timeoutSeconds)

	logger.notice(u"Executing: '{0}'".format(command))
	process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	logger.info(u"Process started, pid: {0}".format(process.pid))
	if not waitForProcessEnding:
		return (process, None, process.pid, None)

	logger.info(u"Waiting for process ending: {0} (timeout: {1} seconds)".format(process.pid, timeoutSeconds))
	timeRunning = 0.0
	while process.poll() is None:
		if timeoutSeconds:
			if timeRunning >= timeoutSeconds:
				_terminateProcess(process)
				raise Exception(u"Timed out after {0} seconds while waiting for process {1}".format(timeRunning, process.pid))

			timeRunning += sleepDuration
		time.sleep(sleepDuration)

	exitCode = process.returncode
	logger.notice(u"Process {0} ended with exit code {1}".format(process.pid, exitCode))
	return (None, None, None, None)


def setLocalSystemTime(timestring):
	"""
	Method sets the local systemtime
	param timestring = "2014-07-15 13:20:24.085661"
	Die Typ SYSTEMTIME-Struktur ist wie folgt:

	WYear           Integer-The current year.
	WMonth          Integer-The current month. January is 1.
	WDayOfWeek      Integer-The current day of the week. Sunday is 0.
	WDay            Integer-The current day of the month.
	WHour           Integer-The current hour.
	wMinute         Integer-The current minute.
	wSecond         Integer-The current second.
	wMilliseconds   Integer-The current millisecond.


	win32api.SetSystemTime

	int = SetSystemTime(year, month , dayOfWeek , day , hour , minute , second , millseconds )

	http://docs.activestate.com/activepython/2.5/pywin32/win32api__SetSystemTime_meth.html
	"""
	if not timestring:
		raise Exception(u"Invalid timestring given. It should be in format like: '2014-07-15 13:20:24.085661'")

	try:
		dt = datetime.datetime.strptime(timestring, '%Y-%m-%d %H:%M:%S.%f')
		logger.info(u"Setting Systemtime Time to %s" % timestring)
		systemTime = 'date --set="%s-%s-%s %s:%s:%s.%s"' % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond)
		subprocess.call([systemTime])
	except Exception as error:
			logger.error(u"Failed to set System Time: %s" % error)
