#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = =
   =    opsi python library - File.Opsi    =
   = = = = = = = = = = = = = = = = = = = = =
   
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

import os, codecs, re, ConfigParser, StringIO, cStringIO, json

if (os.name == 'posix'):
	import fcntl

elif (os.name == 'nt'):
	import win32con
	import win32file
	import pywintypes

# OPSI imports
from OPSI.Logger import *
from OPSI.Object import *
from OPSI.Types import *
from OPSI.Util.File import *

# Get logger instance
logger = Logger()

def toJson(obj):
	if hasattr(json, 'dumps'):
		# python 2.6 json module
		return json.dumps(obj)
	else:
		return json.write(obj)

def fromJson(obj):
	if hasattr(json, 'loads'):
		# python 2.6 json module
		return json.loads(obj)
	else:
		return json.read(obj)

class HostKeyFile(ConfigFile):
	
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
	
	def deleteOpsiHostKey(self, hostId):
		if not self._parsed:
			self.parse()
		hostId = forceHostId(hostId)
		if self._opsiHostKeys.has_key(hostId):
			del self._opsiHostKeys[hostId]
	
class BackendACLFile(ConfigFile):
	
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

class BackendDispatchConfigFile(ConfigFile):
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

class PackageControlFile(TextFile):
	
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
		self._packageDependencies = []
		self._incrementalPackage = False
		
	def parse(self):
		self.readlines()
		
		self._sections = {}
		self._product = None
		self._productDependencies = []
		self._productProperties = []
		self._packageDependencies = []
		self._incrementalPackage = False
		
		sectionType = None
		option = None
		lineNum = 0
		for line in self._lines:
			lineNum += 1
			
			if (len(line) > 0) and line[0] in (';', '#'):
				# Comment
				continue
			
			line = line.replace('\r', '')
			
			match = self.sectionRegex.search(line)
			if match:
				sectionType = match.group(1).strip().lower()
				if sectionType not in ('package', 'product', 'windows', 'productdependency', 'productproperty', 'changelog'):
					raise Exception(u"Parse error in line %s: unkown section '%s'" % (lineNum, sectionType))
				if (sectionType == 'changelog'):
					self._sections[sectionType] = u''
				else:
					if self._sections.has_key(sectionType):
						self._sections[sectionType].append({})
					else:
						self._sections[sectionType] = [{}]
				continue
			
			elif not sectionType and line:
				raise Exception(u"Parse error in line %s: not in a section" % lineNum)
			
			if (sectionType == 'changelog'):
				if self._sections[sectionType]:
					self._sections[sectionType] += u'\n'
				self._sections[sectionType] += line.rstrip()
				continue
			
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
					 'alwaysscript', 'oncescript', 'customscript', 'userloginscript']):
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
				if type(self._sections[sectionType][-1][option]) is unicode:
					self._sections[sectionType][-1][option] += u'\n%s' % value
		
		for (sectionType, secs) in self._sections.items():
			if (sectionType == 'changelog'):
				continue
			for i in range(len(secs)):
				for (option, value) in secs[i].items():
					if (sectionType == 'product'         and option == 'productclasses') or \
					   (sectionType == 'package'         and option == 'depends') or \
					   (sectionType == 'productproperty' and option == 'default') or \
					   (sectionType == 'productproperty' and option == 'values') or \
					   (sectionType == 'windows'         and option == 'softwareids'):
					   	try:
					   		value = fromJson(value.strip())
					   	except Exception, e:
					   		logger.debug(u"Failed to read json string '%s': %s" % (value.strip(), e) )
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
		
		# Get package info
		for (option, value) in self._sections.get('package', {}).items():
			if (option == 'depends'):
				for dep in value:
					match = re.search('^\s*([^\(]+)\s*\(*\s*([^\)]*)\s*\)*', dep)
					if not match.group(1):
						raise Exception(u"Bad package dependency '%s' in control file" % dep)
						continue
					package = match.group(1)
					version = match.group(2)
					condition = None
					if version:
						match = re.search('^\s*([<>]?=?)\s*([\w\.]+-*[\w\.]*)\s*$', version)
						if not match:
							raise Exception(u"Bad version string '%s' in package dependency" % version)
						
						condition = match.group(1)
						if not condition:
							condition = u'='
						if not condition in (u'=', u'<', u'<=', u'>', u'>='):
							raise Exception(u"Bad condition string '%s' in package dependency" % condition)
						version = match.group(2)
					else:
						version = None
					self._packageDependencies.append( { 'package': package, 'condition': condition, 'version': version } )
				
			elif (option == 'incremental'):
				self._incrementalPackage = forceBool(value)
		
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
			windowsSoftwareIds = self._sections.get('windows',[{}])[0].get('softwareids', []),
			changelog          = self._sections.get('changelog')
			
		)
		if isinstance(self._product, NetbootProduct) and not product.get('pxeconfigtemplate') is None:
			self._product.setPxeConfigTemplate(product.get('pxeconfigtemplate'))
		
		if isinstance(self._product, LocalbootProduct) and not product.get('userloginscript') is None:
			self._product.setUserLoginScript(product.get('userloginscript'))
		self._product.setDefaults()
		
		# Create ProductDependency objects
		for productDependency in self._sections.get('productdependency', []):
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
			self._productDependencies[-1].setDefaults()
		
		# Create ProductProperty objects
		for productProperty in self._sections.get('productproperty', []):
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
			self._productProperties[-1].setDefaults()
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
	
	def getPackageDependencies(self):
		if not self._parsed:
			self.parse()
		return self._packageDependencies
	
	def setPackageDependencies(self, packageDependencies):
		self._packageDependencies = []
		for packageDependency in forceDictList(packageDependencies):
			if not packageDependency.get('package'):
				raise ValueError(u"No package given: %s" % packageDependency)
			if packageDependency.get('version') in (None, ''):
				packageDependency['version'] = None
				packageDependency['condition'] = None
			else:
				if not packageDependency.get('condition'):
					packageDependency['condition'] = u'='
				if not packageDependency['condition'] in (u'=', u'<', u'<=', u'>', u'>='):
					raise Exception(u"Bad condition string '%s' in package dependency" % packageDependency['condition'])
			self._packageDependencies.append(packageDependency)
	
	def getIncrementalPackage(self):
		if not self._parsed:
			self.parse()
		return self._incrementalPackage
	
	def setIncrementalPackage(self, incremental):
		self._incrementalPackage = forceBool(incremental)
	
	def generate(self):
		if not self._product:
			raise Exception(u"Got no data to write")
		
		logger.info(u"Writing opsi package control file '%s'" % self._filename)
		
		self._lines = [ u'[Package]' ]
		self._lines.append( u'version: %s' % self._product.getPackageVersion() )
		depends = u''
		for packageDependency in self._packageDependencies:
			if depends: depends += u', '
			depends += packageDependency['package']
			if packageDependency['version']:
				depends += ' (%s %s)'(packageDependency['condition'], packageDependency['version'])
		
		self._lines.append( u'depends: %s' % depends )
		self._lines.append( u'incremental: %s' % self._incrementalPackage )
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
		if not self._product.getProductClassIds() is None:
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
					self._lines.append( u'values: %s' % toJson(productProperty.getPossibleValues()) )
			if productProperty.getDefaultValues():
				self._lines.append( u'default: %s' % toJson(productProperty.getDefaultValues()) )
		
		if not self._product.getChangelog() is None:
			self._lines.append( u'' )
			self._lines.append( u'[Changelog]' )
			self._lines.extend( self._product.getChangelog().split('\n') )
		
		self.open('w')
		self.writelines()
		self.close()
	
	
	

