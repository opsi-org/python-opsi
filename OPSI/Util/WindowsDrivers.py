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
import os, re

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI import System
from OPSI.Util import findFiles

# Get logger instance
logger = Logger()

def integrateDrivers(driverSourceDirectories, driverDestinationDirectory, messageSubject=None):
	logger.info(u"Integrating drivers")
	
	if messageSubject:
		messageSubject.setMessage(u"Integrating drivers")
	
	driverDestinationDirectories = []
	driverNumber = 0
	if not os.path.exists(driverDestinationDirectory):
		os.mkdir(driverDestinationDirectory)
	
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
		if not os.path.exists(driverSourceDirectory):
			logger.error(u"Driver directory '%s' not found" % driverSourceDirectory)
			if messageSubject:
				messageSubject.setMessage(u"Driver directory '%s' not found" % driverSourceDirectory)
			continue
		files = []
		for f in os.listdir(driverSourceDirectory):
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
		System.copy(driverSourceDirectory + '/*', dstDriverPath)
		driverDestinationDirectories.append(forceUnicode(dstDriverPath))
		integratedFiles.append(files)
	return driverDestinationDirectories

def integrateTextmodeDrivers(driverDirectory, destination, hardware, sifFile=None, messageSubject=None):
	logger.info(u"Integrating textmode drivers")
	
	if messageSubject:
		messageSubject.setMessage(u"Integrating textmode drivers")
	
	hardwareIds = {}
	for info in hardware.get("PCI_DEVICE", []):
		vendorId = info.get('vendorId', '').upper()
		deviceId = info.get('deviceId', '').upper()
		if not hardwareIds.has_key(vendorId):
			hardwareIds[vendorId] = []
		hardwareIds[vendorId].append(deviceId)
	
	logger.info(u"Searching for txtsetup.oem in '%s'" % driverDirectory)
	txtSetupOems = findFiles(directory = driverDirectory, prefix = driverDirectory, includeFile = re.compile('^txtsetup\.oem$', re.IGNORECASE), returnDirs = False)
	for txtSetupOem in txtSetupOems:
		logger.notice(u"'%s' found, integrating textmode driver" % txtSetupOem)
		if messageSubject:
			messageSubject.setMessage(u"'%s' found, integrating textmode driver" % txtSetupOem)
		driverPath = os.path.dirname(txtSetupOem)
		
		
		# Copy files
		oemBootFiles = []
		oemBootFiles.append( os.path.basename(txtSetupOem) )
		for textmodePath in ( 	os.path.join(destination, '$', 'textmode'), \
					os.path.join(destination, '$win_nt$.~bt', '$oem$') ):
			if not os.path.exists(textmodePath):
				os.mkdir(textmodePath)
			System.System.copy(txtSetupOem, textmodePath)
		
		for one in inf, driver, catalog:
			for fn in one:
				System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$', 'textmode', os.path.basename(fn)))
				System.copy(os.path.join(driverPath, fn), os.path.join(destination, '$win_nt$.~bt', '$oem$',fn))
				oemBootFiles.append(fn)
		
		# Patch winnt.sif
		if sifFile:
			logger.notice("Registering textmode drivers in sif file '%s'" % sifFile)
			lines = []
			massStorageDriverLines = []
			oemBootFileLines = []
			section = ''
			sif = open(sifFile, 'r')
			for line in sif.readlines():
				if line.strip():
					logger.debug2("Current sif file content: %s" % line.rstrip())
				if line.strip().startswith('['):
					section = line.strip().lower()[1:-1]
					if section in ('massstoragedrivers', 'oembootfiles'):
						continue
				if (section == 'massstoragedrivers'):
					massStorageDriverLines.append(line)
					continue
				if (section == 'oembootfiles'):
					oemBootFileLines.append(line)
					continue
				lines.append(line)
			sif.close()
			
			logger.info("Patching sections for driver '%s'" % description)
			
			if not massStorageDriverLines:
				massStorageDriverLines = ['\r\n', '[MassStorageDrivers]\r\n']
			massStorageDriverLines.append('"%s" = OEM\r\n' % description)
			
			if not oemBootFileLines:
				oemBootFileLines = ['\r\n', '[OEMBootFiles]\r\n']
			for obf in oemBootFiles:
				oemBootFileLines.append('%s\r\n' % obf)
			
			logger.debug("Patching [MassStorageDrivers] in file '%s':" % sifFile)
			logger.debug(massStorageDriverLines)
			lines.extend(massStorageDriverLines)
			logger.debug("Patching [OEMBootFiles] in file '%s':" % sifFile)
			logger.debug(oemBootFileLines)
			lines.extend(oemBootFileLines)
			
			sif = open(sifFile, 'w')
			sif.writelines(lines)
			sif.close()
		
def integrateAdditionalDrivers(driverSourceDirectory, driverDestinationDirectory, additionalDrivers, messageObserver=None, progressObserver=None):
	logger.info("Adding additional drivers")
	
	messageSubject = MessageSubject(id='integrateAdditionalDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	messageSubject.setMessage("Adding additional drivers")
	
	driverDirectories = []
	for additionalDriver in additionalDrivers.split(','):
		additionalDriver = additionalDriver.strip()
		if not additionalDriver:
			continue
		additionalDriverDir = os.path.join(driverSourceDirectory, additionalDriver)
		if not os.path.exists(additionalDriverDir):
			logger.error("Additional drivers dir '%s' not found" % additionalDriverDir)
			messageSubject.setMessage("Additional drivers dir '%s' not found" % additionalDriverDir, severity='ERROR')
			continue
		infFiles = findFiles(directory = additionalDriverDir, prefix = additionalDriverDir, includeFile = re.compile('\.inf$', re.IGNORECASE), returnDirs=False)
		logger.info("Found inf files: %s in dir '%s'" % (infFiles, additionalDriverDir))
		if not infFiles:
			logger.error("No drivers found in dir '%s'" % additionalDriverDir)
			messageSubject.setMessage("No drivers found in dir '%s'" % additionalDriverDir, severity='ERROR')
			continue
		for infFile in infFiles:
			additionalDriverDir = os.path.dirname(infFile)
			if additionalDriverDir in driverDirectories:
				continue
			logger.info("Adding additional driver dir '%s'" % additionalDriverDir)
			messageSubject.setMessage("Adding additional driver dir '%s'" % additionalDriverDir, severity='INFO')
			driverDirectories.append(additionalDriverDir)
	
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
	return integrateDrivers(driverDirectories, driverDestinationDirectory, messageObserver, progressObserver)

def integrateHardwareDrivers(driverSourceDirectory, driverDestinationDirectory, hardware, messageObserver=None, progressObserver=None):
	logger.info("Adding drivers for detected hardware")
	
	messageSubject = MessageSubject(id='integrateHardwareDrivers')
	if messageObserver:
		messageSubject.attachObserver(messageObserver)
	messageSubject.setMessage("Adding drivers for detected hardware")
	
	driverDirectories = []
	integratedFiles = []
	for type in ('PCI', 'USB', 'HDAUDIO'):
		devices = []
		baseDir = ''
		if (type == 'PCI'):
			devices = hardware.get("PCI_DEVICE", [])
			baseDir = 'pciids'
		elif (type == 'USB'):
			devices = hardware.get("USB_DEVICE", [])
			baseDir = 'usbids'
		elif (type == 'HDAUDIO'):
			devices = hardware.get("HDAUDIO_DEVICE", [])
			baseDir = 'hdaudioids'
		for info in devices:
			name = info.get('name', '???')
			name = name.replace('/', '_')
			vendorId = info.get('vendorId', '').upper()
			deviceId = info.get('deviceId', '').upper()
			if not vendorId or not deviceId:
				continue
			logger.info("Searching driver for %s device '%s', id '%s:%s'" % (type, name, vendorId, deviceId))
			messageSubject.setMessage("Searching driver for %s device '%s', id '%s:%s'" % (type, name, vendorId, deviceId), severity = 'INFO')
			srcDriverPath = os.path.join(driverSourceDirectory, baseDir, vendorId)
			if not os.path.exists(srcDriverPath):
				logger.error("%s Vendor directory '%s' not found" % (type, srcDriverPath))
				messageSubject.setMessage("%s Vendor directory '%s' not found" % (type, srcDriverPath), severity = 'ERROR')
				continue
			srcDriverPath = os.path.join(srcDriverPath, deviceId)
			if not os.path.exists(srcDriverPath):
				logger.error("%s Device directory '%s' not found" % (type, srcDriverPath))
				messageSubject.setMessage("%s Device directory '%s' not found" % (type, srcDriverPath), severity = 'ERROR')
				continue
			if os.path.exists( os.path.join(srcDriverPath, 'WINDOWS_BUILDIN') ):
				logger.notice("Using build-in windows driver")
				messageSubject.setMessage("Using build-in windows driver", severity = 'SUCCESS')
				continue
			logger.notice("Found driver for %s device '%s', in dir '%s'" % (type, name, srcDriverPath))
			logger.notice("Integrating driver for %s device '%s'" % (type, name))
			messageSubject.setMessage("Integrating driver for %s device '%s'" % (type, name), severity = 'SUCCESS')
			driverDirectories.append(srcDriverPath)
	
	if messageObserver:
		messageSubject.detachObserver(messageObserver)
	
	return integrateDrivers(driverDirectories, driverDestinationDirectory, messageObserver, progressObserver)

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

