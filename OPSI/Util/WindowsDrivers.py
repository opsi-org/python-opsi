#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
#
# Copyright (C) 2006-2010, 2013-2015 uib GmbH <info@uib.de>
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
Functions to work with Windows drivers.

:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import re
import codecs

import OPSI.System as System
from OPSI.Logger import Logger
from OPSI.Object import AuditHardware, AuditHardwareOnHost
from OPSI.Types import (forceFilename, forceInt, forceList,
	forceObjectClassList, forceUnicode, forceUnicodeList)
from OPSI.Util import findFiles
from OPSI.Util.File import InfFile, TxtSetupOemFile
from OPSI.Util.Repository import Repository

__version__ = '4.0.6.15'

logger = Logger()


def searchWindowsDrivers(driverDir, auditHardwares, messageSubject=None, srcRepository=None):
	driverDir = forceFilename(driverDir)
	try:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardware)
	except Exception:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardwareOnHost)

	exists = os.path.exists
	listdir = os.listdir
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists = srcRepository.exists
		listdir = srcRepository.listdir

	drivers = []
	for auditHardware in auditHardwares:
		hwClass = auditHardware.getHardwareClass()
		baseDir = ''
		if hwClass == 'PCI_DEVICE':
			baseDir = u'pciids'
		elif hwClass == 'USB_DEVICE':
			baseDir = u'usbids'
		elif hwClass == 'HDAUDIO_DEVICE':
			baseDir = u'hdaudioids'
		else:
			logger.debug(u"Skipping unhandled hardware class '%s' (%s)" % (hwClass, auditHardware))
			continue

		if not hasattr(auditHardware, 'vendorId') or not auditHardware.vendorId:
			logger.debug(u"Skipping %s device %s: vendor id not found" % (hwClass, auditHardware))
			continue
		if not hasattr(auditHardware, 'deviceId') or not auditHardware.deviceId:
			logger.debug(u"Skipping %s device %s: device id not found" % (hwClass, auditHardware))
			continue

		name = u'unknown'
		if hasattr(auditHardware, 'name') and auditHardware.name:
			name = auditHardware.name.replace(u'/', u'_')

		logger.info(u"Searching driver for %s '%s', id '%s:%s'" % (hwClass, name, auditHardware.vendorId, auditHardware.deviceId))
		if messageSubject:
			messageSubject.setMessage(u"Searching driver for %s '%s', id '%s:%s'" % (hwClass, name, auditHardware.vendorId, auditHardware.deviceId))

		driver = {
			'directory': None,
			'buildin': False,
			'textmode': False,
			'vendorId': auditHardware.vendorId,
			'deviceId': auditHardware.deviceId,
			'hardwareInfo': auditHardware
		}
		srcDriverPath = os.path.join(driverDir, baseDir, auditHardware.vendorId)
		if not exists(srcDriverPath):
			logger.error(u"%s vendor directory '%s' not found" % (hwClass, srcDriverPath))
			continue

		srcDriverPath = os.path.join(srcDriverPath, auditHardware.deviceId)
		if not exists(srcDriverPath):
			logger.error(u"%s device directory '%s' not found" % (hwClass, srcDriverPath))
			continue

		if exists(os.path.join(srcDriverPath, 'WINDOWS_BUILDIN')):
			logger.notice(u"Found windows build-in driver")
			driver['buildin'] = True
			drivers.append(driver)
			continue

		logger.notice(u"Found driver for %s device '%s', in dir '%s'" % (hwClass, name, srcDriverPath))
		driver['directory'] = srcDriverPath

		for entry in listdir(srcDriverPath):
			if entry.lower() == 'txtsetup.oem':
				driver['textmode'] = True
				break

		if not driver['textmode']:
			srcDriverPath = os.path.dirname(srcDriverPath)
			for entry in listdir(srcDriverPath):
				if entry.lower() == 'txtsetup.oem':
					driver['directory'] = srcDriverPath
					driver['textmode'] = True
					break
		drivers.append(driver)
	return drivers


def integrateWindowsDrivers(driverSourceDirectories, driverDestinationDirectory, messageSubject=None, srcRepository=None, drivers=None, checkDups=False):
	driverSourceDirectories = forceUnicodeList(driverSourceDirectories)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)

	if not driverSourceDirectories:
		logger.warning(u"No driver source directories passed")
		return []

	driversOnMachine = {}
	if drivers:
		for driver in drivers:
			vendorId = driver.get('vendorId', '')
			deviceId = driver.get('deviceId', '')
			if not vendorId or not deviceId:
				continue
			if vendorId not in driversOnMachine:
				driversOnMachine[vendorId] = []
			driversOnMachine[vendorId].append(deviceId)

	exists = os.path.exists
	copy = System.copy
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists = srcRepository.exists
		copy = srcRepository.copy

	logger.info(u"Integrating drivers: %s" % driverSourceDirectories)

	if messageSubject:
		messageSubject.setMessage(u"Integrating drivers")

	System.mkdir(driverDestinationDirectory)
	driverNumber = 0
	for filename in os.listdir(driverDestinationDirectory):
		dirname = os.path.join(driverDestinationDirectory, filename)
		if not os.path.isdir(dirname):
			continue
		if re.search('^\d+$', filename):
			if forceInt(filename) >= driverNumber:
				driverNumber = forceInt(filename)

	integratedDrivers = {}
	infFiles = findFiles(
		directory=driverDestinationDirectory,
		prefix=driverDestinationDirectory,
		includeFile=re.compile('\.inf$', re.IGNORECASE),
		returnDirs=False,
		followLinks=True
	)
	logger.debug(u"Found inf files: %s in dir '%s'" % (infFiles, driverDestinationDirectory))
	for infFile in infFiles:
		infFile = InfFile(infFile)
		for dev in infFile.getDevices():
			if dev['type'] not in integratedDrivers:
				integratedDrivers[dev['type']] = {}
			if dev['vendor'] not in integratedDrivers[dev['type']]:
				integratedDrivers[dev['type']][dev['vendor']] = []
			if dev['device'] in integratedDrivers[dev['type']][dev['vendor']]:
				continue
			integratedDrivers[dev['type']][dev['vendor']].append(dev['device'])
			logger.debug(u"Integrated driver for %s device %s:%s, infFile: %s found." \
					% (dev['type'], dev['vendor'], dev['device'], os.path.abspath(infFile.getFilename())))

	newDrivers = []
	for driverSourceDirectory in driverSourceDirectories:
		logger.notice(u"Integrating driver dir '%s'" % driverSourceDirectory)
		if messageSubject:
			messageSubject.setMessage(u"Integrating driver dir '%s'" % os.path.basename(driverSourceDirectory))
		if not exists(driverSourceDirectory):
			logger.error(u"Driver directory '%s' not found" % driverSourceDirectory)
			if messageSubject:
				messageSubject.setMessage(u"Driver directory '%s' not found" % driverSourceDirectory)
			continue
		driverNeeded = True
		newDriversTmp = []
		infFiles = findFiles(
			directory=driverSourceDirectory,
			prefix=driverSourceDirectory,
			includeFile=re.compile('\.inf$', re.IGNORECASE),
			returnDirs=False,
			followLinks=True,
			repository=srcRepository)

		for infFile in infFiles:
			tempInfFile = None
			if srcRepository:
				tempInfFile = u'/tmp/temp.inf'
				copy(infFile, tempInfFile)
				infFile = InfFile(tempInfFile)
			else:
				infFile = InfFile(infFile)
			devices = infFile.getDevices()
			newDriversTmp.append({
				'devices': devices,
				'infFile': os.path.basename(infFile.getFilename())
			})
			if checkDups:
				for dev in devices:
					if dev['device'] not in driversOnMachine.get(dev['vendor'], []):
						continue
					if dev['device'] in integratedDrivers.get(dev['type'], {}).get(dev['vendor'], []):
						logger.notice(u"Driver for %s device %s:%s already integrated" \
							% (dev['type'], dev['vendor'], dev['device']))
						driverNeeded = False
					else:
						driverNeeded = True
					break
			if tempInfFile:
				os.remove(tempInfFile)
			if not driverNeeded:
				break

		if driverNeeded:
			driverNumber += 1
			dstDriverPath = os.path.join(driverDestinationDirectory, forceUnicode(driverNumber))
			if not os.path.exists(dstDriverPath):
				os.mkdir(dstDriverPath)

			copy(driverSourceDirectory + '/*', dstDriverPath)
			for i in range(len(newDriversTmp)):
				newDriversTmp[i]['driverNumber'] = driverNumber
				newDriversTmp[i]['directory'] = dstDriverPath
				newDriversTmp[i]['infFile'] = os.path.join(dstDriverPath, newDriversTmp[i]['infFile'])
				for dev in newDriversTmp[i]['devices']:
					if dev['type'] not in integratedDrivers:
						integratedDrivers[dev['type']] = {}
					if dev['vendor'] not in integratedDrivers[dev['type']]:
						integratedDrivers[dev['type']][dev['vendor']] = []
					integratedDrivers[dev['type']][dev['vendor']].append(dev['device'])
			newDrivers.extend(newDriversTmp)
	return newDrivers


def integrateWindowsHardwareDrivers(driverSourceDirectory, driverDestinationDirectory, auditHardwares, messageSubject=None, srcRepository=None):
	logger.info(u"Adding drivers for detected hardware")

	driverSourceDirectory = forceFilename(driverSourceDirectory)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)
	try:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardware)
	except Exception:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardwareOnHost)

	drivers = searchWindowsDrivers(driverDir=driverSourceDirectory, auditHardwares=auditHardwares, messageSubject=messageSubject, srcRepository=srcRepository)

	driverDirectories = []
	for driver in drivers:
		if driver['buildin'] or not driver['directory']:
			continue

		logger.debug(u"Got windows driver: %s" % driver)

		if driver['directory'] not in driverDirectories:
			driverDirectories.append(driver['directory'])

		name = u'[%s:%s]' % (driver['vendorId'], driver['deviceId'])
		if hasattr(driver['hardwareInfo'], 'vendor'):
			name += u' %s' % driver['hardwareInfo'].vendor
		if hasattr(driver['hardwareInfo'], 'name'):
			name += u' : %s' % driver['hardwareInfo'].name
		logger.notice(u"Integrating driver for device %s" % name)
		if messageSubject:
			messageSubject.setMessage(u"Integrating driver for device %s" % name)

	if not driverDirectories:
		logger.debug(u"No driver directories to integrate")
		return []

	return integrateWindowsDrivers(driverDirectories, driverDestinationDirectory, messageSubject=messageSubject, srcRepository=srcRepository, drivers=drivers, checkDups=True)


def integrateWindowsTextmodeDrivers(driverDirectory, destination, devices, sifFile=None, messageSubject=None):
	driverDirectory = forceFilename(driverDirectory)
	destination = forceFilename(destination)
	devices = forceList(devices)

	logger.notice(u"Integrating textmode drivers")

	if not os.path.exists(driverDirectory):
		logger.notice(u"Driver directory '%s' does not exist" % driverDirectory)
		return

	if messageSubject:
		messageSubject.setMessage(u"Integrating textmode drivers")

	logger.info(u"Searching for txtsetup.oem in '%s'" % driverDirectory)
	txtSetupOems = findFiles(directory=driverDirectory, prefix=driverDirectory, includeFile=re.compile('^txtsetup\.oem$', re.IGNORECASE), returnDirs=False)
	if not txtSetupOems:
		logger.info(u"No txtsetup.oem found in '%s'" % driverDirectory)
		return

	for txtSetupOem in txtSetupOems:
		logger.info(u"File '%s' found" % txtSetupOem)
		txtSetupOemFile = TxtSetupOemFile(txtSetupOem)
		driverPath = os.path.dirname(txtSetupOem)
		supportedDevice = None
		deviceKnown = None
		for device in devices:
			logger.debug2(u"Testing if textmode driver '%s' supports device %s" % (driverPath, device))
			try:
				deviceKnown = txtSetupOemFile.isDeviceKnown(vendorId=device.get('vendorId'), deviceId=device.get('deviceId'))
			except Exception as error:
				logger.critical(u"Error by integrating TextMode driver, error was: %s" % error)

			if deviceKnown:
				logger.debug(u"Textmode driver '%s' supports device %s" % (driverPath, device))
				supportedDevice = device
				break
			else:
				logger.debug2(u"Textmode driver '%s' does not support device %s" % (driverPath, device))
				continue
		if not supportedDevice:
			logger.debug2(u"Textmode driver '%s' not needed" % driverPath)
			continue

		logger.notice(u"Integrating textmode driver '%s'" % driverPath)
		if messageSubject:
			messageSubject.setMessage(u"Integrating textmode driver '%s'" % driverPath)

		oemBootFiles = []
		for fn in txtSetupOemFile.getFilesForDevice(vendorId=supportedDevice['vendorId'], deviceId=supportedDevice['deviceId'], fileTypes=['inf', 'driver', 'catalog', 'dll']):
			System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$', 'textmode', os.path.basename(fn)))
			System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$win_nt$.~bt', '$oem$', fn))
			oemBootFiles.append(fn)

		# Apply workarounds for windows setup errors
		txtSetupOemFile.applyWorkarounds()
		txtSetupOemFile.generate()

		oemBootFiles.append(os.path.basename(txtSetupOem))
		for textmodePath in (os.path.join(destination, u'$', u'textmode'),
							os.path.join(destination, u'$win_nt$.~bt', u'$oem$')):
			System.mkdir(textmodePath)
			System.copy(txtSetupOem, textmodePath)

		description = txtSetupOemFile.getComponentOptionsForDevice(vendorId=supportedDevice['vendorId'], deviceId=supportedDevice['deviceId'])['description']

		# Patch winnt.sif
		if sifFile:
			logger.notice(u"Registering textmode drivers in sif file '%s'" % sifFile)
			lines = []
			massStorageDriverLines = []
			oemBootFileLines = []
			section = u''
			with codecs.open(sifFile, 'r', 'cp1250') as sif:
				for line in sif.readlines():
					if line.strip():
						logger.debug2(u"Current sif file content: %s" % line.rstrip())
					if line.strip().startswith(u'['):
						section = line.strip().lower()[1:-1]
						if section in (u'massstoragedrivers', u'oembootfiles'):
							continue
					if section == u'massstoragedrivers':
						massStorageDriverLines.append(line)
						continue
					if section == u'oembootfiles':
						oemBootFileLines.append(line)
						continue
					lines.append(line)

			logger.info(u"Patching sections for driver '%s'" % description)

			if not massStorageDriverLines:
				massStorageDriverLines = [u'\r\n', u'[MassStorageDrivers]\r\n']
			massStorageDriverLines.append(u'"%s" = "OEM"\r\n' % description)

			if not oemBootFileLines:
				oemBootFileLines = [u'\r\n', u'[OEMBootFiles]\r\n']
			for obf in oemBootFiles:
				oemBootFileLines.append(u'%s\r\n' % obf)

			logger.debug(u"Patching [MassStorageDrivers] in file '%s':" % sifFile)
			logger.debug(massStorageDriverLines)
			lines.extend(massStorageDriverLines)
			logger.debug(u"Patching [OEMBootFiles] in file '%s':" % sifFile)
			logger.debug(oemBootFileLines)
			lines.extend(oemBootFileLines)

			with codecs.open(sifFile, 'w', 'cp1250') as sif:
				sif.writelines(lines)


def integrateAdditionalWindowsDrivers(driverSourceDirectory, driverDestinationDirectory, additionalDrivers, messageSubject=None, srcRepository=None, auditHardwareOnHosts=None):
	driverSourceDirectory = forceFilename(driverSourceDirectory)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)
	if not isinstance(additionalDrivers, list):
		additionalDrivers = [additionalDriver.strip() for additionalDriver in forceUnicodeList(additionalDrivers.split(','))]
	else:
		additionalDrivers = forceUnicodeList(additionalDrivers)

	if not auditHardwareOnHosts:
		auditHardwareOnHosts = []

	exists = os.path.exists
	listdir = os.listdir
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists = srcRepository.exists
		listdir = srcRepository.listdir

	logger.info(u"Adding additional drivers")

	if messageSubject:
		messageSubject.setMessage(u"Adding additional drivers")

	rulesdir = os.path.join(driverSourceDirectory, "byAudit")

	auditInfoByClass = {}
	for auditHardwareOnHost in auditHardwareOnHosts:
		if auditHardwareOnHost.hardwareClass not in ("COMPUTER_SYSTEM", "BASE_BOARD"):
			continue
		else:
			if auditHardwareOnHost.hardwareClass not in auditInfoByClass:
				auditInfoByClass[auditHardwareOnHost.hardwareClass] = auditHardwareOnHost

	byAuditIntegrated = False
	if exists(rulesdir) and "COMPUTER_SYSTEM" in auditInfoByClass:
		logger.info(u"Checking if automated integrating of additional drivers are possible")
		auditHardwareOnHost = auditInfoByClass["COMPUTER_SYSTEM"]
		vendorFromHost = re.sub("[\<\>\?\"\:\|\\\/\*]", "_", auditHardwareOnHost.vendor or "")
		modelFromHost = re.sub("[\<\>\?\"\:\|\\\/\*]", "_", auditHardwareOnHost.model or "")
		skuFromHost = auditHardwareOnHost.model or ""
		skuLabel = ""
		fallbackPath = ""

		if vendorFromHost and modelFromHost:
			vendordirectories = listdir(rulesdir)
			if vendorFromHost not in vendordirectories:
				if vendorFromHost.endswith(".") or vendorFromHost.endswith(" "):
					vendorFromHost = "%s_" % vendorFromHost[:-1]

			for vendordirectory in vendordirectories:
				if vendordirectory.lower() == vendorFromHost.lower():
					modeldirectories = listdir(os.path.join(rulesdir, vendordirectory))
					if skuFromHost and skuFromHost in modelFromHost:
						skuLabel = "(%s)" % skuFromHost
					if modelFromHost not in modeldirectories:
						if modelFromHost.endswith(".") or modelFromHost.endswith(" "):
							modelFromHost = "%s_" % modelFromHost[:-1]
					for modeldirectory in modeldirectories:
						if modeldirectory.lower() == modelFromHost.lower():
							logger.info("ByAudit: Exact match found.")
							additionalDrivers.append(os.path.join("byAudit", vendordirectory, modeldirectory))
							byAuditIntegrated = True
							break
						elif modeldirectory.lower() == modelFromHost.replace(skuLabel, "").strip():
							fallbackPath = os.path.join("byAudit", vendordirectory, modeldirectory)
					if not byAuditIntegrated and fallbackPath:
						logger.info("ByAudit: No Exact match found but model without sku found. Using Directory: '%s'" % modeldirectory )
						additionalDrivers.append(fallbackPath)
						byAuditIntegrated = True
					break

	if not byAuditIntegrated and exists(rulesdir) and "BASE_BOARD" in auditInfoByClass:
		logger.info(u"Checking if mainboard-fallback for automated integrating of additional drivers are possible")
		auditHardwareOnHost = auditInfoByClass["BASE_BOARD"]
		vendorFromHost = re.sub("[\<\>\?\"\:\|\\\/\*]", "_", auditHardwareOnHost.vendor or "")
		productFromHost = re.sub("[\<\>\?\"\:\|\\\/\*]", "_", auditHardwareOnHost.product or "")

		if vendorFromHost and productFromHost:
			vendordirectories = listdir(rulesdir)
			if vendorFromHost not in vendordirectories:
				if vendorFromHost.endswith(".") or vendorFromHost.endswith(" "):
					vendorFromHost = "%s_" % vendorFromHost[:-1]

			for vendordirectory in vendordirectories:
				if vendordirectory.lower() == vendorFromHost.lower():
					productdirectories = listdir(os.path.join(rulesdir, vendordirectory))
					if productFromHost not in productdirectories:
						if productFromHost.endswith(".") or productFromHost.endswith(" "):
							productFromHost = "%s_" % productFromHost[:-1]

					for productdirectory in productdirectories:
						if productdirectory.lower() == productFromHost.lower():
							additionalDrivers.append(os.path.join("byAudit", vendordirectory, productdirectory))

	driverDirectories = []
	for additionalDriver in additionalDrivers:
		if not additionalDriver:
			continue
		additionalDriverDir = os.path.join(driverSourceDirectory, additionalDriver)
		if not exists(additionalDriverDir):
			logger.error(u"Additional drivers dir '%s' not found" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage(u"Additional drivers dir '%s' not found" % additionalDriverDir)
			continue
		infFiles = findFiles(
				directory=additionalDriverDir,
				prefix=additionalDriverDir,
				includeFile=re.compile('\.inf$', re.IGNORECASE),
				returnDirs=False,
				followLinks=True,
				repository=srcRepository)
		logger.info(u"Found inf files: %s in dir '%s'" % (infFiles, additionalDriverDir))
		if not infFiles:
			logger.error(u"No drivers found in dir '%s'" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage(u"No drivers found in dir '%s'" % additionalDriverDir)
			continue
		for infFile in infFiles:
			additionalDriverDir = os.path.dirname(infFile)
			parentDir = os.path.dirname(additionalDriverDir)
			try:
				for entry in listdir(parentDir):
					if entry.lower() == 'txtsetup.oem':
						additionalDriverDir = parentDir
						break
			except Exception as error:
				logger.debug(error)

			if additionalDriverDir in driverDirectories:
				continue
			logger.info(u"Adding additional driver dir '%s'" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage(u"Adding additional driver dir '%s'" % additionalDriverDir)
			driverDirectories.append(additionalDriverDir)

	if not driverDirectories:
		logger.debug(u"No additional driver directories to integrate")
		return []

	return integrateWindowsDrivers(driverDirectories, driverDestinationDirectory, messageSubject=messageSubject, srcRepository=srcRepository)


def getOemPnpDriversPath(driverDirectory, target, separator=u';', prePath=u'', postPath=u''):
	logger.info(u"Generating oemPnpDriversPath")
	if not driverDirectory.startswith(target):
		raise Exception(u"Driver directory '%s' not on target '%s'" % (driverDirectory, target))

	relPath = driverDirectory[len(target):]
	while relPath.startswith(os.sep):
		relPath = relPath[1:]
	while relPath.endswith(os.sep):
		relPath = relPath[:-1]
	relPath = u'\\'.join(relPath.split(os.sep))
	oemPnpDriversPath = u''
	if os.path.exists(driverDirectory):
		for dirname in os.listdir(driverDirectory):
			dirname = relPath + u'\\' + dirname
			if prePath:
				dirname = prePath + u'\\' + dirname
			if postPath:
				dirname = postPath + u'\\' + dirname
			if oemPnpDriversPath:
				oemPnpDriversPath += separator
			oemPnpDriversPath += dirname
	logger.info(u"Returning oemPnpDriversPath '%s'" % oemPnpDriversPath)
	return oemPnpDriversPath
