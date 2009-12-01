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

import os, codecs, re, ConfigParser, StringIO, cStringIO

if (os.name == 'posix'):
	import fcntl

elif (os.name == 'nt'):
	import win32con
	import win32file
	import pywintypes

# OPSI imports
from OPSI.Logger import *
from OPSI.Backend.Object import *
from OPSI.Types import *

# Get logger instance
logger = Logger()

class File(object):
	def __init__(self, filename):
		self._filename = forceFilename(filename)
		self._fileHandle = None
		self.mode = None
	
	def getFilename(self):
		return self._filename
	
	def setFilename(self, filename):
		self._filename = forceFilename(filename)
	
	def delete(self):
		if os.path.exists(self._filename):
			os.unlink(self._filename)
	
	def create(self):
		if not os.path.exists(self._filename):
			self.open('w')
			self.close()
	
	def open(self, mode = 'r'):
		self.mode = mode
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
		self._lockFile()
	
	def close(self):
		self._unlockFile()
		File.close(self)
		
	def _lockFile(self):
		timeout = 0
		while (timeout < self._lockFailTimeout):
			# While not timed out and not locked
			logger.debug("Trying to lock file '%s' (%s/%s)" % (self._filename, timeout, self._lockFailTimeout))
			try:
				# Try to lock file
				if (os.name =='posix'):
					# Flags for exclusive, non-blocking lock
					flags = fcntl.LOCK_EX | fcntl.LOCK_NB
					if self.mode in ('r', 'rb'):
						# Flags for shared, non-blocking lock
						flags = fcntl.LOCK_SH | fcntl.LOCK_NB
					fcntl.flock(self._fileHandle.fileno(), flags)
				elif (os.name == 'nt'):
					flags = win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY
					if self.mode in ('r', 'rb'):
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
		self._lockFile()
	
	def write(self, str):
		if not self._fileHandle:
			raise IOError("File not opened")
		str = forceUnicode(str)
		self._fileHandle.write(str)
	
	def readlines(self):
		self._lines = []
		if not self._fileHandle:
			self.open()
		self._lines = self._fileHandle.readlines()
		self.close()
		return self._lines
	
	def writelines(self, sequence=[]):
		if not self._fileHandle:
			raise IOError("File not opened")
		if sequence:
			self._lines = forceUnicodeList(sequence)
		for i in range(len(self._lines)):
			self._lines[i] += self._lineSeperator
		self._fileHandle.writelines(self._lines)
	
class ConfigFile(TextFile):
	def __init__(self, filename, lockFailTimeout = 2000, commentChars=[';', '/', '#']):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._commentChars = forceList(commentChars)
		self._parsed = False
	
	def setFilename(self, filename):
		TextFile.setFilename(filename)
		self._parsed = False
	
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

class OpsiHostKeyFile(ConfigFile):
	
	lineRegex = re.compile('^\s*([^:]+)\s*:\s*([0-9a-fA-F]{32})\s*$')
	
	def __init__(self, filename, lockFailTimeout = 2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars = [';', '/', '#'])
		self._opsiHostKeys = {}
		
	def parse(self):
		for line in ConfigFile.parse(self):
			match = self.lineRegex.search(line)
			if not match:
				logger.error(u"Found bad formatted line '%s' in pckey file '%s'" % (line, self._filename))
				continue
			try:
				hostId = forceHostId(match.group(1))
				opsiHostKey = forceOpsiHostKey(match.group(2))
				if self._opsiHostKeys.has_key(hostId):
					logger.error(u"Found duplicate host '%s' in pckey file '%s'" % (hostId, self._filename))
				self._opsiHostKeys[hostId] = opsiHostKey
			except BackendBadValueError, e:
				logger.error(u"Found bad formatted line '%s' in pckey file '%s': %s" % (line, self._filename, e))
	
	def generate(self):
		if not self._opsiHostKeys:
			raise Exception(u"Got no data to write")
		
		self._lines = []
		hostIds = self._opsiHostKeys.keys()
		hostIds.sort()
		for hostId in hostIds:
			self._lines.append(u'%s:%s' % (hostId, self._opsiHostKeys[hostId]))
		self.open('w')
		self.writelines()
		self.close()
	
	def getOpsiHostKey(self, hostId):
		if not self._parsed:
			self.parse()
		hostId = forceHostId(hostId)
		if not self._opsiHostKeys.has_key(hostId):
			return None
		return self._opsiHostKeys[hostId]
		
	def setOpsiHostKey(self, hostId, opsiHostKey):
		if not self._parsed:
			self.parse()
		hostId = forceHostId(hostId)
		opsiHostKey = forceOpsiHostKey(opsiHostKey)
		self._opsiHostKeys[hostId] = opsiHostKey
	
class OpsiBackendACLFile(ConfigFile):
	
	aclEntryRegex = re.compile('^([^:]+)+\s*:\s*(\S.*)$')
	
	def parse(self):
		# acl example:
		#    <method>: <aclType>[(aclTypeParam[(aclTypeParamValue,...)],...)]
		#    xyz_.*:   opsi_depotserver,(attributes(id,name))
		#    abc:      self(attributes(!opsiHostKey)),sys_group(admin, group 2, attributes(!opsiHostKey))
		
		acl = []
		for line in ConfigFile.parse(self):
			match = re.search(self.aclEntryRegex, line)
			if not match:
				raise Exception(u"Found bad formatted line '%s' in acl file '%s'" % (line, self._filename))
			method = match.group(1)
			acl.append([method, []])
			for entry in match.group(2).split(';'):
				entry = entry.strip()
				aclType = entry
				aclTypeParams = ''
				if (entry.find('(') != -1):
					(aclType, aclTypeParams) = entry.split('(', 1)
					if (aclTypeParams[-1] != ')'):
						raise Exception(u"Bad formatted acl entry '%s': trailing ')' missing" % entry)
					aclType = aclType.strip()
					aclTypeParams = aclTypeParams[:-1]
				if not aclType in ('all', 'self', 'opsi_depotserver', 'opsi_client', 'sys_group', 'sys_user'):
					raise Exception(u"Unhandled acl type: '%s'" % aclType)
				entry = { 'type': aclType, 'allowAttributes': [], 'denyAttributes': [], 'ids': [] }
				if not aclTypeParams:
					if aclType in ('sys_group', 'sys_user'):
						raise Exception(u"Bad formatted acl type '%s': no params given" % aclType)
				else:
					aclTypeParam = u''
					aclTypeParamValues = [u'']
					inAclTypeParamValues = False
					for i in range(len(aclTypeParams)):
						c = aclTypeParams[i]
						if (c == '('):
							if inAclTypeParamValues:
								raise Exception(u"Bad formatted acl type params '%s'" % aclTypeParams)
							inAclTypeParamValues = True
						elif (c == ')'):
							if not inAclTypeParamValues or not aclTypeParam:
								raise Exception(u"Bad formatted acl type params '%s'" % aclTypeParams)
							inAclTypeParamValues = False
						elif (c != ',') or (i == len(aclTypeParams)-1):
							if inAclTypeParamValues:
								aclTypeParamValues[-1] += c
							else:
								aclTypeParam += c
						
						if (c == ',') or (i == len(aclTypeParams)-1):
							if inAclTypeParamValues:
								if (i == len(aclTypeParams)-1):
									raise Exception(u"Bad formatted acl type params '%s'" % aclTypeParams)
								aclTypeParamValues.append(u'')
							else:
								aclTypeParam = aclTypeParam.strip()
								tmp = []
								for t in aclTypeParamValues:
									t = t.strip()
									if not t:
										continue
									tmp.append(t)
								aclTypeParamValues = tmp
								if (aclTypeParam == 'attributes'):
									for v in aclTypeParamValues:
										if not v:
											continue
										if v.startswith('!'):
											entry['denyAttributes'].append(v.strip())
										else:
											entry['allowAttributes'].append(v)
								elif aclType in ('sys_group', 'sys_user', 'opsi_depotserver', 'opsi_client'):
									entry['ids'].append(aclTypeParam.strip())
								else:
									raise Exception(u"Unhandled acl type param '%s' for acl type '%s'" % (aclTypeParam, aclType))
								aclTypeParam = u''
								aclTypeParamValues = [u'']
						
						
				acl[-1][1].append(entry)
		return acl

class OpsiBackendDispatchConfigFile(ConfigFile):
	def parse(self):
		dispatchEntryRegex = re.compile('^([^:]+)+\s*:\s*(\S.*)$')
		dispatch = []
		for line in self.readlines():
			match = re.search(dispatchEntryRegex, line)
			if not match:
				logger.error(u"Found bad formatted line '%s' in dispatch config file '%s'" % (line, self._filename))
				continue
			method = match.group(1)
			dispatch.append([match.group(1), []])
			for entry in match.group(2).split(','):
				dispatch[-1][1].append(entry.strip())
		return dispatch

class IniFile(ConfigFile):
	optionMatch = re.compile('^([^\:\=]+)([\:\=].*)$')
	
	def __init__(self, filename, lockFailTimeout = 2000, ignoreCase = True, raw = False):
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
		
		for (section, options) in sections.items():
			self._configParser.add_section(section)
			for (option, value) in options.items():
				self._configParser.set(section, option, value)
		
		for section in self._configParser.sections():
			for (option, value) in self._configParser.items(section):
				print option, type(option)
				print value, type(value)
		
		data = StringIO.StringIO()
		self._configParser.write(data)
		self._lines = data.getvalue().decode('utf-8').replace('\r', '').split('\n')
		
		self.open('w')
		self.writelines()
		self.close()
	

class OpsiPackageControlFile(TextFile):
	
	sectionRegex = re.compile('^\s*\[([^\]]+)\]\s*$')
	valueContinuationRegex = re.compile('^\s(.*)$')
	optionRegex = re.compile('^(\S+)\s*\:\s*(.*)$')
	
	def __init__(self, filename, lockFailTimeout = 2000):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._parsed = False
		self._sections = {}
		self._product = None
		self._productDependencies = []
		self._productProperties = []
		
	def parse(self):
		self.readlines()
		
		self._sections = {}
		self._product = None
		self._productDependencies = []
		self._productProperties = []
		
		sectionType = None
		option = None
		lineNum = 0
		for line in self._lines:
			lineNum += 1
			if (len(line) > 0) and line[0] in (';', '#'):
				# Comment
				continue
			
			match = self.sectionRegex.search(line)
			if match:
				sectionType = match.group(1).strip().lower()
				if sectionType not in ('package', 'product', 'windows', 'productdependency', 'productproperty'):
					raise Exception(u"Parse error in line %s: unkown section '%s'" % (lineNum, sectionType))
				if self._sections.has_key(sectionType):
					self._sections[sectionType].append({})
				else:
					self._sections[sectionType] = [{}]
				continue
			
			elif not sectionType and line:
				raise Exception(u"Parse error in line %s: not in a section" % lineNum)
			
			key = None
			value = None
			match = self.valueContinuationRegex.search(line)
			if match:
				value = match.group(1)
			else:
				match = self.optionRegex.search(line)
				if match:
					key = match.group(1).lower()
					value = match.group(2).lstrip()
			
			if (sectionType == 'package' and key in \
					['version', 'depends', 'incremental']):
				option = key
				if   (key == 'version'):     value = forceUnicodeLower(value)
				elif (key == 'depends'):     value = forceUnicodeLower(value)
				elif (key == 'incremental'): value = forceBool(value)
				
			elif (sectionType == 'product' and key in \
					['id', 'type', 'name', 	'description', 'advice',
					 'version', 'packageversion', 'priority',
					 'licenserequired', 'productclasses', 'pxeconfigtemplate',
					 'setupscript', 'uninstallscript', 'updatescript',
					 'alwaysscript', 'oncescript']):
				option = key
				if   (key == 'id'):                value = forceProductId(value)
				elif (key == 'type'):              value = forceProductType(value)
				elif (key == 'name'):              value = forceUnicode(value)
				elif (key == 'description'):       value = forceUnicode(value)
				elif (key == 'advice'):            value = forceUnicode(value)
				elif (key == 'version'):           value = forceProductVersion(value)
				elif (key == 'packageversion'):    value = forcePackageVersion(value)
				elif (key == 'priority'):          value = forceProductPriority(value)
				elif (key == 'licenserequired'):   value = forceBool(value)
				elif (key == 'productclasses'):    value = forceUnicodeLower(value)
				elif (key == 'pxeconfigtemplate'): value = forceFilename(value)
				elif (key == 'setupscript'):       value = forceFilename(value)
				elif (key == 'uninstallscript'):   value = forceFilename(value)
				elif (key == 'updatescript'):      value = forceFilename(value)
				elif (key == 'alwaysscript'):      value = forceFilename(value)
				elif (key == 'oncescript'):        value = forceFilename(value)
				elif (key == 'customscript'):      value = forceFilename(value)
				elif (key == 'userloginscript'):   value = forceFilename(value)
				
			elif (sectionType == 'windows' and key in \
					['softwareids']):
				option = key
				value = forceUnicodeLower(value)
			
			elif (sectionType == 'productdependency' and key in \
					['action', 'requiredproduct', 'requiredclass',
					 'requiredstatus', 'requiredaction', 'requirementtype']):
				option = key
				if   (key == 'action'):          value = forceActionRequest(value)
				elif (key == 'requiredproduct'): value = forceProductId(value)
				elif (key == 'requiredclass'):   value = forceUnicodeLower(value)
				elif (key == 'requiredstatus'):  value = forceInstallationStatus(value)
				elif (key == 'requiredaction'):  value = forceActionRequest(value)
				elif (key == 'requirementtype'): value = forceRequirementType(value)
			
			elif (sectionType == 'productproperty' and key in \
					['type', 'name', 'default', 'values', 'description']):
				option = key
				if   (key == 'type'):        value = forceProductPropertyType(value)
				elif (key == 'name'):        value = forceUnicodeLower(value)
				elif (key == 'default'):     value = forceUnicode(value)
				elif (key == 'values'):      value = forceUnicode(value)
				elif (key == 'description'): value = forceUnicode(value)
			
			else:
				value = forceUnicode(line)
			
			if not option:
				raise Exception(u"Parse error in line '%s': no option / bad option defined" % lineNum)
			
			if not self._sections[sectionType][-1].has_key(option):
				self._sections[sectionType][-1][option] = value
			else:
				self._sections[sectionType][-1][option] += '\n' + value
		
		for (sectionType, secs) in self._sections.items():
			for i in range(len(secs)):
				for (option, value) in secs[i].items():
					if (sectionType == 'product'         and option == 'productclasses') or \
					   (sectionType == 'package'         and option == 'depends') or \
					   (sectionType == 'productproperty' and option == 'default') or \
					   (sectionType == 'productproperty' and option == 'values') or \
					   (sectionType == 'windows'         and option == 'softwareids'):
						value = value.replace(u'\n', u'')
						value = value.replace(u'\t', u'')
						value = value.split(u',')
						value = map ( lambda x:x.strip(), value )
						# Remove duplicates
						tmp = []
						for v in value:
							if v and v not in tmp:
								tmp.append(v)
						value = tmp
					
					if type(value) is unicode:
						value = value.rstrip()
						#value = value.replace(u'\n', u'')
						#value = value.replace(u'\t', u'')
					
					self._sections[sectionType][i][option] = value
		
		if not self._sections.get('product'):
			raise Exception(u"Error in control file '%s': 'product' section not found" % self._filename)
		
		# Create Product object
		product = self._sections['product'][0]
		Class = None
		if   (product.get('type') == 'NetbootProduct'):
			Class = NetbootProduct
		elif (product.get('type') == 'LocalbootProduct'):
			Class = LocalbootProduct
		else:
			raise Exception(u"Error in control file '%s': unkown product type '%s'" % (self._filename, product.get('type')))
		
		self._product = Class(
			id                 = product.get('id'),
			name               = product.get('name'),
			productVersion     = product.get('version'),
			packageVersion     = self._sections.get('package',[{}])[0].get('version') or product.get('packageversion'),
			licenseRequired    = product.get('licenserequired'),
			setupScript        = product.get('setupscript'),
			uninstallScript    = product.get('uninstallscript'),
			updateScript       = product.get('updatescript'),
			alwaysScript       = product.get('alwaysscript'),
			onceScript         = product.get('oncescript'),
			customScript       = product.get('customscript'),
			priority           = product.get('priority'),
			description        = product.get('description'),
			advice             = product.get('advice'),
			productClassNames  = product.get('productclasses'),
			windowsSoftwareIds = self._sections.get('windows',[{}])[0].get('softwareids')
		)
		if isinstance(self._product, NetbootProduct) and product.get('pxeconfigtemplate'):
			self._product.setPxeConfigTemplate(product.get('pxeconfigtemplate'))
		
		if isinstance(self._product, LocalbootProduct) and product.get('userloginscript'):
			self._product.setUserLoginScript(product.get('userloginscript'))
		
		# Create ProductDependency objects
		for productDependency in self._sections['productdependency']:
			self._productDependencies.append(
				ProductDependency(
					productId                  = self._product.getId(),
					productVersion             = self._product.getProductVersion(),
					packageVersion             = self._product.getPackageVersion(),
					productAction              = productDependency.get('action'),
					requiredProductId          = productDependency.get('requiredproduct'),
					requiredProductVersion     = None,
					requiredPackageVersion     = None,
					requiredAction             = productDependency.get('requiredaction'),
					requiredInstallationStatus = productDependency.get('requiredstatus'),
					requirementType            = productDependency.get('requirementtype')
				)
			)
		
		# Create ProductProperty objects
		for productProperty in self._sections['productproperty']:
			Class = UnicodeProductProperty
			if   productProperty.get('type') in ('UnicodeProductProperty', '', None):
				Class = UnicodeProductProperty
			elif (productProperty.get('type') == 'BoolProductProperty'):
				Class = BoolProductProperty
			else:
				raise Exception(u"Error in control file '%s': unkown product property type '%s'" % (self._filename, productProperty.get('type')))
			self._productProperties.append(
				Class(
					productId      = self._product.getId(),
					productVersion = self._product.getProductVersion(),
					packageVersion = self._product.getPackageVersion(),
					propertyId     = productProperty.get('name'),
					description    = productProperty.get('description'),
					defaultValues  = productProperty.get('default')
				)
			)
			if isinstance(self._productProperties[-1], UnicodeProductProperty):
					if productProperty.get('values'):
						self._productProperties[-1].setPossibleValues(productProperty.get('values'))
						self._productProperties[-1].setEditable(False)
					else:
						self._productProperties[-1].setEditable(True)
		self._parsed = True
		return self._sections
	
	def getProduct(self):
		if not self._parsed:
			self.parse()
		return self._product
	
	def setProduct(self, product):
		self._product = forceObjectClass(product, Product)
	
	def getProductDependencies(self):
		if not self._parsed:
			self.parse()
		return self._productDependencies
	
	def setProductDependencies(self, productDependencies):
		self._productDependencies = forceObjectClassList(productDependencies, ProductDependency)
	
	def getProductProperties(self):
		if not self._parsed:
			self.parse()
		return self._productProperties
	
	def setProductProperties(self, productProperties):
		self._productProperties = forceObjectClassList(productProperties, ProductProperty)
	
	def generate(self):
		if not self._product:
			raise Exception(u"Got no data to write")
		
		logger.info(u"Writing opsi package control file '%s'" % self._filename)
		
		self._lines = [ u'[Package]' ]
		self._lines.append( u'version: %s' % self._product.getPackageVersion() )
		self._lines.append( u'depends:' )
		self._lines.append( u'incremental: False' )
		self._lines.append( u'' )
		
		self._lines.append( u'[Product]' )
		self._lines.append( u'type: %s' % self._product.getType() )
		self._lines.append( u'id: %s'   % self._product.getId() )
		self._lines.append( u'name: %s' % self._product.getName() )
		self._lines.append( u'description: ' )
		descLines = self._product.getDescription().split(u'\\n')
		if (len(descLines) > 0):
			self._lines[-1] += descLines[0]
			if (len(descLines) > 1):
				self._lines.extend( descLines )
		self._lines.append( u'advice: %s'          % self._product.getAdvice() )
		self._lines.append( u'version: %s'         % self._product.getProductVersion() )
		self._lines.append( u'priority: %s'        % self._product.getPriority() )
		self._lines.append( u'licenseRequired: %s' % self._product.getLicenseRequired() )
		self._lines.append( u'productClasses: %s'  % u', '.join(self._product.getProductClassIds()) )
		self._lines.append( u'setupScript: %s'     % self._product.getSetupScript() )
		self._lines.append( u'uninstallScript: %s' % self._product.getUninstallScript() )
		self._lines.append( u'updateScript: %s'    % self._product.getUpdateScript() )
		self._lines.append( u'alwaysScript: %s'    % self._product.getAlwaysScript() )
		self._lines.append( u'onceScript: %s'      % self._product.getOnceScript() )
		self._lines.append( u'customScript: %s'    % self._product.getCustomScript() )
		if isinstance(self._product, LocalbootProduct):
			self._lines.append( u'userLoginScript: %s'   % self._product.getUserLoginScript() )
		if isinstance(self._product, NetbootProduct):
			self._lines.append( u'pxeConfigTemplate: %s' % self._product.getPxeConfigTemplate() )
		self._lines.append( u'' )
		
		if self._product.getWindowsSoftwareIds():
			self._lines.append( '[Windows]' )
			self._lines.append( u'softwareIds: %s' % u', '.join(self._product.getWindowsSoftwareIds()) )
		
		for dependency in self._productDependencies:
			self._lines.append( u'' )
			self._lines.append( u'[ProductDependency]' )
			self._lines.append( u'action: %s' % dependency.getRequiredAction() )
			if dependency.getRequiredProductId():
				self._lines.append( u'requiredProduct: %s' % dependency.getRequiredProductId() )
			#if dependency.requiredProductClassId:
			#	self._lines.append( u'requiredClass: %s'   % dependency.requiredProductClassId )
			if dependency.getRequiredAction():
				self._lines.append( u'requiredAction: %s'  % dependency.getRequiredAction() )
			if dependency.getRequiredInstallationStatus():
				self._lines.append( u'requiredStatus: %s'  % dependency.getRequiredInstallationStatus() )
			if dependency.getRequirementType():
				self._lines.append( u'requirementType: %s' % dependency.getRequirementType() )
		
		for productProperty in self._productProperties:
			self._lines.append( u'' )
			self._lines.append( u'[ProductProperty]' )
			self._lines.append( u'name: %s' % productProperty.getPropertyId() )
			if productProperty.getDescription():
				self._lines.append( u'description: ' )
				descLines = productProperty.getDescription().split(u'\\n')
				if (len(descLines) > 0):
					self._lines[-1] += descLines[0]
					if (len(descLines) > 1):
						self._lines.extend( descLines )
			if not isinstance(productProperty, BoolProductProperty) and productProperty.getPossibleValues():
					self._lines.append( u'values: %s' % ', '.join(productProperty.getPossibleValues()) )
			if productProperty.getDefaultValues():
				self._lines.append( u'default: %s' % u', '.join(forceUnicodeList(productProperty.getDefaultValues())) )
		
		self.open('w')
		self.writelines()
		self.close()
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

