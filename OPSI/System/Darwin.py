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
opsi python library - Darwin

Functions and classes for the use with a DARWIN operating system.

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

HIERARCHY_SEPARATOR = "//"

def set_tree_value(mydict, key_list, last_key, value):
	subdict = mydict
	for key in key_list:
		sub = subdict.get(key)
		if sub is None:
			subdict[key] = {}
			subdict = subdict.get(key)
		else:
			subdict = sub
	subdict[last_key] = value

def get_tree_value(mydict, key_string):
	key_list = key_string.split(HIERARCHY_SEPARATOR)
	subdict = mydict
	for key in key_list:
		sub = subdict.get(key)
		if sub is None:
			return None
		else:
			subdict = sub
	return subdict

def parse_profiler_output(lines):
	hwdata = {}
	key_list = []
	indent_list = [-1]
	for line in lines:
		indent = len(line) - len(line.lstrip())
		parts = [x.strip() for x in line.split(":", 1)]
		if len(parts) < 2:
			continue

		while indent <= indent_list[-1]:	# walk up tree
			indent_list.pop()
			key_list.pop()
		if parts[1] == "":					# branch new subtree ...
			indent_list.append(indent)
			key_list.append(parts[0])
		else:								# ... or fill in leaf
			value = parts[1].strip(",")
			value = removeUnit(value)
			set_tree_value(hwdata, key_list, parts[0], value)
	return hwdata

def parse_sysctl_output(lines):
	hwdata = {}
	for line in lines:
		key_string, value = line.split(':', 1)
		key_list = key_string.split('.')
		set_tree_value(hwdata, key_list[:-1], key_list[-1], value.strip())
	return hwdata

def parse_ioreg_output(lines):
	hwdata = {}
	key_list = []
	indent_list = [-1]
	for line in lines:
		if line.endswith("{") or line.endswith("}"):
			continue
		indent = line.find("+-o ")
		parts = [x.strip() for x in line.split("=", 1)]

		while indent <= indent_list[-1]:	# walk up tree
			indent_list.pop()
			key_list.pop()
		if len(parts) == 1:					# branch new subtree ...
			indent_list.append(indent)
			key = parts[0][indent+3:].split("<")[0]
			key_list.append(key.strip())
		else:								# ... or fill in leaf
			value = removeUnit(parts[1])
			set_tree_value(hwdata, key_list, parts[0], value)
	return hwdata

def osx_hardwareInventory(config):

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
			SPStorageDataType SPThunderboltDataType SPUSBDataType SPSoftwareDataType"
	cmd = "{}".format(getHardwareCommand)
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	logger.debug("reading stdout stream from system_profiler")
	while True:
		line = proc.stdout.readline()
		if not line:
			break
		hardwareList.append(forceUnicode(line))
	profiler = parse_profiler_output(hardwareList)
	logger.debug(u"Parsed system_profiler info:")
	logger.debug(objectToBeautifiedText(profiler))

	hardwareList = []
	# Read output from systcl
	logger.debug("calling sysctl command")
	getHardwareCommand = "sysctl -a"
	cmd = "{}".format(getHardwareCommand)
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	logger.debug("reading stdout stream from sysctl")
	while True:
		line = proc.stdout.readline()
		if not line:
			break
		hardwareList.append(forceUnicode(line))
	systcl = parse_sysctl_output(hardwareList)
	logger.debug(u"Parsed sysctl info:")
	logger.debug(objectToBeautifiedText(systcl))

	hardwareList = []
	# Read output from ioreg
	logger.debug("calling ioreg command")
	getHardwareCommand = "ioreg -l"
	cmd = "{}".format(getHardwareCommand)
	proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	logger.debug("reading stdout stream from sysctl")
	while True:
		line = proc.stdout.readline()
		if not line:
			break
		hardwareList.append(forceUnicode(line))
	ioreg = parse_ioreg_output(hardwareList)
	logger.debug(u"Parsed ioreg info:")
	logger.debug(objectToBeautifiedText(ioreg))

	# Build hw info structure
	for hwClass in config:
		if not hwClass.get('Class'):
			continue
		opsiClass = hwClass['Class'].get('Opsi')
		osxClass = hwClass['Class'].get('OSX')

		if osxClass is None or opsiClass is None:
			continue
		
		logger.info(u"Processing class '%s' : '%s'", opsiClass, osxClass)
		opsiValues[opsiClass] = []

		command, section = osxClass.split(']', 1)
		command = command[1:]
		for singleclass in section.split('|'):
			(filterAttr, filterExp) = (None, None)
			if ':' in singleclass:
				(singleclass, filter_string) = singleclass.split(':', 1)
				if '.' in filter_string:
					(filterAttr, filterExp) = filter_string.split('.', 1)

			if command == "profiler":
				# produce dictionary from key singleclass - traversed for all devices
				singleclassdata = get_tree_value(profiler, singleclass)
			elif command == "sysctl":
				# produce dictionary with only contents from key singleclass
				singleclassdata = { singleclass : get_tree_value(systcl, singleclass) }
			elif command == "ioreg":
				# produce dictionary with only contents from key singleclass
				singleclassdata = get_tree_value(ioreg, singleclass)
			else:
				break
			for key, dev in singleclassdata.items():
				if not isinstance(dev, dict):
					continue
				logger.debug("found device %s for singleclass %s", key, singleclass)
				if filterAttr and dev.get(filterAttr) and not eval("str(dev.get(filterAttr)).%s" % filterExp):
					continue
				device = {}
				for attribute in hwClass['Values']:
					if not attribute.get('OSX'):
						continue
					for aname in attribute['OSX'].split('||'):
						aname = aname.strip()
						method = None
						if '.' in aname:
							(aname, method) = aname.split('.', 1)
						value = get_tree_value(dev, aname)

						if method:
							try:
								logger.debug(u"Eval: %s.%s" % (value, method))
								device[attribute['Opsi']] = eval("value.%s" % method)
							except Exception as e:
								device[attribute['Opsi']] = u''
								logger.warning(u"Class %s: Failed to excecute '%s.%s': %s" % (opsiClass, value, method, e))
						else:
							device[attribute['Opsi']] = value
						if device[attribute['Opsi']]:
							break
				device["state"] = "1"
				device["type"] = "AuditHardwareOnHost"
				if len(opsiValues[hwClass['Class']['Opsi']]) == 0:
					opsiValues[hwClass['Class']['Opsi']].append(device)
					continue	#catch this case first, as it shortens computation
				previous = opsiValues[hwClass['Class']['Opsi']][-1]
				shared_items = {key: "" for key in previous if key in device and previous[key] == device[key]}
				if len(shared_items) == len(previous) and len(shared_items) == len(device):
					# Do not add two devices with the same characteristics (e.g. 127 empty RAM slots...)
					# TODO: better solution?
					logger.debug("skipping device")
				else:
					opsiValues[hwClass['Class']['Opsi']].append(device)

	opsiValues['SCANPROPERTIES'] = [{"scantime": time.strftime("%Y-%m-%d %H:%M:%S")}]
	logger.debug(u"Result of hardware inventory:\n" + objectToBeautifiedText(opsiValues))
	return opsiValues
