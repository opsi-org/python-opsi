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
"""
opsi python library - Posix

Functions and classes for the use with a POSIX operating system.

:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import re
import struct
import sys
import subprocess
import threading
import time

from OPSI.Logger import Logger
from OPSI.Types import forceUnicode
from OPSI.Object import *
from OPSI.Util import  objectToBeautifiedText, removeUnit

logger = Logger()


def getKernelParams():
	return {}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            NETWORK                                                -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def getEthernetDevices():
	return []

def getNetworkInterfaces():
	return [getNetworkDeviceConfig(device) for device in getEthernetDevices()]

def getNetworkDeviceConfig(device):
	if not device:
		raise ValueError(u"No device given")

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
	return result

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
		self._regex = re.compile(r'\s*(\S+):\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')
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
		pass #TODO

	def getBytesInPerSecond(self):
		return self._bytesInPerSecond

	def getBytesOutPerSecond(self):
		return self._bytesOutPerSecond

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                            FILESYSTEMS                                            -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def isXenialSfdiskVersion():
	return False

def getHarddisks(data=None):
	"""
	Get the available harddisks from the machine.

	:param data: Data to parse through.
	:type data: [str, ]
	:return: The found harddisks.
	:rtype: [Harddisk, ]
	"""
	disks = []
	#TODO
	return disks


def is_mounted(devOrMountpoint):
	#TODO
	return False

def getBlockDeviceBusType(device):
	"""
	:return: 'IDE', 'SCSI', 'SATA', 'RAID' or None (not found)
	:rtype: str or None
	"""
	#TODO
	return None

class Harddisk:
	pass

class Distribution:
	pass


class SysInfo:
	pass

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# -                                       HARDWARE INVENTORY                                          -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def set_value(mydict, key_list, last_key, value):
	subdict = mydict
	for key in key_list:
		sub = subdict.get(key)
		if sub is None:
			subdict[key] = {}
			subdict = subdict.get(key)
		else:
			subdict = sub
	subdict[last_key] = value

def parse_profiler_output(lines):
	optRegex = re.compile('(\s+)([^:]+):(.*)')

	hwdata = {}
	key_list = []
	current_indent = 0
	for line in lines:
		indent = len(line) - len(line.lstrip())
		parts = [x.strip() for x in line.split(":", 1)]
		if len(parts) < 2:
			logger.devel("unexpected input line %s", line)
			continue

		#IDEA: more efficient to maintain a subdict view -> Problem: upwards reference
		if indent > current_indent and parts[1] == "":
			current_indent = indent
			key_list.append(parts[0])
		elif indent < current_indent:
			current_indent = indent
			key_list.pop()
		elif not parts[1] == "":
			value = removeUnit(parts[1])
			set_value(hwdata, key_list, parts[0], value)
	return hwdata

def hardwareInventory(config):

	if not config:
		logger.error(u"hardwareInventory: no config given")
		return {}

	opsiValues = {}
	hardwareList = []

	# Read output from system_profiler	
	logger.debug("calling system_profiler command")
	getHardwareCommand = "system_profiler SPParallelATADataType SPAudioDataType SPBluetoothDataType SPCameraDataType \
			SPCardReaderDataType SPEthernetDataType SPDiscBurningDataType SPFibreChannelDataType SPFireWireDataType \
			SPDisplaysDataType SPHardwareDataType SPHardwareRAIDDataType SPMemoryDataType SPNVMeDataType \
			SPNetworkDataType SPParallelSCSIDataType SPPowerDataType SPSASDataType SPSerialATADataType \
			SPStorageDataType SPThunderboltDataType SPUSBDataType"
	cmd = "{}".format(getHardwareCommand)
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	logger.debug("reading stdout stream from system_profiler")
	while True:
		line = proc.stdout.readline()
		if not line:
			break
		hardwareList.append(forceUnicode(line))		#line.rstrip()
	hwdata = parse_profiler_output(hardwareList)
	logger.debug(u"Parsed system_profiler info:")
	logger.debug(objectToBeautifiedText(hwdata))

	# Build hw info structure
	for hwClass in config:		#config['result']:
		if not hwClass.get('Class') or not hwClass['Class'].get('Opsi'): # or not hwClass['Class'].get('OSX'):
			continue
		opsiClass = hwClass['Class'].get('Opsi')
		osxClass = hwClass['Class'].get('OSX')

		logger.info(u"Processing class '%s' : '%s'" % (opsiClass, osxClass))
		
		# Get hw info from system_profiler
		if osxClass is not None and osxClass.startswith('[profiler]'):
			opsiValues[opsiClass] = []
			for hwclass in osxClass[10:].split('|'):
				(filterAttr, filterExp) = (None, None)
				if ':' in hwclass:
					(hwclass, filter_string) = hwclass.split(':', 1)
					if '.' in filter_string:
						(filterAttr, filterExp) = filter_string.split('.', 1)
				for dev in hwdata.get(hwclass, {}):
					logger.debug("found device %s for hwclass %s", dev, hwclass)
					if filterAttr and dev.get(filterAttr) and not eval("str(dev.get(filterAttr)).%s" % filterExp):
						continue
					device = {}
					for attribute in hwClass['Values']:
						if not attribute.get('OSX'):
							continue
						for aname in attribute['OSX'].split('||'):
							if hwclass == "Network":
								logger.devel("aname is %s", aname)
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
									logger.warning(u"Class %s: Failed to excecute '%s.%s': %s" % (opsiClass, dev.get(aname, ''), method, e))
							else:
								device[attribute['Opsi']] = dev.get(aname)
							if device[attribute['Opsi']]:
								break
					device["state"] = "1"
					device["type"] = "AuditHardwareOnHost"
					opsiValues[hwClass['Class']['Opsi']].append(device)

	opsiValues['SCANPROPERTIES'] = [{"scantime": time.strftime("%Y-%m-%d %H:%M:%S")}]
	logger.debug(u"Result of hardware inventory:\n" + objectToBeautifiedText(opsiValues))
	return opsiValues

def getServiceNames(_serviceStatusOutput=None):
	#TODO
	services = set()
	return services

def runCommandInSession(command, sessionId=None, desktop=None, duplicateFrom=None, waitForProcessEnding=True, timeoutSeconds=0, noWindow=False):
	#TODO
	return (None, None, None, None)