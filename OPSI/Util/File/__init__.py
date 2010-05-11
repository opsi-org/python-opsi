#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =    opsi python library - File     =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH
   
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

__version__ = "4.0"

import os, codecs, re, ConfigParser, StringIO, cStringIO

if (os.name == 'posix'):
	import fcntl, grp, pwd

elif (os.name == 'nt'):
	import win32con
	import win32file
	import pywintypes

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get logger instance
logger = Logger()

class File(object):
	def __init__(self, filename):
		self._filename = forceFilename(filename)
		self._fileHandle = None
		
	def getFilename(self):
		return self._filename
	
	def setFilename(self, filename):
		self._filename = forceFilename(filename)
	
	def exists(self):
		return os.path.exists(self._filename)
			
	def delete(self):
		if os.path.exists(self._filename):
			os.unlink(self._filename)
	
	def chown(self, user, group):
		if (os.name == 'nt'):
			logger.warning(u"Not implemented on windows")
			return
		uid = -1
		if type(user) is int:
			if (user > -1):
				uid = user
		elif not user is None:
			try:
				uid = pwd.getpwnam(user)[2]
			except KeyError:
				raise Exception(u"Unknown user '%s'" % user)
		
		gid = -1
		if type(group) is int:
			if (group > -1):
				gid = group
		elif not group is None:
			try:
				gid = grp.getgrnam(group)[2]
			except KeyError:
				raise Exception(u"Unknown group '%s'" % group)
		
		os.chown(self._filename, uid, gid)
	
	def chmod(self, mode):
		mode = forceOct(mode)
		os.chmod(self._filename, mode)
	
	def create(self, user = None, group = None, mode = None):
		if not os.path.exists(self._filename):
			self.open('w')
			self.close()
		
		if not user is None or not group is None:
			self.chown(user, group)
		if not mode is None:
			self.chmod(mode)
	
	def open(self, mode = 'r'):
		self._fileHandle = __builtins__['open'](self._filename, mode)
		return self._fileHandle
		
	def close(self):
		if not self._fileHandle:
			return
		self._fileHandle.close()
		self._fileHandle = None
		
	def __getattr__(self, attr):
		if self.__dict__.has_key(attr):
			return self.__dict__[attr]
		elif self.__dict__['_fileHandle']:
			return getattr(self.__dict__['_fileHandle'], attr)

class LockableFile(File):
	def __init__(self, filename, lockFailTimeout = 2000):
		File.__init__(self, filename)
		self._lockFailTimeout = forceInt(lockFailTimeout)
	
	def delete(self):
		if os.path.exists(self._filename):
			os.unlink(self._filename)
	
	def open(self, mode = 'r'):
		File.open(self, mode)
		self._lockFile(mode)
		return self._fileHandle
		
	def close(self):
		self._unlockFile()
		File.close(self)
		
	def _lockFile(self, mode='r'):
		timeout = 0
		while (timeout < self._lockFailTimeout):
			# While not timed out and not locked
			logger.debug("Trying to lock file '%s' (%s/%s)" % (self._filename, timeout, self._lockFailTimeout))
			try:
				# Try to lock file
				if (os.name =='posix'):
					# Flags for exclusive, non-blocking lock
					flags = fcntl.LOCK_EX | fcntl.LOCK_NB
					if mode in ('r', 'rb'):
						# Flags for shared, non-blocking lock
						flags = fcntl.LOCK_SH | fcntl.LOCK_NB
					fcntl.flock(self._fileHandle.fileno(), flags)
				elif (os.name == 'nt'):
					flags = win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY
					if mode in ('r', 'rb'):
						flags = win32con.LOCKFILE_FAIL_IMMEDIATELY
					hfile = win32file._get_osfhandle(self._fileHandle.fileno())
					win32file.LockFileEx(hfile, flags, 0, 0x7fff0000, pywintypes.OVERLAPPED())
				
			except IOError, e:
				# Locking failed 
				# increase timeout counter, sleep 100 millis
				timeout += 100
				time.sleep(0.1)
				continue
			# File successfully locked
			logger.debug("File '%s' locked after %d millis" % (self._filename, timeout))
			return self._fileHandle
		
		self.close()
		# File lock failed => raise BackendIOError
		raise IOError("Failed to lock file '%s' after %d millis" % (self._filename,  self._lockFailTimeout))
	
	def _unlockFile(self):
		if not self._fileHandle:
			return
		if (os.name == 'posix'):
			fcntl.flock(self._fileHandle.fileno(), fcntl.LOCK_UN)
		elif (os.name == 'nt'):
			hfile = win32file._get_osfhandle(self._fileHandle.fileno())
			win32file.UnlockFileEx(hfile, 0, 0x7fff0000, pywintypes.OVERLAPPED())
	
class TextFile(LockableFile):
	def __init__(self, filename, lockFailTimeout = 2000):
		LockableFile.__init__(self, filename, lockFailTimeout)
		self._lines = []
		self._lineSeperator = u'\n'
		
	def open(self, mode = 'r', encoding='utf-8', errors='replace'):
		self._fileHandle = codecs.open(self._filename, mode, encoding, errors)
		self._lockFile(mode)
		return self._fileHandle
		
	def write(self, str):
		if not self._fileHandle:
			raise IOError("File not opened")
		str = forceUnicode(str)
		self._fileHandle.write(str)
	
	def readlines(self):
		self._lines = []
		if not self._fileHandle:
			for encoding in ('utf-8', 'utf-16', 'latin_1', 'cp1252', 'replace'):
				errors = 'strict'
				if (encoding == 'replace'):
					errors = 'replace'
					encoding = 'utf-8'
				
				self.open(encoding = encoding, errors = errors)
				try:
					self._lines = self._fileHandle.readlines()
					self.close()
					break
				except ValueError, e:
					self.close()
					continue
		return self._lines
	
	def getLines(self):
		return self._lines
	
	def writelines(self, sequence=[]):
		if not self._fileHandle:
			raise IOError("File not opened")
		if sequence:
			self._lines = forceUnicodeList(sequence)
		for i in range(len(self._lines)):
			self._lines[i] += self._lineSeperator
		self._fileHandle.writelines(self._lines)

class ChangelogFile(TextFile):
	'''
	package (version) distribution(s); urgency=urgency
	    [optional blank line(s), stripped]
	  * change details
	     more change details
	      [blank line(s), included]
	  * even more change details
	      [optional blank line(s), stripped]
	[one space]-- maintainer name <email address>[two spaces]date

	'''
	releaseLineRegex = re.compile('^\s*(\S+)\s+\(([^\)]+)\)\s+([^\;]+)\;\s+urgency\=(\S+)\s*$')
	
	def __init__(self, filename, lockFailTimeout = 2000):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._parsed = False
		self._entries = []
	
	def parse(self, lines=None):
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._parsed = False
		self._entries = []
		for lineNum in range(len(self._lines)):
			try:
				line = self._lines[lineNum]
				match = self.releaseLineRegex.search(line)
				if match:
					self._entries.append( {
						'package':         match.group(1),
						'version':         match.group(2),
						'release':         match.group(3),
						'urgency':         match.group(4),
						'changelog':       [],
						'maintainerName':  u'',
						'maintainerEmail': u'',
						'date':            None
					})
					continue
				
				if line.startswith(' --'):
					if (line.find('  ') == -1):
						raise Exception(u"maintainer must be separated from date using two spaces")
					if (len(self._entries) == 0) or self._entries[-1]['date']:
						raise Exception(u"found trailer out of release")
					
					(maintainer, date) = line[3:].strip().split('  ', 1)
					email = u''
					if (maintainer.find('<') != -1):
						(maintainer, email) = maintainer.split('<', 1)
						maintainer = maintainer.strip()
						email = email.strip().replace('<', '').replace('>', '')
					self._entries[-1]['maintainerName'] = maintainer
					self._entries[-1]['maintainerEmail'] = email
					if (date.find('+') != -1):
						date = date.split('+')[0]
					self._entries[-1]['date'] = time.strptime(date.strip(), "%a, %d %b %Y %H:%M:%S")
					changelog = []
					buf = []
					for l in self._entries[-1]['changelog']:
						if not changelog and not l.strip():
							continue
						if not l.strip():
							buf.append(l)
						else:
							changelog.extend(buf)
							buf = []
							changelog.append(l)
					self._entries[-1]['changelog'] = changelog
					
				else:
					if (len(self._entries) == 0) and line.strip():
						raise Exception(u"text out of release")
					self._entries[-1]['changelog'].append(line.rstrip())
			except Exception, e:
				self._entries = []
				raise Exception(u"Parse error in line %d: %s" % (lineNum, e))
		self._parsed = True
		return self._entries
		
	def generate(self):
		if not self._entries:
			raise Exception(u"No entries to write")
		self._lines = []
		for entry in self._entries:
			self._lines.append(u'%s (%s) %s; urgency=%s' % (entry['package'], entry['version'], entry['release'], entry['urgency']))
			self._lines.append(u'')
			for line in entry['changelog']:
				self._lines.append(line)
			if self._lines[-1].strip():
				self._lines.append(u'')
			self._lines.append(u' -- %s <%s>  %s' % (entry['maintainerName'], entry['maintainerEmail'], time.strftime('%a, %d %b %Y %H:%M:%S +0000', entry['date'])))
			self._lines.append(u'')
		self.open('w')
		self.writelines()
		self.close()
		
	def getEntries(self):
		if not self._parsed:
			self.parse()
		return self._entries
	
	def setEntries(self, entries):
		entries = forceList(entries)
		for i in range(len(entries)):
			entries[i] = forceDict(entries[i])
			for key in ('package', 'version', 'release', 'urgency', 'changelog', 'maintainerName', 'maintainerEmail', 'date'):
				if not entries[i].has_key(key):
					raise Exception(u"Missing key '%s' in entry %s" % (key, entries[i]))
			entries[i]['package']         = forceProductId(entries[i]['package'])
			entries[i]['version']         = forceUnicode(entries[i]['version'])
			entries[i]['release']         = forceUnicode(entries[i]['release'])
			entries[i]['urgency']         = forceUnicode(entries[i]['urgency'])
			entries[i]['changelog']       = forceUnicodeList(entries[i]['changelog'])
			entries[i]['maintainerName']  = forceUnicode(entries[i]['maintainerName'])
			entries[i]['maintainerEmail'] = forceEmailAddress(entries[i]['maintainerEmail'])
			entries[i]['date']            = forceTime(entries[i]['date'])
		self._entries = entries
	
class ConfigFile(TextFile):
	def __init__(self, filename, lockFailTimeout = 2000, commentChars=[';', '#'], lstrip = True):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._commentChars = forceList(commentChars)
		self._lstrip = forceBool(lstrip)
		self._parsed = False
	
	def parse(self, lines=None):
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._parsed = False
		lines = []
		for line in self._lines:
			l = line.strip()
			if not l or l[0] in self._commentChars:
				continue
			if self._lstrip:
				line = line.strip()
			else:
				line = line.rstrip()
			for cc in self._commentChars:
				index = line.find(cc)
				if (index == -1):
					continue
				parts = line.split(cc)
				quote = 0
				doublequote = 0
				cut = -1
				for i in range(len(parts)):
					quote += parts[i].count("'")
					doublequote += parts[i].count('"')
					if (len(parts[i]) > 0) and (parts[i][-1] == '\\'):
						# escaped comment
						continue
					if (i == len(parts)-1):
						break
					if not (quote % 2) and not (doublequote % 2):
						cut = i
						break
				if (cut > -1):
					line = cc.join(parts[:cut+1])
			if not line:
				continue
			#for cc in self._commentChars:
			#	line = line.replace(u'\\' + cc, cc)
			lines.append(line)
		self._parsed = True
		return lines

class IniFile(ConfigFile):
	optionMatch = re.compile('^([^\:\=]+)([\:\=].*)$')
	
	def __init__(self, filename, lockFailTimeout = 2000, ignoreCase = True, raw = True):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars = [';', '#'])
		self._ignoreCase = forceBool(ignoreCase)
		self._raw = forceBool(raw)
		self._configParser = None
		self._parsed = False
		
	def parse(self, lines=None):
		self._parsed = False
		logger.debug(u"Parsing ini file '%s'" % self._filename)
		start = time.time()
		lines = ConfigFile.parse(self, lines)
		self._parsed = False
		if self._ignoreCase:
			for i in range(len(lines)):
				lines[i] = lines[i].strip()
				if lines[i].startswith('['):
					lines[i] = lines[i].lower()
				
				match = self.optionMatch.search(lines[i])
				if not match:
					continue
				lines[i] = match.group(1).lower() + match.group(2)
		
		self._configParser = None
		if self._raw:
			self._configParser = ConfigParser.RawConfigParser()
		else:
			self._configParser = ConfigParser.SafeConfigParser()
		try:
			self._configParser.readfp( StringIO.StringIO(u'\r\n'.join(lines)) )
		except Exception, e:
			raise Exception(u"Failed to parse ini file '%s': %s" % (self._filename, e))
		
		logger.debug(u"Finished reading file after %0.3f seconds" % (time.time() - start))
		
		self._parsed = True
		# Return ConfigParser
		return self._configParser
	
	def generate(self, configParser):
		self._configParser = configParser
		
		if not self._configParser:
			raise Exception(u"Got no data to write")
		
		sections = {}
		for section in self._configParser.sections():
			if type(section) is unicode:
				section = section.encode('utf-8')
			sections[section] = {}
			for (option, value) in self._configParser.items(section):
				if type(option) is unicode:
					option = option.encode('utf-8')
				if type(value) is unicode:
					value = value.encode('utf-8')
				sections[section][option] = value
			self._configParser.remove_section(section)
		
		sectionNames = sections.keys()
		sectionNames.sort()
		
		# Move section 'info' to first place
		if ( 'info' in sectionNames ):
			sectionNames.insert(0, sectionNames.pop(sectionNames.index('info')))
		
		for section in sectionNames:
			self._configParser.add_section(section)
			for (option, value) in sections[section].items():
				self._configParser.set(section, option, value)
		
		data = StringIO.StringIO()
		self._configParser.write(data)
		self._lines = data.getvalue().decode('utf-8').replace('\r', '').split('\n')
		
		self.open('w')
		self.writelines()
		self.close()
	

class InfFile(ConfigFile):
	sectionRegex       = re.compile('\[\s*([^\]]+)\s*\]')
	pciDeviceRegex     = re.compile('VEN_([\da-fA-F]+)&DEV_([\da-fA-F]+)', re.IGNORECASE)
	hdaudioDeviceRegex = re.compile('HDAUDIO\\\.*VEN_([\da-fA-F]+)&DEV_([\da-fA-F]+)', re.IGNORECASE)
	usbDeviceRegex     = re.compile('USB.*VID_([\da-fA-F]+)&PID_([\da-fA-F]+)', re.IGNORECASE)
	acpiDeviceRegex    = re.compile('ACPI\\\(\S+)_-_(\S+)', re.IGNORECASE)
	varRegex           = re.compile('\%([^\%]+)\%')
	classRegex         = re.compile('class\s*=')
	
	def __init__(self, filename, lockFailTimeout = 2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars = [';', '#'])
		self._devices = []
	
	def getDevices(self):
		if not self._parsed:
			self.parse()
		return self._devices
	
	def parse(self, lines=None):
		logger.debug(u"Parsing inf file %s" % self._filename)
		lines = ConfigFile.parse(self, lines)
		self._parsed = False
		self._devices = []
		
		path = os.path.dirname(self._filename)
		
		deviceClass = u'???'
		deviceSections = []
		appendNext = False
		newLines = []
		for line in lines:
			if appendNext:
				newLines[-1] = lines[-1][:-1] + line
			else:
				newLines.append(line)
			
			if line.endswith(u'\\'):
				appendNext = True
			else:
				appendNext = False
		lines = newLines
		
		# Get strings
		logger.debug(u"   - Getting strings")
		strings = {}
		section = u''
		for line in lines:
			match = re.search(self.sectionRegex, line)
			if match:
				if (section.lower() == u'strings'):
					break
				section = match.group(1)
			else:
				if (section.lower() == u'strings'):
					try:
						(var, string) = line.split(u'=', 1)
						string = string.strip()
						if string.startswith(u'"') and string.endswith(u'"'):
							string = string[1:-1]
						strings[var.strip().lower()] = string
					except:
						pass
		logger.debug2(u"        got strings: %s" % strings)
		
		# Get devices
		logger.debug(u"   - Getting devices")
		section = u''
		for line in lines:
			match = re.search(self.sectionRegex, line)
			if match:
				if (section.lower() == u'manufacturer'):
					break
				section = match.group(1)
			else:
				if (section.lower() == u'version'):
					if line.lower().startswith(u'class'):
						if re.search(self.classRegex, line.lower()):
							deviceClass = line.split('=')[1].strip().lower()
							match = re.search(self.varRegex, deviceClass)
							if match:
								var = match.group(1).lower()
								if strings.has_key(var):
									deviceClass = deviceClass.replace(u'%'+var+u'%', strings[var])
				
				elif (section.lower() == u'manufacturer'):
					if line and (line.find(u'=') != -1):
						for d in line.split(u'=')[1].split(u','):
							deviceSections.append(d.strip())
		
		logger.debug(u"      - Device sections: %s" % ', '.join(deviceSections))
		
		def isDeviceSection(section):
			if section in deviceSections:
				return True
			for s in section.split(u'.', 1):
				if not s in deviceSections:
					return False
			return True
		
		found = []
		section = ''
		sectionsParsed = []
		for line in lines:
			try:
				match = re.search(self.sectionRegex, line)
				if match:
					if section and isDeviceSection(section):
						sectionsParsed.append(section)
					section = match.group(1)
					if isDeviceSection(section): logger.debug(u"   - Parsing device section: %s" % section)
				else:
					if isDeviceSection(section) and not section in sectionsParsed:
						try:
							if (line.find('=') == -1) or (line.find(',') == -1):
								continue
							devString = line.split(u'=')[1].split(u',')[1].strip()
							logger.debug(u"      - Processing device string: %s" % devString)
							type = ''
							match = re.search(self.hdaudioDeviceRegex, devString)
							if match:
								type = u'HDAUDIO'
							else:
								match = re.search(self.pciDeviceRegex, devString)
								if match:
									type = u'PCI'
								else:
									match = re.search(self.usbDeviceRegex, devString)
									if match:
										type = u'USB'
									else:
										match = re.search(self.acpiDeviceRegex, devString)
										if match:
											type = u'ACPI'
							if match:
								logger.debug(u"         - Device type is %s" % type)
								if (type == u'ACPI'):
									vendor = match.group(1)
									device = match.group(2)
								else:
									vendor = forceHardwareVendorId(match.group(1))
									device = forceHardwareDeviceId(match.group(2))
								if u"%s:%s" % (vendor, device) not in found:
									logger.debug(u"         - Found %s device: %s:%s" % (type, vendor, device))
									found.append(u"%s:%s:%s" % (type, vendor, device))
									self._devices.append( { 'path': path, 'class': deviceClass, 'vendor': vendor, 'device': device, 'type': type } )
						except IndexError:
							logger.warning(u"Skipping bad line '%s' in file %s" % (line, self._filename))
			except Exception, e:
				logger.error(u"Parse error in inf file '%s' line '%s': %s" % (self._filename, line, e))
		self._parsed = True


class PciidsFile(ConfigFile):
	
	def __init__(self, filename, lockFailTimeout = 2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars = [';', '#'], lstrip = False)
		self._devices = {}
		self._vendors = {}
		self._subDevices = {}
		
	def getVendor(self, vendorId):
		vendorId = forceHardwareVendorId(vendorId)
		if not self._parsed:
			self.parse()
		return self._vendors.get(vendorId, None)
	
	def getDevice(self, vendorId, deviceId):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		if not self._parsed:
			self.parse()
		return self._devices.get(vendorId, {}).get(deviceId, None)
	
	def getSubDevice(self, vendorId, deviceId, subVendorId, subDeviceId):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		subVendorId = forceHardwareVendorId(subVendorId)
		subDeviceId = forceHardwareDeviceId(subDeviceId)
		if not self._parsed:
			self.parse()
		return self._subDevices.get(vendorId, {}).get(deviceId, {}).get(subVendorId + ':' + subDeviceId, None)
	
	def parse(self, lines=None):
		logger.debug(u"Parsing ids file %s" % self._filename)
		
		lines = ConfigFile.parse(self, lines)
		self._parsed = False
		
		self._devices = {}
		self._vendors = {}
		self._subDevices = {}
		
		currentVendorId = None
		currentDeviceId = None
		for line in lines:
			try:
				if line.startswith(u'C '):
					# Start of list of known device classes, subclasses and programming interfaces
					break
				
				if line.startswith(u'\t'):
					if not currentVendorId or not self._devices.has_key(currentVendorId):
						raise Exception(u"Parse error in file '%s': %s" % (self._filename, line))
					if line.startswith(u'\t\t'):
						if not currentDeviceId or not self._subDevices.has_key(currentVendorId) or not self._subDevices[currentVendorId].has_key(currentDeviceId):
							raise Exception(u"Parse error in file '%s': %s" % (self._filename, line))
						(subVendorId, subDeviceId, subName) = line.lstrip().split(None, 2)
						subVendorId = forceHardwareVendorId(subVendorId)
						subDeviceId = forceHardwareDeviceId(subDeviceId)
						self._subDevices[currentVendorId][currentDeviceId][subVendorId + ':' + subDeviceId] = subName.strip()
					else:
						(deviceId, deviceName) = line.lstrip().split(None, 1)
						currentDeviceId = deviceId = forceHardwareDeviceId(deviceId)
						if not self._subDevices[vendorId].has_key(deviceId):
							self._subDevices[vendorId][deviceId] = {}
						self._devices[currentVendorId][deviceId] = deviceName.strip()
				else:
					(vendorId, vendorName) = line.split(None, 1)
					currentVendorId = vendorId = forceHardwareVendorId(vendorId)
					if not self._devices.has_key(vendorId):
						self._devices[vendorId] = {}
					if not self._subDevices.has_key(vendorId):
						self._subDevices[vendorId] = {}
					self._vendors[vendorId] = vendorName.strip()
			except Exception, e:
				logger.error(e)
		self._parsed = True

UsbidsFile = PciidsFile

class TxtSetupOemFile(ConfigFile):
	sectionRegex     = re.compile('\[\s*([^\]]+)\s*\]')
	pciDeviceRegex   = re.compile('VEN_([\da-fA-F]+)(&DEV_([\da-fA-F]+))?')
	usbDeviceRegex   = re.compile('USB.*VID_([\da-fA-F]+)(&PID_([\da-fA-F]+))', re.IGNORECASE)
	filesRegex       = re.compile('files\.(computer|display|keyboard|mouse|scsi)\.(.+)$', re.IGNORECASE)
	hardwareIdsRegex = re.compile('hardwareids\.(computer|display|keyboard|mouse|scsi)\.(.+)$', re.IGNORECASE)
	
	def __init__(self, filename, lockFailTimeout = 2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars = [';', '#'])
		self._devices = []
		self._files = []
		self._componentNames = []
		self._componentOptions = []
		self._defaultComponentIds = []
		self._serviceNames = []
		self._driverDisks = []
		
	def getDevices(self):
		if not self._parsed:
			self.parse()
		return self._devices
	
	def isDeviceKnown(self, vendorId, deviceId, deviceType = None):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		for d in self._devices:
			if (not deviceType or (d.get('type') == deviceType)) and (d.get('vendor') == vendorId) and (not d.get('device') or d['device'] == deviceId):
				continue
			return True
		return False
	
	def getFilesForDevice(self, vendorId, deviceId, deviceType = None, fileTypes = []):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		fileTypes = forceUnicodeLowerList(fileTypes)
		if not self._parsed:
			self.parse()
		device = None
		for d in self._devices:
			if (not deviceType or (d.get('type') == deviceType)) and (d.get('vendor') == vendorId) and (not d.get('device') or d['device'] == deviceId):
				device = d
				break
		if not device:
			raise Exception(u"Device '%s:%s' not found in txtsetup.oem file '%s'" % (vendorId, deviceId, self._filename))
		files = []
		diskDriverDirs = {}
		for d in self._driverDisks:
			diskDriverDirs[d["diskName"]] = d["driverDir"]
		
		for f in self._files:
			if (f['componentName'] != device['componentName']) or (f['componentId'] != device['componentId']):
				continue
			if fileTypes and f['fileType'] not in fileTypes:
				continue
			if not diskDriverDirs.has_key(f['diskName']):
				raise Exception(u"Driver disk for file %s not found in txtsetup.oem file '%s'" % (f, self._filename))
			files.append(os.path.join(diskDriverDirs[f['diskName']], f['filename']))
		return files
		
	def parse(self, lines=None):
		logger.debug(u"Parsing txtsetup.oem file %s" % self._filename)
		lines = ConfigFile.parse(self, lines)
		self._parsed = False
		
		self._devices = []
		self._files = []
		self._componentNames = []
		self._componentOptions = []
		self._defaultComponentIds = []
		self._serviceNames = []
		self._driverDisks = []
		
		sections = {}
		section = None
		for line in lines:
			logger.debug2(u"txtsetup.oem: %s" % line)
			match = re.search(self.sectionRegex, line)
			if match:
				section = match.group(1)
				sections[section] = []
			elif section:
				sections[section].append(line)
		
		# Search for component options
		logger.info(u"Searching for component names and options")
		for (section, lines) in sections.items():
			if not section.lower() in ('computer', 'display', 'keyboard', 'mouse', 'scsi'):
				continue
			componentName = section.lower()
			for line in lines:
				if (line.find(u'=') == -1):
					continue
				optionName = None
				(optionId, value) = line.split('=', 1)
				optionId = optionId.strip()
				if (value.find(u',') != -1):
					(description, optionName) = value.split(',', 1)
					optionName = optionName.strip()
				else:
					description = value
				description = description.strip()
				if description.startswith(u'"') and description.endswith(u'"'):
					description = description[1:-1]
				if not componentName in self._componentNames:
					self._componentNames.append(componentName)
					self._componentOptions.append({"componentName": componentName, "description": description, "optionName": optionName })
				
		logger.info(u"Component names found: %s" % self._componentNames)
		logger.info(u"Component options found: %s" % self._componentOptions)
		
		# Search for default component ids
		logger.info(u"Searching for default component ids")
		for (section, lines) in sections.items():
			if (section.lower() != 'defaults'):
				continue
			for line in lines:
				(componentName, componentId) = line.split('=', 1)
				self._defaultComponentIds.append({ 'componentName': componentName.strip().lower(), 'componentId': componentId.strip() })
		
		if not self._defaultComponentIds:
			logger.info(u"No default component ids found")
		else:
			logger.info(u"Found default component ids: %s" % self._defaultComponentIds)
		
		# Search for hardware ids
		logger.info(u"Searching for devices")
		for (section, lines) in sections.items():
			match = re.search(self.hardwareIdsRegex, section)
			if not match:
				continue
			componentName = match.group(1).lower()
			componentId   = match.group(2)
			logger.info(u"Found hardwareIds section '%s', component name '%s', component id '%s'" % (section, componentName, componentId))
			found = []
			for line in lines:
				if not re.search('[iI][dD]\s*=', line):
					continue
				(device, serviceName) = line.split(u'=', 1)[1].strip().split(u',', 1)
				device = device.strip()
				if device.startswith(u'"') and device.endswith(u'"'):
					device = device[1:-1]
				serviceName = serviceName.strip()
				if serviceName.startswith(u'"') and serviceName.endswith(u'"'):
					serviceName = serviceName[1:-1]
				match = re.search(self.pciDeviceRegex, device)
				if match:
					type = u'PCI'
				else:
					match = re.search(self.usbDeviceRegex, device)
					if match:
						type = u'USB'
					else:
						logger.error(u"Parse error: =>%s<=" % device)
				if (type != u'PCI'):
					continue
				vendor = forceHardwareVendorId(match.group(1))
				device = None
				if match.group(2):
					device = forceHardwareDeviceId(match.group(3))
				
				if u"%s:%s" % (vendor, device) not in found:
					logger.debug(u"   Found %s device: %s:%s, service name: %s" % (type, vendor, device, serviceName))
					found.append(u"%s:%s:%s" % (type, vendor, device))
					self._devices.append( { 'vendor': vendor, 'device': device, 'type': type, 'serviceName': serviceName, 'componentName': componentName, 'componentId': componentId } )
					if not serviceName in self._serviceNames:
						self._serviceNames.append(serviceName)
		
		if not self._devices:
			raise Exception(u"No devices found in txtsetup file '%s'" % self._filename)
		
		logger.info(u"Found services: %s" % self._serviceNames)
		logger.debug(u"Found devices: %s" % self._devices)
		
		# Search for disks
		logger.info(u"Searching for disks")
		for (section, lines) in sections.items():
			if (section.lower() != 'disks'):
				continue
			for line in lines:
				if (line.find(u'=') == -1):
					continue
				(diskName, value) = line.split('=', 1)
				diskName = diskName.strip()
				(desc, tf, dd) = value.split(',', 2)
				desc = desc.strip()
				if desc.startswith(u'"') and desc.endswith(u'"'):
					desc = desc[1:-1]
				tf = tf.strip()
				if tf.startswith(u'\\'): tf = tf[1:]
				dd = dd.strip()
				if dd.startswith(u'\\'): dd = dd[1:]
				self._driverDisks.append({"diskName": diskName, "description": desc, "tagfile": tf, "driverDir": dd })
		if not self._driverDisks:
			raise Exception(u"No driver disks found in txtsetup file '%s'" % self._filename)
		logger.info(u"Found driver disks: %s" % self._driverDisks)
		
		# Search for files
		logger.info(u"Searching for files")
		for (section, lines) in sections.items():
			match = re.search(self.filesRegex, section)
			if not match:
				continue
			componentName = match.group(1).lower()
			componentId   = match.group(2)
			logger.info(u"Found files section '%s', component name '%s', component id '%s'" % (section, componentName, componentId))
			for line in lines:
				(fileType, value) = line.split(u'=', 1)
				fileType = fileType.strip()
				diskName = value.split(u',')[0].strip()
				filename = value.split(u',')[1].strip()
				self._files.append({ 'fileType': fileType, 'diskName': diskName, 'filename': filename, 'componentName': componentName, 'componentId': componentId })
		logger.debug(u"Found files: %s" % self._files)
		
		self._parsed = True










class DHCPDConf_Component(object):
	def __init__(self, startLine, parentBlock):
		self.startLine = startLine
		self.endLine = startLine
		self.parentBlock = parentBlock
	
	def getShifting(self):
		shifting = u''
		if not self.parentBlock:
			return shifting
		parentBlock = self.parentBlock.parentBlock
		while(parentBlock):
			shifting += u'\t'
			parentBlock = parentBlock.parentBlock
		return shifting
	
	def asText(self):
		return self.getShifting()
	
	def __repr__(self):
		return '<%s line %d-%d>' % (self.__class__.__name__, self.startLine, self.endLine)
		
class DHCPDConf_Parameter(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, key, value):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.key = key
		self.value = value
		if type(self.value) in (unicode, str):
			if self.value.lower() in [u'yes', u'true', u'on']:
				self.value = True
			elif self.value.lower() in [u'no', u'false', u'off']:
				self.value = False
	
	def asText(self):
		value = self.value
		if type(value) is bool:
			if value:
				value = u'on'
			else:
				value = u'off'
		elif self.key in [u'filename', u'ddns-domainname'] or \
		     re.match('.*[\'/\\\].*', value) or \
		     re.match('^\w+\.\w+$', value) or \
		     self.key.endswith(u'-name'):
			value = u'"%s"' % value
		return u"%s%s %s;" % (self.getShifting(), self.key, value)
	
	def asHash(self):
		return { self.key: self.value }
	
class DHCPDConf_Option(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, key, value):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.key = key
		self.value = value
		if not type(self.value) is list:
			self.value = [ self.value ]
	def asText(self):
		text = u"%soption %s " % (self.getShifting(), self.key)
		for i in range(len(self.value)):
			value = self.value[i]
			if re.match('.*[\'/\\\].*', value) or \
			   re.match('^\w+\.\w+$', value) or \
			   self.key.endswith(u'-name') or \
			   self.key.endswith(u'-identifier'):
				value = u'"%s"' % value
			if (i+1 < len(self.value)):
				value += u', '
			text += value
		return text + u';'
	
	def asHash(self):
		return { self.key: self.value }
	
class DHCPDConf_Comment(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, data):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self._data = data
	
	def asText(self):
		return self.getShifting() + u'#%s' % self._data
	
class DHCPDConf_EmptyLine(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
	
class DHCPDConf_Block(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, type, settings = []):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.type = type
		self.settings = settings
		self.lineRefs = {}
		self.components = []
		
	def getComponents(self):
		return self.components
	
	def removeComponents(self):
		logger.debug(u"Removing components: %s" % self.components)
		for c in forceList(self.components):
			self.removeComponent(c)
		
	def addComponent(self, component):
		self.components.append(component)
		if not self.lineRefs.has_key(component.startLine):
			self.lineRefs[component.startLine] = []
		self.lineRefs[component.startLine].append(component)
	
	def removeComponent(self, component):
		index = -1
		for i in range(len(self.components)):
			if (self.components[i] == component):
				index = i
				break
		if (index < 0):
			raise BackendMissingDataError(u"Component '%s' not found")
		del self.components[index]
		index = -1
		
		if self.lineRefs.has_key(component.startLine):
			for i in range(len(self.lineRefs[component.startLine])):
				if (self.lineRefs[component.startLine][i] == component):
					index = i
					break
		if (index >= 0):
			del self.lineRefs[component.startLine][index]
		
	def getOptions_hash(self, inherit = None):
		options = {}
		for component in self.components:
			if not isinstance(component, DHCPDConf_Option):
				continue
			options[component.key] = component.value
		
		if inherit and (self.type != inherit) and self.parentBlock:
			for (key, value) in self.parentBlock.getOptions_hash(inherit).items():
				if not options.has_key(key):
					options[key] = value
		return options
	
	def getOptions(self, inherit = None):
		options = []
		for component in self.components:
			if not isinstance(component, DHCPDConf_Option):
				continue
			options.append(component)
		
		if inherit and (self.type != inherit) and self.parentBlock:
			options.extend(self.parentBlock.getOptions(inherit))
		
		return options
	
	def getParameters_hash(self, inherit = None):
		parameters = {}
		for component in self.components:
			if not isinstance(component, DHCPDConf_Parameter):
				continue
			parameters[component.key] = component.value
		
		if inherit and (self.type != inherit) and self.parentBlock:
			for (key, value) in self.parentBlock.getParameters_hash(inherit).items():
				if not parameters.has_key(key):
					parameters[key] = value
		return parameters
	
	def getParameters(self, inherit = None):
		parameters = []
		for component in self.components:
			if not isinstance(component, DHCPDConf_Parameter):
				continue
			options.append(component)
		
		if inherit and (self.type != inherit) and self.parentBlock:
			parameters.extend(self.parentBlock.getParameters(inherit))
		
		return parameters
	
	def getBlocks(self, type, recursive = False):
		blocks = []
		for component in self.components:
			if not isinstance(component, DHCPDConf_Block):
				continue
			if (component.type == type):
				blocks.append(component)
			if recursive:
				blocks.extend(component.getBlocks(type, recursive))
		return blocks
	
	def asText(self):
		text = u''
		shifting = self.getShifting()
		if not isinstance(self, DHCPDConf_GlobalBlock):
			text += shifting + u' '.join(self.settings) + u' {\n'
		
		notWritten = self.components
		lineNumber = self.startLine
		if (lineNumber < 1): lineNumber = 1
		while (lineNumber <= self.endLine):
			if not self.lineRefs.has_key(lineNumber) or not self.lineRefs[lineNumber]:
				lineNumber += 1
				continue
			for i in range(len(self.lineRefs[lineNumber])):
				compText = self.lineRefs[lineNumber][i].asText()
				if (i > 0) and isinstance(self.lineRefs[lineNumber][i], DHCPDConf_Comment):
					compText = u' ' + compText.lstrip()
				text += compText
				# Mark component as written
				if self.lineRefs[lineNumber][i] in notWritten:
					notWritten.remove(self.lineRefs[lineNumber][i])
			text += u'\n'
			lineNumber += 1
		
		for component in notWritten:
			text += component.asText() + u'\n'
		
		if not isinstance(self, DHCPDConf_GlobalBlock):
			# Write '}' to close block
			text += shifting + u'}'
		
		return text
		
class DHCPDConf_GlobalBlock(DHCPDConf_Block):
	def __init__(self):
		DHCPDConf_Block.__init__(self, 1, None, u'global')

class DHCPDConfFile(TextFile):
	
	def __init__(self, filename, lockFailTimeout = 2000):
		TextFile.__init__(self, filename, lockFailTimeout)
		
		self._currentLine = 0
		self._currentToken = None
		self._currentIndex = -1
		self._data = u''
		self._currentBlock = None
		self._globalBlock = None
		self._parsed = False
		
		logger.debug(u"Parsing dhcpd conf file '%s'" % self._filename)
	
	def getGlobalBlock(self):
		return self._globalBlock
		
	def parse(self, lines=None):
		self._currentLine = 0
		self._currentToken = None
		self._currentIndex = -1
		self._data = u''
		self._currentBlock = self._globalBlock = DHCPDConf_GlobalBlock()
		self._parsed = False
		
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._globalBlock.endLine = len(self._lines)
		
		minIndex = 0
		while True:
			self._currentToken = None
			self._currentIndex = -1
			if not self._data.strip():
				if not self._getNewData():
					break
				if not self._data.strip():
					self._parse_emptyline()
				continue
			for token in ('#', ';', '{', '}'):
				index = self._data.find(token)
				if (index != -1) and (index >= minIndex) and ((self._currentIndex == -1) or (index < self._currentIndex)):
					if (self._data[:index].count('"') % 2 == 1) or (self._data[:index].count("'") % 2 == 1):
						continue
					self._currentToken = token
					self._currentIndex = index
			if not self._currentToken:
				minIndex = len(self._data)
				if not self._getNewData():
					break
				continue
			minIndex = 0
			if   (self._currentToken == '#'):
				self._parse_comment()
			elif (self._currentToken == ';'):
				self._parse_semicolon()
			elif (self._currentToken == '{'):
				self._parse_lbracket()
			elif (self._currentToken == '}'):
				self._parse_rbracket()
		self._parsed = True
		
	def generate(self):
		if not self._globalBlock:
			raise Exception(u"Got no data to write")
		
		self.open('w')
		self.write(self._globalBlock.asText())
		self.close()
	
	def addHost(self, hostname, hardwareAddress, ipAddress, fixedAddress, parameters = {}):
		if not parameters: parameters = {}
		hostname        = forceHostname(hostname)
		hardwareAddress = forceHardwareAddress(hardwareAddress)
		ipAddress       = forceIPAddress(ipAddress)
		fixedAddress    = forceUnicodeLower(fixedAddress)
		parameters      = forceDict(parameters)
		
		if not self._parsed:
			self.parse()
		
		logger.info(u"Creating host '%s', hardwareAddress '%s', ipAddress '%s', fixedAddress '%s', parameters '%s'" % \
					(hostname, hardwareAddress, ipAddress, fixedAddress, parameters) )
		
		existingHost = None
		for block in self._globalBlock.getBlocks('host', recursive = True):
			if (block.settings[1].lower() == hostname):
				existingHost = block
			else:
				for (key, value) in block.getParameters_hash().items():
					if (key == 'fixed-address') and (value.lower() == fixedAddress):
						raise BackendBadValueError(u"Host '%s' uses the same fixed address" % block.settings[1])
					elif (key == 'hardware') and (value.lower() == 'ethernet %s' % hardwareAddress):
						raise BackendBadValueError(u"Host '%s' uses the same hardware ethernet address" % block.settings[1])
		if existingHost:
			logger.info(u"Host '%s' already exists in config file '%s', deleting first" % (hostname, self._filename))
			self.deleteHost(hostname)
		
		for (key, value) in parameters.items():
			parameters[key] = DHCPDConf_Parameter(-1, None, key, value).asHash()[key]
		
		# Calculate bitmask of host's ipaddress
		n = ipAddress.split('.')
		for i in range(4):
			n[i] = forceInt(n[i])
		ip = (n[0] << 24) + (n[1] << 16) + (n[2] << 8) + n[3]
		
		# Default parent block is global
		parentBlock = self._globalBlock
		
		# Search the right subnet block
		for block in self._globalBlock.getBlocks('subnet'):
			# Calculate bitmask of subnet
			n = (block.settings[1]).split('.')
			for i in range(4):
				n[i] = int(n[i])
			network = (n[0] << 24) + (n[1] << 16) + (n[2] << 8) + n[3]
			n = (block.settings[3]).split('.')
			for i in range(4):
				n[i] = int(n[i])
			netmask = (n[0] << 24) + (n[1] << 16) + (n[2] << 8) + n[3]
			
			wildcard = netmask ^ 0xFFFFFFFFL
			if (wildcard | ip == wildcard | network):
				# Host matches the subnet
				logger.debug(u"Choosing subnet %s/%s for host %s" % (block.settings[1], block.settings[3], hostname))
				parentBlock = block
		
		# Search the right group for the host
		bestGroup = None
		bestMatchCount = 0
		for block in parentBlock.getBlocks('group'):
			matchCount = 0
			blockParameters = block.getParameters_hash(inherit = 'global')
			if blockParameters:
				# Block has parameters set, check if they match the hosts parameters
				for (key, value) in blockParameters.items():
					if not parameters.has_key(key):
						continue
					if (parameters[key] == value):
						matchCount += 1
					else:
						matchCount -= 1
			
			if (matchCount > bestMatchCount) or (matchCount >= 0 and not bestGroup):
				matchCount = bestMatchCount
				bestGroup = block
		
		if bestGroup:
			parentBlock = bestGroup
		
		# Remove parameters which are already defined in parents
		blockParameters = parentBlock.getParameters_hash(inherit = 'global')
		if blockParameters:
			for (key, value) in blockParameters.items():
				if parameters.has_key(key) and (parameters[key] == value):
					del parameters[key]
		
		hostBlock = DHCPDConf_Block(
					startLine = -1,
					parentBlock = parentBlock,
					type = 'host',
					settings = ['host', hostname] )
		hostBlock.addComponent( DHCPDConf_Parameter( startLine = -1, parentBlock = hostBlock, key = 'fixed-address', value = fixedAddress ) )
		hostBlock.addComponent( DHCPDConf_Parameter( startLine = -1, parentBlock = hostBlock, key = 'hardware', value = "ethernet %s" % hardwareAddress ) )
		for (key, value) in parameters.items():
			hostBlock.addComponent(
				DHCPDConf_Parameter( startLine = -1, parentBlock = hostBlock, key = key, value = value ) )
		
		parentBlock.addComponent(hostBlock)
	
	def getHost(self, hostname):
		hostname = forceHostname(hostname)
		
		if not self._parsed:
			self.parse()
		
		for block in self._globalBlock.getBlocks('host', recursive = True):
			if (block.settings[1] == hostname):
				return block.getParameters_hash()
		return None
		
	def deleteHost(self, hostname):
		hostname = forceHostname(hostname)
		
		if not self._parsed:
			self.parse()
		
		logger.notice(u"Deleting host '%s' from dhcpd config file '%s'" % (hostname, self._filename))
		hostBlocks = []
		for block in self._globalBlock.getBlocks('host', recursive = True):
			if (block.settings[1] == hostname):
				hostBlocks.append(block)
			else:
				for (key, value) in block.getParameters_hash().items():
					if (key == 'fixed-address') and (value == hostname):
						hostBlocks.append(block)
		if not hostBlocks:
			logger.warning(u"Failed to remove host '%s': not found" % hostname)
			return
		
		for block in hostBlocks:
			block.parentBlock.removeComponent(block)
	
	def modifyHost(self, hostname, parameters):
		hostname   = forceHostname(hostname)
		parameters = forceDict(parameters)
		
		if not self._parsed:
			self.parse()
		
		logger.notice(u"Modifying host '%s' in dhcpd config file '%s'" % (hostname, self.filename))
		
		hostBlocks = []
		for block in self._globalBlock.getBlocks('host', recursive = True):
			if (block.settings[1] == hostname):
				hostBlocks.append(block)
			else:
				for (key, value) in block.getParameters_hash().items():
					if (key == 'fixed-address') and (value == hostname):
						hostBlocks.append(block)
					elif (key == 'hardware') and (value.lower() == parameters.get('hardware')):
						raise BackendBadValueError(u"Host '%s' uses the same hardware ethernet address" % block.settings[1])
		if (len(hostBlocks) != 1):
			raise BackendBadValueError(u"Host '%s' found %d times" % (hostname, len(hostBlocks)))
		
		hostBlock = hostBlocks[0]
		hostBlock.removeComponents()
		
		for (key, value) in parameters.items():
			parameters[key] = Parameter(-1, None, key, value).asHash()[key]
		
		for (key, value) in hostBlock.parentBlock.getParameters_hash(inherit = 'global').items():
			if not parameters.has_key(key):
				continue
			if (parameters[key] == value):
				del parameters[key]
		
		for (key, value) in parameters.items():
			hostBlock.addComponent(
				DHCPDConf_Parameter( startLine = -1, parentBlock = hostBlock, key = key, value = value ) )
		
	def _getNewData(self):
		if (self._currentLine >= len(self._lines)):
			return False
		self._data += self._lines[self._currentLine]
		self._currentLine += 1
		return True
	
	def _parse_emptyline(self):
		logger.debug(u"_parse_emptyline")
		self._currentBlock.addComponent(
			DHCPDConf_EmptyLine(
				startLine   = self._currentLine,
				parentBlock = self._currentBlock
			)
		)
		self._data = self._data[:self._currentIndex]
	
	def _parse_comment(self):
		logger.debug(u"_parse_comment")
		self._currentBlock.addComponent(
			DHCPDConf_Comment(
				startLine   = self._currentLine,
				parentBlock = self._currentBlock,
				data        = self._data.strip()[1:]
			)
		)
		self._data = self._data[:self._currentIndex]
		
	def _parse_semicolon(self):
		logger.debug(u"_parse_semicolon")
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex+1:]
		
		key = data.split()[0]
		if (key != 'option'):
			# Parameter
			value = u' '.join(data.split()[1:]).strip()
			if (len(value) > 1) and value.startswith('"') and value.endswith('"'):
				value = value[1:-1]
			self._currentBlock.addComponent(
				DHCPDConf_Parameter(
					startLine   = self._currentLine,
					parentBlock = self._currentBlock,
					key         = key,
					value       = value
				)
			)
			return
		
		# Option
		key = data.split()[1]
		value = u' '.join(data.split()[2:]).strip()
		if (len(value) > 1) and value.startswith('"') and value.endswith('"'):
			value = value[1:-1]
		values  = []
		quote   = u''
		current = u''
		for l in value:
			if   (l == u'"'):
				if   (quote == u'"'):
					quote = u''
				elif (quote == u"'"):
					current += l
				else:
					quote = u'"'
			elif (l == u"'"):
				if   (quote == u"'"):
					quote = u''
				elif (quote == u'"'):
					current += l
				else:
					quote = u"'"
			elif re.search('\s', l):
				current += l
			elif (l == u','):
				if quote:
					current += l
				else:
					values.append(current.strip())
					current = u''
			else:
				current += l
		if current:
			values.append(current.strip())
		
		self._currentBlock.addComponent(
			DHCPDConf_Option(
				startLine   = self._currentLine,
				parentBlock = self._currentBlock,
				key         = key,
				value       = values
			)
		)
		
	def _parse_lbracket(self):
		logger.debug(u"_parse_lbracket")
		# Start of a block
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex+1:]
		# Split the block definition at whitespace
		# The first value is the block type
		# Example: subnet 194.31.185.0 netmask 255.255.255.0 => type is subnet
		block = DHCPDConf_Block(
			startLine   = self._currentLine,
			parentBlock = self._currentBlock,
			type        = data.split()[0].strip(),
			settings    = data.split()
		)
		self._currentBlock.addComponent(block)
		self._currentBlock = block
		
	def _parse_rbracket(self):
		logger.debug(u"_parse_rbracket")
		# End of a block
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex+1:]
		
		self._currentBlock.endLine = self._currentLine
		self._currentBlock = self._currentBlock.parentBlock
	
	
infTestData = [
'''
; SMBUSati.inf
;
; Installation file (.inf) for the ATI SMBus device.
;
; (c) Copyright 2002-2006 ATI Technologies Inc
;

[Version]
Signature="$CHICAGO$"
Provider=%ATI%
ClassGUID={4d36e97d-e325-11ce-bfc1-08002be10318}
Class=System
CatalogFile=SMbusati.cat
DriverVer=02/26/2007,5.10.1000.8

[DestinationDirs]
DefaultDestDir   = 12

;
; Driver information
;

[Manufacturer]
%ATI%   = ATI.Mfg, NTamd64


[ATI.Mfg]
%ATI.DeviceDesc0% = ATISMBus, PCI\VEN_1002&DEV_4353
%ATI.DeviceDesc0% = ATISMBus, PCI\VEN_1002&DEV_4363
%ATI.DeviceDesc0% = ATISMBus, PCI\VEN_1002&DEV_4372
%ATI.DeviceDesc0% = ATISMBus, PCI\VEN_1002&DEV_4385

[ATI.Mfg.NTamd64]
%ATI.DeviceDesc0% = ATISMBus64, PCI\VEN_1002&DEV_4353
%ATI.DeviceDesc0% = ATISMBus64, PCI\VEN_1002&DEV_4363
%ATI.DeviceDesc0% = ATISMBus64, PCI\VEN_1002&DEV_4372
%ATI.DeviceDesc0% = ATISMBus64, PCI\VEN_1002&DEV_4385

;
; General installation section
;

[ATISMBus]
AddReg=Install.AddReg

[ATISMBus64]
AddReg=Install.AddReg.NTamd64

;
; Service Installation
;                     

[ATISMBus.Services]
AddService = , 0x00000002

[ATISMBus64.Services]
AddService = , 0x00000002

[ATISMBus_Service_Inst]
ServiceType    = 1                  ; SERVICE_KERNEL_DRIVER
StartType      = 3                  ; SERVICE_DEMAND_START 
ErrorControl   = 0                  ; SERVICE_ERROR_IGNORE
LoadOrderGroup = Pointer Port

[ATISMBus_EventLog_Inst]
AddReg = ATISMBus_EventLog_AddReg

[ATISMBus_EventLog_AddReg]

[Install.AddReg]
HKLM,"Software\ATI Technologies\Install\South Bridge\SMBus",DisplayName,,"ATI SMBus"
HKLM,"Software\ATI Technologies\Install\South Bridge\SMBus",Version,,"5.10.1000.8"
HKLM,"Software\ATI Technologies\Install\South Bridge\SMBus",Install,,"Success"

[Install.AddReg.NTamd64]
HKLM,"Software\Wow6432Node\ATI Technologies\Install\South Bridge\SMBus",DisplayName,,"ATI SMBus"
HKLM,"Software\Wow6432Node\ATI Technologies\Install\South Bridge\SMBus",Version,,"5.10.1000.8"
HKLM,"Software\Wow6432Node\ATI Technologies\Install\South Bridge\SMBus",Install,,"Success"

;
; Source file information
;

[SourceDisksNames]
1 = %DiskId1%,,,

[SourceDisksFiles]
; Files for disk ATI Technologies Inc Installation Disk #1 (System)

[Strings]

;
; Non-Localizable Strings
;

REG_SZ         = 0x00000000
REG_MULTI_SZ   = 0x00010000
REG_EXPAND_SZ  = 0x00020000
REG_BINARY     = 0x00000001
REG_DWORD      = 0x00010001
SERVICEROOT    = "System\CurrentControlSet\Services"

;
; Localizable Strings
;

ATI.DeviceDesc0 = "ATI SMBus"
DiskId1 = "ATI Technologies Inc Installation Disk #1 (System)"
ATI = "ATI Technologies Inc"
''',
'''
[Version]
Signature="$WINDOWS NT$"
Class=Processor
ClassGuid={50127DC3-0F36-415e-A6CC-4CB3BE910B65}
Provider=%AMD%
DriverVer=10/26/2004, 1.2.2.0
CatalogFile=AmdK8.cat

[DestinationDirs]
DefaultDestDir = 12

[SourceDisksNames]
1 = %DiskDesc%,,, 

[SourceDisksFiles]
AmdK8.sys = 1

[ControlFlags]
;
; Exclude all devices from Select Device list
;
ExcludeFromSelect = *

[ClassInstall32]
AddReg=Processor_Class_Addreg

[Processor_Class_Addreg]
HKR,,,0,%ProcessorClassName%
HKR,,NoInstallClass,,1
HKR,,Icon,,"-28"

[Manufacturer]
%AMD%=AmdK8

[AmdK8]
%AmdK8.DeviceDesc% = AmdK8_Inst,ACPI\AuthenticAMD_-_x86_Family_15
%AmdK8.DeviceDesc% = AmdK8_Inst,ACPI\AuthenticAMD_-_AMD64_Family_15

[AmdK8_Inst.NT]
Copyfiles = @AmdK8.sys

[AmdK8_Inst.NT.Services]
AddService = AmdK8,%SPSVCINST_ASSOCSERVICE%,AmdK8_Service_Inst,AmdK8_EventLog_Inst

[AmdK8_Service_Inst]
DisplayName    = %AmdK8.SvcDesc%
ServiceType    = %SERVICE_KERNEL_DRIVER%
StartType      = %SERVICE_SYSTEM_START%
ErrorControl   = %SERVICE_ERROR_NORMAL%
ServiceBinary  = %12%\AmdK8.sys
LoadOrderGroup = Extended Base
AddReg         = AmdK8_Inst_AddReg

[AmdK8_Inst_AddReg]
HKR,"Parameters",Capabilities,0x00010001,0x80

[AmdK8_EventLog_Inst]
AddReg = AmdK8_EventLog_AddReg

[AmdK8_EventLog_AddReg]
HKR,,EventMessageFile,0x00020000,"%%SystemRoot%%\System32\IoLogMsg.dll;%%SystemRoot%%\System32\drivers\AmdK8.sys"
HKR,,TypesSupported,0x00010001,7

[strings]
AMD                   = "Advanced Micro Devices"
ProcessorClassName    = "Processors"
AmdK8.DeviceDesc      = "AMD K8 Processor"
AmdK8.SvcDesc         = "AMD Processor Driver"
DiskDesc              = "AMD Processor Driver Disk"

SPSVCINST_ASSOCSERVICE= 0x00000002
SERVICE_KERNEL_DRIVER = 1
SERVICE_SYSTEM_START  = 1
SERVICE_ERROR_NORMAL  = 1
''',
'''
;
; SYMMPI.INF - version XP.10 (Windows XP)
;
; This is the INF file for Windows XP for the SYMMPI based PCI MPI
; environment
;
; ********************************************************************
;                                                                    *
;   Copyright 2005 LSI Logic, Inc. All rights reserved.              *
;                                                                    *
;   This file is property of LSI Logic, Inc. and is licensed for     *
;   use as is.  The receipt of or possession of this file does not   *
;   convey any rights to modify its contents, in whole, or in part,  *
;   without the specific written consent of LSI Logic, Inc.          *
;                                                                    *
; ********************************************************************

[version]
signature="$Windows NT$"
Class=SCSIAdapter
ClassGUID={4D36E97B-E325-11CE-BFC1-08002BE10318}
Provider=%LSI%
DriverVer=08/04/2006,1.21.25.00
CatalogFile.ntx86=mpixp32.cat

[DestinationDirs]
DefaultDestDir = 12 ; DIRID_DRIVERS

[SourceDisksFiles.x86]
symmpi.sys = 1
lsipseud.inf = 1

[SourceDisksNames]
1 = %DiskDesc%,,

[Manufacturer]
%LSI%=LSI
%DELL%=DELL

[LSI]
%DevDesc2% = SYMMPI_Inst, PCI\VEN_1000&DEV_0622
%DevDesc3% = SYMMPI_Inst, PCI\VEN_1000&DEV_0624
%DevDesc4% = SYMMPI_Inst, PCI\VEN_1000&DEV_0626
%DevDesc5% = SYMMPI_Inst, PCI\VEN_1000&DEV_0628
%DevDesc6% = SYMMPI_Inst, PCI\VEN_1000&DEV_0030
%DevDesc7% = SYMMPI_Inst, PCI\VEN_1000&DEV_0032
%DevDesc8% = SYMMPI_Inst, PCI\VEN_1000&DEV_0050
%DevDesc9% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054
%DevDesc10% = SYMMPI_Inst, PCI\VEN_1000&DEV_0058
%DevDesc11% = SYMMPI_Inst, PCI\VEN_1000&DEV_0056
%DevDesc12% = SYMMPI_Inst, PCI\VEN_1000&DEV_0640
%DevDesc13% = SYMMPI_Inst, PCI\VEN_1000&DEV_0646
%DevDesc14% = SYMMPI_Inst, PCI\VEN_1000&DEV_0062

[DELL]
%DevDescD1% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F041028
%DevDescD2% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F051028
%DevDescD3% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F061028
%DevDescD4% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F071028
%DevDescD5% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F081028
%DevDescD6% = SYMMPI_Inst, PCI\VEN_1000&DEV_0054&SUBSYS_1F091028
%DevDescD7% = SYMMPI_Inst, PCI\VEN_1000&DEV_0058&SUBSYS_1F0E1028
%DevDescD8% = SYMMPI_Inst, PCI\VEN_1000&DEV_0058&SUBSYS_1F0F1028
%DevDescD9% = SYMMPI_Inst, PCI\VEN_1000&DEV_0058&SUBSYS_1F101028

[ControlFlags]
ExcludeFromSelect = *

[SYMMPI_Inst]
CopyFiles = SYMMPI_CopyFiles
AddReg = SYMMPI_AddReg
CopyINF = lsipseud.inf

[SYMMPI_Inst.HW]
AddReg = Shutdown_addreg
DelReg = LegacyScsiportValues

[SYMMPI_Inst.Services]
AddService = SYMMPI, %SPSVCINST_ASSOCSERVICE%, SYMMPI_Service_Inst, Miniport_EventLog_Inst

[SYMMPI_Service_Inst]
ServiceType    = %SERVICE_KERNEL_DRIVER%
StartType      = %SERVICE_BOOT_START%
ErrorControl   = %SERVICE_ERROR_NORMAL%
ServiceBinary  = %12%\symmpi.sys
LoadOrderGroup = SCSI Miniport
AddReg         = pnpsafe_pci_addreg
AddReg         = bus_type_scsi

[SYMMPI_CopyFiles]
symmpi.sys,,,1

[SYMMPI_AddReg]
HKLM,SYSTEM\CurrentControlSet\Services\Symmpi\Parameters\Device,DriverParameter,0x00000002,"EnablePseudoDevice=1;"
HKLM,SYSTEM\CurrentControlSet\Services\Symmpi\Parameters\Device,MaximumSGList,0x00010001,0xFF
HKLM,SYSTEM\CurrentControlSet\Services\Symmpi\Parameters\Device,NumberOfRequests,0x00010001,0xFF

[Shutdown_addreg]
HKR,"ScsiPort","NeedsSystemShutdownNotification",0x00010001,1

[LegacyScsiportValues]
HKR,Scsiport,BusNumber
HKR,Scsiport,LegacyInterfaceType
HKR,Scsiport,SlotNumber

[pnpsafe_pci_addreg]
HKR, "Parameters\PnpInterface", "5", 0x00010001, 0x00000001

[bus_type_scsi]
HKR, "Parameters", "BusType", 0x00010001, 0x00000001

[Miniport_EventLog_Inst]
AddReg = Miniport_EventLog_AddReg

[Miniport_EventLog_AddReg]
HKR,,EventMessageFile,%REG_EXPAND_SZ%,"%%SystemRoot%%\System32\IoLogMsg.dll"
HKR,,TypesSupported,%REG_DWORD%,7

[Strings]
LSI = "LSI Logic"
DELL = "Dell"
DiskDesc = "LSI Logic PCI Fusion-MPT Driver Install Disk"
DevDesc2 = "LSI Adapter, 2Gb FC, models 44929, G2 with 929"
DevDesc3 = "LSI Adapter, 2Gb FC, models 40919 with 919"
DevDesc4 = "LSI Adapter, 2Gb FC, models 7202,7402 with 929X"
DevDesc5 = "LSI Adapter, 2Gb FC, models 7102 with 919X"
DevDesc6 = "LSI Adapter, Ultra320 SCSI 2000 series, w/1020/1030"
DevDesc7 = "LSI Adapter, Ultra320 SCSI RAID series, w/1035"
DevDesc8 = "LSI Adapter, SAS 3000 series, 4-port with 1064"
DevDesc9 = "LSI Adapter, SAS 3000 series, 8-port with 1068"
DevDesc10 = "LSI Adapter, SAS 3000 series, 8-port with 1068E"
DevDesc11 = "LSI Adapter, SAS 3000 series, 4-port with 1064E"
DevDesc12 = "LSI Adapter, 4Gb FC, models 7104,7204,7404 with 949X"
DevDesc13 = "LSI Adapter, 4Gb FC, models 7104,7204,7404 with 949E"
DevDesc14 = "LSI Adapter, SAS RAID-on-Chip, 8-port with 1078"
DevDescD1 = "Dell SAS 5/E Adapter"
DevDescD2 = "Dell SAS 5/i Adapter"
DevDescD3 = "Dell SAS 5/i Integrated"
DevDescD4 = "Dell SAS 5/iR Integrated D/C"
DevDescD5 = "Dell SAS 5/iR Integrated Emb"
DevDescD6 = "Dell SAS 5/iR Adapter"
DevDescD7 = "Dell SAS 6/iR Adapter"
DevDescD8 = "Dell SAS 6/iR Integrated"
DevDescD9 = "Dell SAS 6/i Integrated"

;*******************************************
;Handy macro substitutions (non-localizable)
SPSVCINST_ASSOCSERVICE = 0x00000002
SERVICE_KERNEL_DRIVER  = 1
SERVICE_BOOT_START     = 0
SERVICE_ERROR_NORMAL   = 1
REG_EXPAND_SZ          = 0x00020000
REG_DWORD              = 0x00010001
'''
,
'''
;
;   SER2PL.INF (for Windows 2000)
;
;   Copyright (c) 2000, Prolific Technology Inc.

[version]
signature="$Windows NT$"
Class=Ports
ClassGuid={4D36E978-E325-11CE-BFC1-08002BE10318}
Provider=%Pro%
catalogfile=pl2303.cat
DriverVer=12/31/2002,2.0.0.7

[SourceDisksNames]
1=%Pro.Disk%,,,

[ControlFlags]
ExcludeFromSelect = USB\VID_067b&PID_2303

[SourceDisksFiles]
ser2pl.sys=1

[DestinationDirs]
DefaultDestDir=12
ComPort.NT.Copy=12

[Manufacturer]
%Pro%=Pro

[Pro]
%DeviceDesc% = ComPort, USB\VID_067B&PID_2303

[ComPort.NT]
CopyFiles=ComPort.NT.Copy
AddReg=ComPort.NT.AddReg

[ComPort.NT.HW]
AddReg=ComPort.NT.HW.AddReg

[ComPort.NT.Copy]
ser2pl.sys

[ComPort.NT.AddReg]
HKR,,DevLoader,,*ntkern
HKR,,NTMPDriver,,ser2pl.sys
HKR,,EnumPropPages32,,"MsPorts.dll,SerialPortPropPageProvider"

[ComPort.NT.HW.AddReg]
HKR,,"UpperFilters",0x00010000,"serenum"

[ComPort.NT.Services]
AddService = Ser2pl, 0x00000002, Serial_Service_Inst
AddService = Serenum,,Serenum_Service_Inst

[Serial_Service_Inst]
DisplayName    = %Serial.SVCDESC%
ServiceType    = 1               ; SERVICE_KERNEL_DRIVER
StartType      = 3               ; SERVICE_SYSTEM_START (this driver may do detection)
ErrorControl   = 1               ; SERVICE_ERROR_IGNORE
ServiceBinary  = %12%\ser2pl.sys
LoadOrderGroup = Base

[Serenum_Service_Inst]
DisplayName    = %Serenum.SVCDESC%
ServiceType    = 1               ; SERVICE_KERNEL_DRIVER
StartType      = 3               ; SERVICE_DEMAND_START
ErrorControl   = 1               ; SERVICE_ERROR_NORMAL
ServiceBinary  = %12%\serenum.sys
LoadOrderGroup = PNP Filter

[linji]
Pro = "Prolific"
Pro.Disk="USB-Serial Cable Diskette"
DeviceDesc = "Prolific USB-to-Serial Comm Port"
Serial.SVCDESC   = "Prolific Serial port driver"
Serenum.SVCDESC = "Serenum Filter Driver"
'''
,
'''
[Version]
CatalogFile=RTHDMI32.cat
Signature = "$chicago$"
Class=MEDIA
ClassGuid={4d36e96c-e325-11ce-bfc1-08002be10318}
Provider=%OrganizationName%
DriverPackageType=PlugAndPlay
DriverPackageDisplayName=%PackageDisplayName%
DriverVer=03/02/2007, 5.10.0.5368

[Manufacturer]
%MfgName% = AzaliaManufacturerID

[ControlFlags]
ExcludeFromSelect = *

[AzaliaManufacturerID]
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_791A
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_793C
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_AA01
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_AA09
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_AA11
"ATI HDMI Audio" = RtAzAudModel, HDAUDIO\FUNC_01&VEN_1002&DEV_AA19

[SourceDisksNames]
222="Realtek HD Audio Installation Disk",,,

[SourceDisksFiles]
RtHDMI.sys=222
RtkUpd.exe=222

[DestinationDirs]
DefaultDestDir=10; dirid = \system32\drivers
RtAzAudModelCopyFiles = 10,system32\drivers
RTUninstall.CopyList = 10           ;; WINDOWS

[RtAzAudModelCopyFiles]
RtHDMI.sys

[RTUninstall.CopyList]
RtkUpd.exe

[RtAzAudModel.NTX86]
Include=ks.inf,wdmaudio.inf
Needs=KS.Registration,WDMAUDIO.Registration
CopyFiles = RtAzAudModelCopyFiles, RTUninstall.CopyList
AddReg    = RtAzAudModelAddReg, DS3DConfiguration.AddReg, RTUninstall.AddReg

[RtAzAudModel.NTX86.HW]
AddReg=HdAudSecurity.AddReg

[RtAzAudModel.NTX86.Services]
AddService = RTHDMIAzAudService, 0x00000002, RTHDMIAzAudServiceInstall

[RTHDMIAzAudServiceInstall]
DisplayName   = "Service for HDMI"
ServiceType   = 1
StartType     = 3
ErrorControl  = 1
ServiceBinary = %10%\system32\drivers\RtHDMI.sys


[RtAzAudModel.NTX86.Interfaces]
AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifWave%, RtAzAudModel.RtSpdifWave
AddInterface=%KSCATEGORY_RENDER%,%KSNAME_RtSpdifWave%, RtAzAudModel.RtSpdifWave
AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifTopo%, RtAzAudModel.RtSpdifTopo
AddInterface=%KSCATEGORY_TOPOLOGY%,%KSNAME_RtSpdifTopo%, RtAzAudModel.RtSpdifTopo

AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifHDMIWave%, RtAzAudModel.RtSpdifHDMIWave
AddInterface=%KSCATEGORY_RENDER%,%KSNAME_RtSpdifHDMIWave%, RtAzAudModel.RtSpdifHDMIWave
AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifHDMITopo%, RtAzAudModel.RtSpdifHDMITopo
AddInterface=%KSCATEGORY_TOPOLOGY%,%KSNAME_RtSpdifHDMITopo%, RtAzAudModel.RtSpdifHDMITopo

AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifRCAWave%, RtAzAudModel.RtSpdifRCAWave
AddInterface=%KSCATEGORY_RENDER%,%KSNAME_RtSpdifRCAWave%, RtAzAudModel.RtSpdifRCAWave
AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifRCATopo%, RtAzAudModel.RtSpdifRCATopo
AddInterface=%KSCATEGORY_TOPOLOGY%,%KSNAME_RtSpdifRCATopo%, RtAzAudModel.RtSpdifRCATopo

AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifOptWave%, RtAzAudModel.RtSpdifOptWave
AddInterface=%KSCATEGORY_RENDER%,%KSNAME_RtSpdifOptWave%, RtAzAudModel.RtSpdifOptWave
AddInterface=%KSCATEGORY_AUDIO%,%KSNAME_RtSpdifOptTopo%, RtAzAudModel.RtSpdifOptTopo
AddInterface=%KSCATEGORY_TOPOLOGY%,%KSNAME_RtSpdifOptTopo%, RtAzAudModel.RtSpdifOptTopo

[DS3DConfiguration.AddReg]
HKR,DS3D,ForwardSpeakerConfiguration,0x00010001,0
HKR,DS3D,IgnoreDSSpeakerConfiguration,0x00010001,1
HKR,"DS3D\OldArch",ForwardSpeakerConfiguration,0x00010001,0
HKR,"DS3D\OldArch",IgnoreDSSpeakerConfiguration,0x00010001,1

[RTUninstall.AddReg]
HKLM,%RT_UNINSTALL%,DisplayName,,"Realtek High Definition Audio Driver"
HKLM,%RT_UNINSTALL%,UninstallString,,"RtkUpd.exe -r -m"

[HdAudSecurity.AddReg]
HKR,,DeviceType,0x10001,0x0000001D

[RtAzAudModelAddReg]
HKR,,AssociatedFilters,,"wdmaud,swmidi,redbook"
HKR,,Driver,,RtHDMI.sys

HKR,Drivers,SubClasses,,"wave,midi,mixer,aux"

HKR,Drivers\wave\wdmaud.drv,Driver,,wdmaud.drv
HKR,Drivers\midi\wdmaud.drv,Driver,,wdmaud.drv
HKR,Drivers\mixer\wdmaud.drv,Driver,,wdmaud.drv
HKR,Drivers\aux\wdmaud.drv,Driver,,wdmaud.drv

HKR,Drivers\wave\wdmaud.drv,Description,,%IntcAzAudioDeviceDescription%
HKR,Drivers\midi\wdmaud.drv,Description,,%IntcAzAudioDeviceDescription%
HKR,Drivers\mixer\wdmaud.drv,Description,,%IntcAzAudioDeviceDescription%
HKR,Drivers\aux\wdmaud.drv,Description,,%IntcAzAudioDeviceDescription%

HKR,,SetupPreferredAudioDevices,3,01,00,00,00

[RtAzAudModel.RtSpdifWave]
AddReg = RtAzAudModel.RtSpdifWave.AddReg
[RtAzAudModel.RtSpdifWave.AddReg]
HKR,,FriendlyName,,%RtSpdifWaveDeviceName%
HKR,,CLSID,,%Proxy.CLSID%
[RtAzAudModel.RtSpdifTopo]
AddReg = RtAzAudModel.RtSpdifTopo.AddReg
[RtAzAudModel.RtSpdifTopo.AddReg]
HKR,,FriendlyName,,%RtSpdifTopoDeviceName%
HKR,,CLSID,,%Proxy.CLSID%

[RtAzAudModel.RtSpdifHDMIWave]
AddReg = RtAzAudModel.RtSpdifHDMIWave.AddReg
[RtAzAudModel.RtSpdifHDMIWave.AddReg]
HKR,,FriendlyName,,%RtSpdifHDMIWaveDeviceName%
HKR,,CLSID,,%Proxy.CLSID%
[RtAzAudModel.RtSpdifHDMITopo]
AddReg = RtAzAudModel.RtSpdifHDMITopo.AddReg

[RtAzAudModel.RtSpdifHDMITopo.AddReg]
HKR,,FriendlyName,,%RtSpdifHDMITopoDeviceName%
HKR,,CLSID,,%Proxy.CLSID%

HKLM,%MediaCategories%\%GUID.RTSPDIFOut%,Name,,%Node.RTSPDIFOut%
HKLM,%MediaCategories%\%GUID.RTSPDIFOut%,Display,1,00,00,00,00
HKLM,%MediaCategories%\%GUID.RTHDMIOut%,Name,,%Node.RTHDMIOut%
HKLM,%MediaCategories%\%GUID.RTHDMIOut%,Display,1,00,00,00,00
HKLM,%MediaCategories%\%GUID.RTSPDIFOutRCA%,Name,,%Node.RTSPDIFOutRCA%
HKLM,%MediaCategories%\%GUID.RTSPDIFOutRCA%,Display,1,00,00,00,00
HKLM,%MediaCategories%\%GUID.RTSPDIFOutOpt%,Name,,%Node.RTSPDIFOutOpt%
HKLM,%MediaCategories%\%GUID.RTSPDIFOutOpt%,Display,1,00,00,00,00

[RtAzAudModel.RtSpdifRCAWave]
AddReg = RtAzAudModel.RtSpdifRCAWave.AddReg
[RtAzAudModel.RtSpdifRCAWave.AddReg]
HKR,,FriendlyName,,%RtSpdifRCAWaveDeviceName%
HKR,,CLSID,,%Proxy.CLSID%
[RtAzAudModel.RtSpdifRCATopo]
AddReg = RtAzAudModel.RtSpdifRCATopo.AddReg
[RtAzAudModel.RtSpdifRCATopo.AddReg]
HKR,,FriendlyName,,%RtSpdifRCATopoDeviceName%
HKR,,CLSID,,%Proxy.CLSID%

[RtAzAudModel.RtSpdifOptWave]
AddReg = RtAzAudModel.RtSpdifOptWave.AddReg
[RtAzAudModel.RtSpdifOptWave.AddReg]
HKR,,FriendlyName,,%RtSpdifOptWaveDeviceName%
HKR,,CLSID,,%Proxy.CLSID%
[RtAzAudModel.RtSpdifOptTopo]
AddReg = RtAzAudModel.RtSpdifOptTopo.AddReg
[RtAzAudModel.RtSpdifOptTopo.AddReg]
HKR,,FriendlyName,,%RtSpdifOptTopoDeviceName%
HKR,,CLSID,,%Proxy.CLSID%

[Strings]
MfgName="Realtek"
MediaCategories="SYSTEM\CurrentControlSet\Control\MediaCategories"

OrganizationName="Realtek Semiconductor Corp."
PackageDisplayName="HD Audio Driver"
IntcAzAudioDeviceDescription = "Realtek High Definition Audio"

RT_UNINSTALL="Software\Microsoft\Windows\CurrentVersion\Uninstall\{F132AF7F-7BCA-4EDE-8A7C-958108FE7DBC}"

KSNAME_RtSpdifWave="RtSpdifWave"
KSNAME_RtSpdifTopo="RtSpdifTopo"
KSNAME_RtSpdifHDMIWave="RtSpdifHDMIWave"
KSNAME_RtSpdifHDMITopo="RtSpdifHDMITopo"
KSNAME_RtSpdifRCAWave="RtSpdifRCAWave"
KSNAME_RtSpdifRCATopo="RtSpdifRCATopo"
KSNAME_RtSpdifOptWave="RtSpdifOptWave"
KSNAME_RtSpdifOptTopo="RtSpdifOptTopo"

RtSpdifWaveDeviceName="Realtek HDA SPDIF Out"
RtSpdifTopoDeviceName="Realtek HDA SPDIF Out Mixer"
RtSpdifHDMIWaveDeviceName="Realtek HDA HDMI Out"
RtSpdifHDMITopoDeviceName="Realtek HDA HDMI Out Mixer"
RtSpdifRCAWaveDeviceName="Realtek HDA SPDIF RCA Out"
RtSpdifRCATopoDeviceName="Realtek HDA SPDIF RCA Out Mixer"
RtSpdifOptWaveDeviceName="Realtek HDA SPDIF Optical Out"
RtSpdifOptTopoDeviceName="Realtek HDA SPDIF Optical Out Mixer"


KSCATEGORY_AUDIO = "{6994AD04-93EF-11D0-A3CC-00A0C9223196}"
KSCATEGORY_RENDER="{65E8773E-8F56-11D0-A3B9-00A0C9223196}"
KSCATEGORY_CAPTURE="{65E8773D-8F56-11D0-A3B9-00A0C9223196}"
KSCATEGORY_TOPOLOGY="{DDA54A40-1E4C-11D1-A050-405705C10000}"
Proxy.CLSID ="{17CCA71B-ECD7-11D0-B908-00A0C9223196}"

GUID.RTSPDIFOut			="{8FD300D2-FFE1-44f3-A9EB-6F4395D73C9F}"
Node.RTSPDIFOut			="Realtek Digital Output"
GUID.RTHDMIOut			="{9C8E490E-877D-48fe-9EF1-AD83C91CC057}"
Node.RTHDMIOut			="Realtek HDMI Output"
GUID.RTSPDIFOutRCA		="{3FF4EDB6-3FF3-4b5a-B164-10FFF0367547}"
Node.RTSPDIFOutRCA		="Realtek Digital Output(RCA)"
GUID.RTSPDIFOutOpt		="{94FCA009-B26E-4cdc-AC75-051613EF01BB}"
Node.RTSPDIFOutOpt		="Realtek Digital Output(Optical)"
'''
,
'''
; Copyright (C) 2002-2008  NVIDIA Corporation
; Unauthorized copying or use without explicit permission of NVIDIA
; is prohibited
;
[Version] 
Signature = "$Windows NT$" 
Class=HDC
ClassGUID={4d36e96a-e325-11ce-bfc1-08002be10318} 
Provider=%NVIDIA% 
CatalogFile=nvata.cat
DriverVer=11/12/2008,10.3.0.46

[DestinationDirs] 
NVStor.Files.x86_12 = 12 
NVStor.CoInstFiles = 11


[SourceDisksNames.x86]
0=%Desc_x860%

[SourceDisksFiles.x86]
nvgts.sys=0
nvraidco.dll=0
NvRCoAr.dll=0
NvRCoCs.dll=0
NvRCoDa.dll=0
NvRCoDe.dll=0
NvRCoEl.dll=0
NvRCoEng.dll=0
NvRCoENU.dll=0
NvRCoEs.dll=0
NvRCoEsm.dll=0
NvRCoFi.dll=0
NvRCoFr.dll=0
NvRCoHe.dll=0
NvRCoHu.dll=0
NvRCoIt.dll=0
NvRCoJa.dll=0
NvRCoKo.dll=0
NvRCoNl.dll=0
NvRCoNo.dll=0
NvRCoPl.dll=0
NvRCoPt.dll=0
NvRCoPtb.dll=0
NvRCoRu.dll=0
NvRCoSk.dll=0
NvRCoSl.dll=0
NvRCoSv.dll=0
NvRCoTh.dll=0
NvRCoTr.dll=0
NvRCoZhc.dll=0
NvRCoZht.dll=0

[Manufacturer] 
%NVIDIA%=NVIDIA, ntx86, ntx86.6.0


[NVIDIA.ntx86.6.0]

[NVIDIA]
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0054&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0055&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0266&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0267&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_037F&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_03F6&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_044D&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0554&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0555&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_07F4&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AD5&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AD4&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AB9&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AB8&CC_0106

[NVIDIA.ntx86]
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0054&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0055&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0266&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0267&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_037F&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_03F6&CC_0101
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_044D&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0554&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0555&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_07F4&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AD5&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AD4&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AB9&CC_0106
%NVSTOR_DESC%=NVStor_Inst,PCI\VEN_10DE&DEV_0AB8&CC_0106

                                           
[NVStor_Inst.ntx86] 
CopyFiles = NVStor.Files.x86_12

[NVStor_Inst.ntx86.HW] 
AddReg=NVStor_Inst.ntx86.AddReg.HW

[NVStor_Inst.ntx86.AddReg.HW]
; allow access from system and administrator only
HKR,,"Security",,"D:P(A;;GA;;;SY)(A;;GA;;;BA)"

[NVStor_Inst.ntx86.CoInstallers]
CopyFiles = NVStor.CoInstFiles
AddReg = NVStor_Inst.CoInst_AddReg

[NVStor_Inst.CoInst_AddReg]
HKR,,CoInstallers32,0x00010000,		\
	"nvraiins.dll,NvRaidCoInstaller"


HKR, Uninstall, Script,0,"nvide.nvu"
HKR, Uninstall, Name,0,"NVIDIA IDE Driver"
HKR, Uninstall, INFSrcDir, 0, %01% 
HKR, Uninstall, Uninstaller,0,"nvuide.exe"

[NVStor_Inst.ntx86.Services] 
AddService = nvgts,0x00000002,NVStor_Service_Instx86,NVStor_EventLog_Instx86

[NVStor_Service_Instx86] 
ServiceType = %SERVICE_KERNEL_DRIVER% 
StartType = %SERVICE_BOOT_START% 
ErrorControl = %SERVICE_ERROR_CRITICAL% 
ServiceBinary = %12%\nvgts.sys
LoadOrderGroup = "SCSI Miniport"
AddReg = NVStor_DisableFltCache_AddReg
AddReg = pnpsafe_pci_addreg

[NVStor_EventLog_Instx86]
AddReg = NVStor_EventLog_AddReg

[NVStor_EventLog_AddReg]
HKR,,EventMessageFile,0x00020000,"%%SystemRoot%%\System32\IoLogMsg.dll;%%SystemRoot%%\System32\drivers\nvgts.sys"
HKR,,TypesSupported,0x00010001,7 

[NVStor_DisableFltCache_AddReg]
HKR,,DisableFilterCache,0x00010001,1

[pnpsafe_pci_addreg]
HKR, "Parameters\PnpInterface", "5", %REG_DWORD%, 0x00000001
HKR, "Parameters", "BusType", %REG_DWORD%, 0x00000003 ;; bus type =  ATA (0x3)


[NVStor.Files.x86_12] 
nvgts.sys

[NVStor.CoInstFiles]
nvraidco.dll
nvraiins.dll,nvraidco.dll
NvRCoAr.dll
NvRCoCs.dll
NvRCoDa.dll
NvRCoDe.dll
NvRCoEl.dll
NvRCoEng.dll
NvRCoENU.dll
NvRCoEs.dll
NvRCoEsm.dll
NvRCoFi.dll
NvRCoFr.dll
NvRCoHe.dll
NvRCoHu.dll
NvRCoIt.dll
NvRCoJa.dll
NvRCoKo.dll
NvRCoNl.dll
NvRCoNo.dll
NvRCoPl.dll
NvRCoPt.dll
NvRCoPtb.dll
NvRCoRu.dll
NvRCoSk.dll
NvRCoSl.dll
NvRCoSv.dll
NvRCoTh.dll
NvRCoTr.dll
NvRCoZhc.dll
NvRCoZht.dll



[Strings] 

;  *******Localizable Strings******* 
NVIDIA= "NVIDIA Corporation" 
Desc_x860= "SRCDATA" 
NVSTOR_DESC= "NVIDIA nForce Serial ATA Controller"

;  *******Non Localizable Strings******* 

SERVICE_BOOT_START = 0x0 
SERVICE_SYSTEM_START = 0x1 
SERVICE_AUTO_START = 0x2 
SERVICE_DEMAND_START = 0x3 
SERVICE_DISABLED = 0x4 

SERVICE_KERNEL_DRIVER = 0x1 
SERVICE_ERROR_IGNORE = 0x0 
SERVICE_ERROR_NORMAL = 0x1 
SERVICE_ERROR_SEVERE = 0x2 
SERVICE_ERROR_CRITICAL = 0x3 

REG_EXPAND_SZ = 0x00020000 
REG_DWORD = 0x00010001 
'''
]

txtsetupoemTestData = \
[
'''
;
; format for txtsetup.oem.
;
; Follow this format for non-PNP adapters ISA
;
; Follow the txtsetup.oem in initio for PNP adapters like PCI and ISAPNP
;
; Txtsetup.oem is a generic way to install Storage adapters to get them through
; textmode setup.  Do as little as possible and allow GUI mode setup to do the 
; remaining work using the supplied inf.
;
; General format:
;
; [section]
; key = value1,value2,...
;
;
; The hash ('#') or semicolon (';') introduces a comment.
; Strings with embedded spaces, commas, or hashes should be double-quoted
;


; This section lists all disks in the disk set.
;
; <description> is a descriptive name for a disk, used when
;   prompting for the disk
; <tagfile> is a file whose presence allows setup to recognize
;   that the disk is inserted.
; <directory> is where the files are located on the disk.
;
[Disks]
d1 = "NVIDIA AHCI DRIVER (SCSI)",\\disk1,\\testdir

; This section lists the default selection for each 'required'
; hardware component.  If a line is not present for a component,
; the default defaults to the first item in the [<component_name>]
; section (see below).
;
; <component_name> is one of computer, display, keyboard, mouse, scsi
; <id> is a unique <within the component> string to be associated
;   with an option.
[Defaults]


; This section lists the options available for a particular component.
;
; <id> is the unique string for the option
; <description> is a text string, presented to the user in a menu
; <key_name> gives the name of the key to be created for the component in
;   HKEY_LOCAL_MACHINE\ControlSet001\Services
[scsi]
BUSDRV = "NVIDIA nForce Storage Controller (required)"


; This section lists the files that should be copied if the user
; selects a particular component option.
;
; <file_type> is one of driver, port, class, dll, hal, inf, or detect.
;   See below.
; <source_disk> identifies where the file is to be copied from, and must
;   match en entry in the [Disks] section.
; <filename> is the name of the file. This will be appended to the
;   directory specified for the disk in the [Disks] section to form the
;   full path of the file on the disk.
; <driverkey> this is the name that will show under the services\driver key
; this should be the same name as the driver that is being installed.

[Files.scsi.BUSDRV]
driver = d1,nvgts.sys,BUSDRV
inf    = d1, nvgts.inf
catalog = d1, nvata.cat
dll    = d1,nvraidco.dll
dll     = d1,NvRCoENU.dll
dll     = d1,NvRCoAr.dll
dll     = d1,NvRCoCs.dll
dll     = d1,NvRCoDa.dll
dll     = d1,NvRCoDe.dll
dll     = d1,NvRCoEl.dll
dll     = d1,NvRCoEng.dll
dll     = d1,NvRCoEs.dll
dll     = d1,NvRCoEsm.dll
dll     = d1,NvRCoFi.dll
dll     = d1,NvRCoFr.dll
dll     = d1,NvRCoHe.dll
dll     = d1,NvRCoHu.dll
dll     = d1,NvRCoIt.dll
dll     = d1,NvRCoJa.dll
dll     = d1,NvRCoKo.dll
dll     = d1,NvRCoNl.dll
dll     = d1,NvRCoNo.dll
dll     = d1,NvRCoPl.dll
dll     = d1,NvRCoPt.dll
dll     = d1,NvRCoPtb.dll
dll     = d1,NvRCoRu.dll
dll     = d1,NvRCoSk.dll
dll     = d1,NvRCoSl.dll
dll     = d1,NvRCoSv.dll
dll     = d1,NvRCoTh.dll
dll     = d1,NvRCoTr.dll
dll     = d1,NvRCoZhc.dll
dll     = d1,NvRCoZht.dll

; This section specifies values to be set in the registry for
; particular component options.  Required values in the services\\xxx
; key are created automatically -- use this section to specify additional
; keys to be created in services\\xxx and values in services\\xxx and
; services\\xxx\\yyy.
;
; This section must be filled out for storage controllers that 
; are PNP adapters like PCI and ISA PNP adapters.  Failure to do this 
; can cause the driver to fail to load. Must also add the section
; [HardwareIds.scsi.ID] to identify the supported ID's.
;
; <value_name> specifies the value to be set within the key
; <value_type> is a string like REG_DWORD.  See below.
; <value> specifies the actual value; its format depends on <value_type>
;

[Config.BUSDRV]
value = parameters\PnpInterface,5,REG_DWORD,1

; A HardwareIds.scsi.Service section specifies the hardware IDs of 
; the devices that a particular mass-storage driver supports. 
;
; [HardwareIds.scsi.Service]
; id = "deviceID","service"
;
; HardwareIds.scsi.Service 
;   Service specifies the service to be installed. 
;
; <deviceId > Specifies the device ID for a mass-storage device. 
; <service > Specifies the service to be installed for the device. 
;The following example excerpt shows a HardwareIds.scsi.Service section for a disk device:
;


[HardwareIds.scsi.BUSDRV]
id = "PCI\VEN_10DE&DEV_0036", "nvgts"
id = "PCI\VEN_10DE&DEV_003E", "nvgts"
id = "PCI\VEN_10DE&DEV_0054", "nvgts"
id = "PCI\VEN_10DE&DEV_0055", "nvgts"
id = "PCI\VEN_10DE&DEV_0266", "nvgts"
id = "PCI\VEN_10DE&DEV_0267", "nvgts"
id = "PCI\VEN_10DE&DEV_037E", "nvgts"
id = "PCI\VEN_10DE&DEV_037F", "nvgts"
id = "PCI\VEN_10DE&DEV_036F", "nvgts"
id = "PCI\VEN_10DE&DEV_03F6", "nvgts"
id = "PCI\VEN_10DE&DEV_03F7", "nvgts"
id = "PCI\VEN_10DE&DEV_03E7", "nvgts"
id = "PCI\VEN_10DE&DEV_044D", "nvgts"
id = "PCI\VEN_10DE&DEV_044E", "nvgts"
id = "PCI\VEN_10DE&DEV_044F", "nvgts"
id = "PCI\VEN_10DE&DEV_0554", "nvgts"
id = "PCI\VEN_10DE&DEV_0555", "nvgts"
id = "PCI\VEN_10DE&DEV_0556", "nvgts"
id = "PCI\VEN_10DE&DEV_07F4", "nvgts"
id = "PCI\VEN_10DE&DEV_07F5", "nvgts"
id = "PCI\VEN_10DE&DEV_07F6", "nvgts"
id = "PCI\VEN_10DE&DEV_07F7", "nvgts"
id = "PCI\VEN_10DE&DEV_0768", "nvgts"
id = "PCI\VEN_10DE&DEV_0AD5", "nvgts"
id = "PCI\VEN_10DE&DEV_0AD4", "nvgts"
id = "PCI\VEN_10DE&DEV_0AB9", "nvgts"
id = "PCI\VEN_10DE&DEV_0AB8", "nvgts"
id = "PCI\VEN_10DE&DEV_0BCC", "nvgts"
id = "PCI\VEN_10DE&DEV_0BCD", "nvgts"

#--The following lines give additional USB floppy support
id = "USB\VID_03F0&PID_2001", "usbstor" #--HP
id = "USB\VID_054C&PID_002C", "usbstor" #--Sony
id = "USB\VID_057B&PID_0001", "usbstor" #--Y-E Data
id = "USB\VID_0409&PID_0040", "usbstor" #--NEC
id = "USB\VID_0424&PID_0FDC", "usbstor" #--SMSC
id = "USB\VID_08BD&PID_1100", "usbstor" #--Iomega
id = "USB\VID_055D&PID_2020", "usbstor" #--Samsung

id = "USB\VID_03EE&PID_6901", "usbstor" #--Mitsumi
''',
'''
# txtsetup.oem - version XP.8 for SYMMPI Windows XP driver
#
# ***********************************************************************
#                                                                       *
#   Copyright 2004 LSI Logic, Corp.  All rights reserved.               *
#                                                                       *
#   This file is property of LSI Logic, Corp. and is licensed for       *
#   use as is.  The receipt of or posession of this file does not       *
#   convey any rights to modify its contents, in whole, or in part,     *
#   without the specific written consent of LSI Logic, Corp.            *
#                                                                       *
# ***********************************************************************
#
# format for txtsetup.oem.
#
# General format:
#
# [section]
# key = value1,value2,...
#
#
# The hash ('#') introduces a comment.
# Strings with embedded spaces, commas, or hashes should be double-quoted
#


[Disks]

# This section lists all disks in the disk set.
#
# <description> is a descriptive name for a disk, used when
#   prompting for the disk
# <tagfile> is a file whose presence allows setup to recognize
#   that the disk is inserted.
# <directory> is where the files are located on the disk.
#

d1 = "LSI Logic PCI Fusion-MPT Miniport Driver",\symmpi.tag,\


[Defaults]

# This section lists the default selection for each 'required'
# hardware component.  If a line is not present for a component,
# the default defaults to the first item in the [<component_name>]
# section (see below).
#
# <component_name> is one of computer, display, keyboard, mouse, scsi
# <id> is a unique <within the component> string to be associated
#   with an option.

scsi = SYMMPI_32


[scsi]

# This section lists the options available for a particular component.
#
# <id> is the unique string for the option
# <description> is a text string, presented to the user in a menu
# <key_name> gives the name of the key to be created for the component in
#   HKEY_LOCAL_MACHINE\ControlSet001\Services

SYMMPI_32    = "LSI Logic PCI Fusion-MPT Driver (XP 32-bit)",symmpi


[HardwareIds.scsi.SYMMPI_32]

id = "PCI\VEN_1000&DEV_0622", "symmpi"
id = "PCI\VEN_1000&DEV_0624", "symmpi"
id = "PCI\VEN_1000&DEV_0626", "symmpi"
id = "PCI\VEN_1000&DEV_0628", "symmpi"
id = "PCI\VEN_1000&DEV_0030", "symmpi"
id = "PCI\VEN_1000&DEV_0032", "symmpi"
id = "PCI\VEN_1000&DEV_0050", "symmpi"
id = "PCI\VEN_1000&DEV_0054", "symmpi"
id = "PCI\VEN_1000&DEV_0058", "symmpi"
id = "PCI\VEN_1000&DEV_005E", "symmpi"
id = "PCI\VEN_1000&DEV_0056", "symmpi"
id = "PCI\VEN_1000&DEV_005A", "symmpi"
id = "PCI\VEN_1000&DEV_0640", "symmpi"
id = "PCI\VEN_1000&DEV_0646", "symmpi"
id = "PCI\VEN_1000&DEV_0062", "symmpi"


# This section lists the files that should be copied if the user
# selects a particular component option.
#
# <file_type> is one of driver, port, class, dll, hal, inf, or detect.
#   See below.
# <source_disk> identifies where the file is to be copied from, and must
#   match en entry in the [Disks] section.
# <filename> is the name of the file. This will be appended to the
#   directory specified for the disk in the [Disks] section to form the
#   full path of the file on the disk.

[Files.scsi.SYMMPI_32]
driver  = d1,symmpi.sys,SYMMPI
inf     = d1,symmpi.inf
inf     = d1,lsipseud.inf
catalog = d1,mpixp32.cat


[Config.SYMMPI]

# This section specifies values to be set in the registry for
# particular component options.  Required values in the services\\xxx
# key are created automatically -- use this section to specify additional
# keys to be created in services\\xxx and values in services\\xxx and
# services\\xxx\\yyy.
#
# <key_name> is relative to the services node for this device.
#   If it is empty, then it refers to the services node.
#   If specified, the key is created first.
# <value_name> specifies the value to be set within the key
# <value_type> is a string like REG_DWORD.  See below.
# <value> specifies the actual value; its format depends on <value_type>
value = Parameters\PnpInterface,5,REG_DWORD,1
'''
]

iniTestData = [
'''
#[section1]
# abc = def

[section2]
abc = def # comment

[section3]
key = value ;comment ; comment2

[section4]
key = value \; no comment \# comment2 ;# comment3

[section5]
key = \;\;\;\;\;\;\;\;\;\;\;\;
'''
]
if (__name__ == "__main__"):
	logger.setConsoleLevel(LOG_DEBUG2)
	logger.setConsoleColor(True)
	
	
	for data in infTestData:
		infFile = InfFile('/tmp/test.inf')
		infFile.parse(data.split('\n'))
		devices = infFile.getDevices()
		if not devices:
			logger.error(u"No devices found!")
		for dev in devices:
			logger.notice(u"Found device: %s" % dev)
		
	for data in txtsetupoemTestData[:1]:
		try:
			txtSetupOemFile = TxtSetupOemFile('/tmp/txtsetup.oem')
			txtSetupOemFile.parse(data.split('\n'))
			#for f in txtSetupOemFile.getFilesForDevice(vendorId = 1000, deviceId = '0056', fileTypes = []):
			#	print f
			for f in txtSetupOemFile.getFilesForDevice(vendorId = '10DE', deviceId = '07F6', fileTypes = []):
				print f
			
		except Exception, e:
			logger.logException(e)
		
		#devices = txtSetupOemFile.getDevices()
		#if not devices:
		#	logger.error(u"No devices found!")
		#for dev in devices:
		#	logger.notice(u"Found device: %s" % dev)
	
	for data in iniTestData:
		iniFile = IniFile('/tmp/test.ini')
		iniFile.parse(data.split('\n'))
	
	
	
	
	
	
