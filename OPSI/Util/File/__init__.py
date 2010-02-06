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

__version__ = "3.5"

import os, codecs, re, grp, pwd, ConfigParser, StringIO, cStringIO

if (os.name == 'posix'):
	import fcntl

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
	
	def delete(self):
		if os.path.exists(self._filename):
			os.unlink(self._filename)
	
	def chown(self, user, group):
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
		LockableFile.__init__(self, filename)
		self._lines = []
		self._lineSeperator = u'\n'
		
	def open(self, mode = 'r', encoding='utf-8', errors='replace'):
		self._fileHandle = codecs.open(self._filename, mode, encoding, errors)
		self._lockFile(mode)
	
	def write(self, str):
		if not self._fileHandle:
			raise IOError("File not opened")
		str = forceUnicode(str)
		self._fileHandle.write(str)
	
	def readlines(self):
		self._lines = []
		if not self._fileHandle:
			for encoding in ('utf-8', 'latin_1', 'cp1252', 'utf-16', 'replace'):
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
		
	def parse(self):
		self.readlines()
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
	
	def generate(self):
		if not self._entries:
			raise Exception(u"No entries to write")
		self._lines = []
		for entry in self._entries:
			self._lines.append(u'%s (%s) %s; urgency=%s' % (entry['package'], entry['version'], entry['release'], entry['urgency']))
			self._lines.append(u'')
			for line in entry['changelog']:
				self._lines.append(line)
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
		self._entries = forceList(entries)
	
	
class ConfigFile(TextFile):
	def __init__(self, filename, lockFailTimeout = 2000, commentChars=[';', '/', '#']):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._commentChars = forceList(commentChars)
		self._parsed = False
	
	#def setFilename(self, filename):
	#	TextFile.setFilename(filename)
	#	self._parsed = False
	
	def parse(self):
		self.readlines()
		lines = []
		for line in self._lines:
			line = line.strip()
			if not line or line[0] in self._commentChars:
				continue
			lines.append(line)
		self._parsed = True
		return lines

class IniFile(ConfigFile):
	optionMatch = re.compile('^([^\:\=]+)([\:\=].*)$')
	
	def __init__(self, filename, lockFailTimeout = 2000, ignoreCase = True, raw = True):
		ConfigFile.__init__(self, filename, commentChars = [';', '#'])
		self._ignoreCase = forceBool(ignoreCase)
		self._raw = forceBool(raw)
		self._configParser = None
		
	def parse(self):
		logger.debug(u"Parsing ini file '%s'" % self._filename)
		start = time.time()
		lines = ConfigFile.parse(self)
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
		for c in list(self.components):
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
				index = -1
				for j in range(len(notWritten)):
					if (notWritten[j] == self.lineRefs[lineNumber][i]):
						index = j
						break
				if (index > -1):
					del notWritten[index]
				
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
		TextFile.__init__(self, filename)
		
		self._currentLine = -1
		self._currentToken = None
		self._currentIndex = -1
		self._data = u''
		self._currentBlock = None
		self._globalBlock = None
		self._parsed = False
		
		logger.debug(u"Parsing dhcpd conf file '%s'" % self._filename)
	
	def getGlobalBlock(self):
		return self._globalBlock
		
	def parse(self):
		self._parsed = False
		self.readlines()
		self._currentBlock = self._globalBlock = DHCPDConf_GlobalBlock()
		self._globalBlock.endLine = len(self._lines)
		minIndex = 0
		while True:
			logger.debug(u"parse ==>>> %s" % self._data)
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
			logger.warning(u"Host '%s' already exists in config file '%s', deleting first" % (hostname, self._filename))
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
		self._currentLine += 1
		if (self._currentLine >= len(self._lines)):
			return False
		self._data += self._lines[self._currentLine]
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
	
	
	
	

	
	
	
	
	
	
	
	
	
	
