#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - WindowsDrivers  =
   = = = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

# Imports
import os, re, codecs

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *
from OPSI import System
from OPSI.Util import findFiles
from OPSI.Util.File import *
from OPSI.Util.Message import *
from OPSI.Util.Repository import Repository

# Get logger instance
logger = Logger()

def searchWindowsDrivers(driverDir, auditHardwares, messageSubject=None, srcRepository=None):
	driverDir = forceFilename(driverDir)
	try:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardware)
	except:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardwareOnHost)
	
	exists  = os.path.exists
	listdir = os.listdir
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists  = srcRepository.exists
		listdir = srcRepository.listdir
	
	drivers = []
	for auditHardware in auditHardwares:
		hwClass = auditHardware.getHardwareClass()
		baseDir = ''
		if   (hwClass == 'PCI_DEVICE'):
			baseDir = u'pciids'
		elif (hwClass == 'USB_DEVICE'):
			baseDir = u'usbids'
		elif (hwClass == 'HDAUDIO_DEVICE'):
			baseDir = u'hdaudioids'
		else:
			logger.debug(u"Skipping unhandled hardware class '%s' (%s)" % (hwClass, auditHardware))
			continue
		
		if not hasattr(auditHardware, 'vendorId'):
			logger.debug(u"Skipping %s device %s: vendor id not found" % (hwClass, auditHardware))
			continue
		if not hasattr(auditHardware, 'deviceId'):
			logger.debug(u"Skipping %s device %s: device id not found" % (hwClass, auditHardware))
			continue
		
		name = u'unknown'
		if hasattr(auditHardware, 'name'):
			name = auditHardware.name
		name = name.replace(u'/', u'_')
		
		logger.info(u"Searching driver for %s '%s', id '%s:%s'" % (hwClass, name, auditHardware.vendorId, auditHardware.deviceId))
		if messageSubject:
			messageSubject.setMessage(u"Searching driver for %s '%s', id '%s:%s'" % (hwClass, name, auditHardware.vendorId, auditHardware.deviceId))
		
		driver = {
			'directory':    None,
			'buildin':      False,
			'textmode':     False,
			'vendorId':     auditHardware.vendorId,
			'deviceId':     auditHardware.deviceId,
			'hardwareInfo': auditHardware
		}
		srcDriverPath = os.path.join(driverDir, baseDir, auditHardware.vendorId)
		if not exists(srcDriverPath):
			logger.error(u"%s vendor directory '%s' not found" % (hwClass, srcDriverPath))
			#if messageSubject:
			#	messageSubject.setMessage("%s vendor directory '%s' not found" % (hwClass, srcDriverPath))
			continue
		srcDriverPath = os.path.join(srcDriverPath, auditHardware.deviceId)
		if not exists(srcDriverPath):
			logger.error(u"%s device directory '%s' not found" % (hwClass, srcDriverPath))
			#if messageSubject:
			#	messageSubject.setMessage(u"%s device directory '%s' not found" % (hwClass, srcDriverPath))
			continue
		if exists( os.path.join(srcDriverPath, 'WINDOWS_BUILDIN') ):
			logger.notice(u"Found windows build-in driver")
			#if messageSubject:
			#	messageSubject.setMessage(u"Found windows build-in driver")
			driver['buildin'] = True
			drivers.append(driver)
			continue
		logger.notice(u"Found driver for %s device '%s', in dir '%s'" % (hwClass, name, srcDriverPath))
		driver['directory'] = srcDriverPath
		for entry in listdir(srcDriverPath):
			if (entry.lower() == 'txtsetup.oem'):
				driver['textmode'] = True
				break
		if not driver['textmode']:
			srcDriverPath = os.path.dirname(srcDriverPath)
			for entry in listdir(srcDriverPath):
				if (entry.lower() == 'txtsetup.oem'):
					driver['directory'] = srcDriverPath
					driver['textmode'] = True
					break
		drivers.append(driver)
	return drivers
	
def integrateDrivers(driverSourceDirectories, driverDestinationDirectory, messageObserver=None, progressObserver=None):
	messageSubject = MessageSubject(id='integrateDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	integrateWindowsDrivers(driverSourceDirectories, driverDestinationDirectory, messageSubject = messageSubject)
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
def integrateWindowsDrivers(driverSourceDirectories, driverDestinationDirectory, messageSubject=None, srcRepository=None):
	driverSourceDirectories = forceUnicodeList(driverSourceDirectories)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)
	
	exists  = os.path.exists
	listdir = os.listdir
	copy    = System.copy
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists  = srcRepository.exists
		listdir = srcRepository.listdir
		copy    = srcRepository.copy
		
	logger.info(u"Integrating drivers: %s" % driverSourceDirectories)
	
	if messageSubject:
		messageSubject.setMessage(u"Integrating drivers")
	
	driverDestinationDirectories = []
	driverNumber = 0
	System.mkdir(driverDestinationDirectory)
	
	integratedFiles = []
	for filename in os.listdir(driverDestinationDirectory):
		dirname = os.path.join(driverDestinationDirectory, filename)
		if not os.path.isdir(dirname):
			continue
		if re.search('^\d+$', filename):
			if (forceInt(filename) >= driverNumber):
				driverNumber = forceInt(filename)
			files = []
			for f in os.listdir(dirname):
				files.append(f.lower())
			files.sort()
			integratedFiles.append(u','.join(files))
	for driverSourceDirectory in driverSourceDirectories:
		logger.notice(u"Integrating driver dir '%s'" % driverSourceDirectory)
		if messageSubject:
			messageSubject.setMessage(u"Integrating driver dir '%s'" % os.path.basename(driverSourceDirectory))
		if not exists(driverSourceDirectory):
			logger.error(u"Driver directory '%s' not found" % driverSourceDirectory)
			if messageSubject:
				messageSubject.setMessage(u"Driver directory '%s' not found" % driverSourceDirectory)
			continue
		files = []
		for f in listdir(driverSourceDirectory):
			files.append(f.lower())
		files.sort()
		files = u','.join(files)
		logger.debug(u"Driver files: %s" % files)
		for fs in integratedFiles:
			logger.debug(u"   Integrated files: %s" % fs)
		if files in integratedFiles:
			logger.notice(u"Driver directory '%s' already integrated" % driverSourceDirectory)
			if messageSubject:
				messageSubject.setMessage(u"Driver directory '%s' already integrated" % driverSourceDirectory)
			continue
		driverNumber += 1
		dstDriverPath = os.path.join(driverDestinationDirectory, forceUnicode(driverNumber))
		if not os.path.exists(dstDriverPath):
			os.mkdir(dstDriverPath)
		copy(driverSourceDirectory + '/*', dstDriverPath)
		driverDestinationDirectories.append(forceUnicode(dstDriverPath))
		integratedFiles.append(files)
	return driverDestinationDirectories

def integrateHardwareDrivers(driverSourceDirectory, driverDestinationDirectory, hardware, messageObserver=None, progressObserver=None):
	messageSubject = MessageSubject(id='integrateHardwareDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	
	auditHardwares = []
	for (hardwareClass, devices) in hardware.items():
		if (hardwareClass == 'SCANPROPERTIES'):
			continue
		for device in devices:
			data = { 'hardwareClass': hardwareClass }
			for (attribute, value) in device.items():
				data[str(attribute)] = value
			auditHardwares.append( AuditHardware.fromHash(data) )
	
	integrateWindowsHardwareDrivers(driverSourceDirectory, driverDestinationDirectory, auditHardwares, messageSubject = messageSubject)
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
def integrateWindowsHardwareDrivers(driverSourceDirectory, driverDestinationDirectory, auditHardwares, messageSubject=None, srcRepository=None):
	logger.info(u"Adding drivers for detected hardware")
	
	driverSourceDirectory = forceFilename(driverSourceDirectory)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)
	try:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardware)
	except:
		auditHardwares = forceObjectClassList(auditHardwares, AuditHardwareOnHost)
	
	drivers = searchWindowsDrivers(driverDir = driverSourceDirectory, auditHardwares = auditHardwares, messageSubject = messageSubject, srcRepository = srcRepository)
	
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
		
	return integrateWindowsDrivers(driverDirectories, driverDestinationDirectory, messageSubject = messageSubject, srcRepository = srcRepository)

def integrateTextmodeDrivers(driverDirectory, destination, hardware, sifFile=None, messageObserver=None, progressObserver=None):
	messageSubject = MessageSubject(id='integrateTextmodeDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	
	devices = []
	for info in hardware.get("PCI_DEVICE", []):
		if not info.get('vendorId') or not info.get('deviceId'):
			continue
		vendorId = forceHardwareVendorId(info.get('vendorId'))
		deviceId = forceHardwareVendorId(info.get('deviceId'))
		
		devices.append( {"vendorId": vendorId, "deviceId": deviceId} )
	
	integrateWindowsTextmodeDrivers(driverDirectory, destination, devices, sifFile = sifFile, messageSubject = messageSubject)
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
def integrateWindowsTextmodeDrivers(driverDirectory, destination, devices, sifFile=None, messageSubject=None):
	driverDirectory = forceFilename(driverDirectory)
	destination = forceFilename(destination)
	devices = forceList(devices)
	
	logger.notice(u"Integrating textmode drivers")
	
	if messageSubject:
		messageSubject.setMessage(u"Integrating textmode drivers")
	
	logger.info(u"Searching for txtsetup.oem in '%s'" % driverDirectory)
	txtSetupOems = findFiles(directory = driverDirectory, prefix = driverDirectory, includeFile = re.compile('^txtsetup\.oem$', re.IGNORECASE), returnDirs = False)
	if not txtSetupOems:
		logger.info(u"No txtsetup.oem found in '%s'" % driverDirectory)
		return
	
	for txtSetupOem in txtSetupOems:
		logger.info(u"File '%s' found" % txtSetupOem)
		txtSetupOemFile = TxtSetupOemFile(txtSetupOem)
		driverPath = os.path.dirname(txtSetupOem)
		supportedDevice = None
		for device in devices:
			logger.debug2(u"Testing if textmode driver '%s' supports device %s" % (driverPath, device))
			if txtSetupOemFile.isDeviceKnown(vendorId = device.get('vendorId'), deviceId = device.get('deviceId')):
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
		for fn in txtSetupOemFile.getFilesForDevice(vendorId = supportedDevice['vendorId'], deviceId = supportedDevice['deviceId'], fileTypes = ['inf', 'driver', 'catalog', 'dll']):
			System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$', 'textmode', os.path.basename(fn)))
			System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$win_nt$.~bt', '$oem$',fn))
			oemBootFiles.append(fn)
		
		# Apply workarounds for windows setup errors
		txtSetupOemFile.applyWorkarounds()
		txtSetupOemFile.generate()
		
		oemBootFiles.append( os.path.basename(txtSetupOem) )
		for textmodePath in ( 	os.path.join(destination, u'$', u'textmode'), \
					os.path.join(destination, u'$win_nt$.~bt', u'$oem$') ):
			System.mkdir(textmodePath)
			System.copy(txtSetupOem, textmodePath)
		
		description = txtSetupOemFile.getComponentOptionsForDevice(vendorId = supportedDevice['vendorId'], deviceId = supportedDevice['deviceId'])['description']
		
		# Patch winnt.sif
		if sifFile:
			logger.notice(u"Registering textmode drivers in sif file '%s'" % sifFile)
			lines = []
			massStorageDriverLines = []
			oemBootFileLines = []
			section = u''
			sif = codecs.open(sifFile, 'r', 'cp1250')
			for line in sif.readlines():
				if line.strip():
					logger.debug2(u"Current sif file content: %s" % line.rstrip())
				if line.strip().startswith(u'['):
					section = line.strip().lower()[1:-1]
					if section in (u'massstoragedrivers', u'oembootfiles'):
						continue
				if (section == u'massstoragedrivers'):
					massStorageDriverLines.append(line)
					continue
				if (section == u'oembootfiles'):
					oemBootFileLines.append(line)
					continue
				lines.append(line)
			sif.close()
			
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
			
			sif = codecs.open(sifFile, 'w', 'cp1250')
			sif.writelines(lines)
			sif.close()

def integrateAdditionalDrivers(driverSourceDirectory, driverDestinationDirectory, additionalDrivers, messageObserver=None, progressObserver=None):
	logger.notice(u"Integrate additional drivers: %s" % additionalDrivers)
	if type(additionalDrivers) is list:
		additionalDrivers = u','.join(forceUnicodeList(additionalDrivers))
	newAdditionalDrivers = []
	for driverDir in additionalDrivers.split(','):
		driverDir = driverDir.strip()
		if driverDir:
			newAdditionalDrivers.append(driverDir)
	additionalDrivers = newAdditionalDrivers
	
	messageSubject = MessageSubject(id='integrateAdditionalDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	integrateAdditionalWindowsDrivers(driverSourceDirectory, driverDestinationDirectory, additionalDrivers, messageSubject = messageSubject)
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
def integrateAdditionalWindowsDrivers(driverSourceDirectory, driverDestinationDirectory, additionalDrivers, messageSubject=None, srcRepository=None):
	driverSourceDirectory = forceFilename(driverSourceDirectory)
	driverDestinationDirectory = forceFilename(driverDestinationDirectory)
	if not type(additionalDrivers) is list:
		additionalDrivers = [ additionalDriver.strip() for additionalDriver in forceUnicodeList(additionalDrivers.split(',')) ]
	else:
		additionalDrivers = forceUnicodeList(additionalDrivers)
	
	exists  = os.path.exists
	if srcRepository:
		if not isinstance(srcRepository, Repository):
			raise Exception(u"Not a repository: %s" % srcRepository)
		exists  = srcRepository.exists
	
	logger.info(u"Adding additional drivers")
	
	if messageSubject:
		messageSubject.setMessage("Adding additional drivers")
	
	driverDirectories = []
	for additionalDriver in additionalDrivers:
		if not additionalDriver:
			continue
		additionalDriverDir = os.path.join(driverSourceDirectory, additionalDriver)
		if not exists(additionalDriverDir):
			logger.error(u"Additional drivers dir '%s' not found" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage("Additional drivers dir '%s' not found" % additionalDriverDir)
			continue
		infFiles = findFiles(
				directory   = additionalDriverDir,
				prefix      = additionalDriverDir,
				includeFile = re.compile('\.inf$', re.IGNORECASE),
				returnDirs  = False,
				repository  = srcRepository)
		logger.info(u"Found inf files: %s in dir '%s'" % (infFiles, additionalDriverDir))
		if not infFiles:
			logger.error(u"No drivers found in dir '%s'" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage("No drivers found in dir '%s'" % additionalDriverDir)
			continue
		for infFile in infFiles:
			additionalDriverDir = os.path.dirname(infFile)
			if additionalDriverDir in driverDirectories:
				continue
			logger.info(u"Adding additional driver dir '%s'" % additionalDriverDir)
			if messageSubject:
				messageSubject.setMessage("Adding additional driver dir '%s'" % additionalDriverDir)
			driverDirectories.append(additionalDriverDir)
	
	return integrateWindowsDrivers(driverDirectories, driverDestinationDirectory, messageSubject = messageSubject, srcRepository = srcRepository)

def getOemPnpDriversPath(driverDirectory, target, separator=';', prePath='', postPath=''):
	logger.info("Generating oemPnpDriversPath")
	if not driverDirectory.startswith(target):
		raise Exception("Driver directory '%s' not on target '%s'" % (driverDirectory, target))
	
	relPath = driverDirectory[len(target):]
	while relPath.startswith(os.sep):
		relPath = relPath[1:]
	while relPath.endswith(os.sep):
		relPath = relPath[:-1]
	relPath = '\\'.join(relPath.split(os.sep))
	oemPnpDriversPath = ''
	for dirname in os.listdir(driverDirectory):
		dirname = relPath + '\\' + dirname
		if prePath:
			dirname = prePath + '\\' + dirname
		if postPath:
			dirname = postPath + '\\' + dirname
		if oemPnpDriversPath:
			oemPnpDriversPath += separator
		oemPnpDriversPath += dirname
	logger.info("Returning oemPnpDriversPath '%s'" % oemPnpDriversPath)
	return oemPnpDriversPath




