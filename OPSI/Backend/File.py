#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =  opsi python library - File31   =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
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
   @author: Jan Schneider <j.schneider@uib.de>, Arne Kerz <a.kerz@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

import os, socket, ConfigParser, shutil, json, types

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Util import toJson, fromJson
from OPSI.Util.File import *
from OPSI.Util.File.Opsi import *
from Object import *
from Backend import *

# Get logger instance
logger = Logger()

# ======================================================================================================
# =                                   CLASS FILEBACKEND                                                =
# ======================================================================================================
class FileBackend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self.__baseDir     = u'/var/lib/opsi/config'
		self.__hostKeyFile = u'/etc/opsi/pckeys'
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('basedir'):
				self.__baseDir = forceFilename(value)
			elif option in ('hostkeyfile'):
				self.__hostKeyFile = forceFilename(value)
			
		
		self.__clientConfigDir   = os.path.join(self.__baseDir, u'clients')
		self.__depotConfigDir    = os.path.join(self.__baseDir, u'depots')
		self.__productDir        = os.path.join(self.__baseDir, u'products')
		self.__auditDir          = os.path.join(self.__baseDir, u'audit')
		self.__configFile        = os.path.join(self.__baseDir, u'config.ini')
		self.__clientGroupsFile  = os.path.join(self.__baseDir, u'clientgroups.ini')
		self.__clientTemplateDir = os.path.join(self.__baseDir, u'templates')
		
		self.__defaultClientTemplateName = 'pcproto'
		self.__serverId = forceHostId(socket.getfqdn())
		self._placeholderRegex  = re.compile('<([^>]+)>')
		
		self._mappings = {
			'Config': [                                                # TODO: placeholders
				{ 'fileType': 'ini', 'attribute': 'type'           , 'section': '<id>', 'option': 'type',           'json': False     },
				{ 'fileType': 'ini', 'attribute': 'description'    , 'section': '<id>', 'option': 'description',    'json': False     },
				{ 'fileType': 'ini', 'attribute': 'editable'       , 'section': '<id>', 'option': 'editable' ,      'json': True      },
				{ 'fileType': 'ini', 'attribute': 'multiValue'     , 'section': '<id>', 'option': 'multivalue' ,    'json': True      },
				{ 'fileType': 'ini', 'attribute': 'possibleValues' , 'section': '<id>', 'option': 'possiblevalues', 'json': True      },
				{ 'fileType': 'ini', 'attribute': 'defaultValues'  , 'section': '<id>', 'option': 'defaultvalues' , 'json': True      }
			],
			'OpsiClient': [
				{ 'fileType': 'key', 'attribute': 'opsiHostKey' },
				{ 'fileType': 'ini', 'attribute': 'description',     'section': 'info', 'option': 'description'     },
				{ 'fileType': 'ini', 'attribute': 'notes',           'section': 'info', 'option': 'notes'           },
				{ 'fileType': 'ini', 'attribute': 'hardwareAddress', 'section': 'info', 'option': 'hardwareaddress' },
				{ 'fileType': 'ini', 'attribute': 'ipAddress',       'section': 'info', 'option': 'ipaddress'       },
				{ 'fileType': 'ini', 'attribute': 'inventoryNumber', 'section': 'info', 'option': 'inventorynumber' },
				{ 'fileType': 'ini', 'attribute': 'created',         'section': 'info', 'option': 'created'         },
				{ 'fileType': 'ini', 'attribute': 'lastSeen',        'section': 'info', 'option': 'lastseen'        }
			],
			'OpsiDepotserver': [
				{ 'fileType': 'key', 'attribute': 'opsiHostKey' },
				{ 'fileType': 'ini', 'attribute': 'description',         'section': 'depotserver', 'option': 'description'     },
				{ 'fileType': 'ini', 'attribute': 'notes',               'section': 'depotserver', 'option': 'notes'           },
				{ 'fileType': 'ini', 'attribute': 'hardwareAddress',     'section': 'depotserver', 'option': 'hardwareaddress' },
				{ 'fileType': 'ini', 'attribute': 'ipAddress',           'section': 'depotserver', 'option': 'ipaddress'       },
				{ 'fileType': 'ini', 'attribute': 'inventoryNumber',     'section': 'depotserver', 'option': 'inventorynumber' },
				{ 'fileType': 'ini', 'attribute': 'networkAddress',      'section': 'depotserver', 'option': 'network'         },
				{ 'fileType': 'ini', 'attribute': 'depotRemoteUrl',      'section': 'depotshare',  'option': 'remoteurl'       },
				{ 'fileType': 'ini', 'attribute': 'depotLocalUrl',       'section': 'depotshare',  'option': 'localurl'        },
				{ 'fileType': 'ini', 'attribute': 'repositoryRemoteUrl', 'section': 'repository',  'option': 'remoteurl'       },
				{ 'fileType': 'ini', 'attribute': 'repositoryLocalUrl',  'section': 'repository',  'option': 'localurl'        },
				{ 'fileType': 'ini', 'attribute': 'maxBandwidth',        'section': 'repository',  'option': 'maxbandwidth'    }
			],
			'ConfigState': [
				{ 'fileType': 'ini', 'attribute': 'values', 'section': 'generalconfig', 'option': '<configId>',    'json': True }
			],
			'Product': [
				{ 'fileType': 'pro', 'attribute': 'name',               'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'licenseRequired',    'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'setupScript',        'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'uninstallScript',    'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'updateScript',       'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'alwaysScript',       'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'onceScript',         'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'customScript',       'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'priority',           'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'description',        'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'advice',             'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'changelog',          'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'productClassNames',  'object': 'product' },
				{ 'fileType': 'pro', 'attribute': 'windowsSoftwareIds', 'object': 'product' }
			],
			'ProductProperty': [
				{ 'fileType': 'pro', 'attribute': '*' }
			],
			'ProductDependency': [
				{ 'fileType': 'pro', 'attribute': '*' }
			],
			'ProductOnDepot': [
				{ 'fileType': 'ini', 'attribute': 'productType',    'section': '<productId>-state', 'option': 'producttype',    'json': False },
				{ 'fileType': 'ini', 'attribute': 'productVersion', 'section': '<productId>-state', 'option': 'productversion', 'json': False },
				{ 'fileType': 'ini', 'attribute': 'packageVersion', 'section': '<productId>-state', 'option': 'packageversion', 'json': False }
			],
			'ProductOnClient': [
				{ 'fileType': 'ini', 'attribute': 'productType',        'section': '<productId>-state', 'option': 'producttype',        'json': False },
				{ 'fileType': 'ini', 'attribute': 'installationStatus', 'section': '<productId>-state', 'option': 'installationstatus', 'json': False },
				{ 'fileType': 'ini', 'attribute': 'actionRequest',      'section': '<productId>-state', 'option': 'actionrequest',      'json': False },
				{ 'fileType': 'ini', 'attribute': 'actionProgress',     'section': '<productId>-state', 'option': 'actionprogress',     'json': False },
				{ 'fileType': 'ini', 'attribute': 'productVersion',     'section': '<productId>-state', 'option': 'productversion',     'json': False },
				{ 'fileType': 'ini', 'attribute': 'packageVersion',     'section': '<productId>-state', 'option': 'packageversion',     'json': False },
				{ 'fileType': 'ini', 'attribute': 'lastStateChange',    'section': '<productId>-state', 'option': 'laststatechange',    'json': False },
				{ 'fileType': 'ini', 'attribute': 'installationStatus', 'section': '<productType>_product_states', 'option': '<productId>', 'json': False },
				{ 'fileType': 'ini', 'attribute': 'actionRequest',      'section': '<productType>_product_states', 'option': '<productId>', 'json': False },
			],
			'ProductPropertyState': [
				{ 'fileType': 'ini', 'attribute': 'values', 'section': '<productId>-install', 'option': '<propertyId>',    'json': True }
			],
			'Group': [
				{ 'fileType': 'ini', 'attribute': 'description',   'section': '<id>', 'option': 'description'   },
				{ 'fileType': 'ini', 'attribute': 'parentGroupId', 'section': '<id>', 'option': 'parentgroupid' },
				{ 'fileType': 'ini', 'attribute': 'notes',         'section': '<id>', 'option': 'notes'         }
			],
			'ObjectToGroup': [
				{ 'fileType': 'ini', 'attribute': '*', 'section': '<groupId>', 'option': '<objectId>' }
			]
		}
		
		self._mappings['UnicodeConfig'] = self._mappings['Config']
		self._mappings['BoolConfig'] = self._mappings['Config']
		self._mappings['OpsiConfigserver'] = self._mappings['OpsiDepotserver']
		self._mappings['LocalbootProduct'] = self._mappings['Product']
		self._mappings['LocalbootProduct'].append({ 'fileType': 'pro', 'attribute': 'userLoginScript', 'object': 'product' })
		self._mappings['NetbootProduct'] = self._mappings['Product']
		self._mappings['NetbootProduct'].append({ 'fileType': 'pro', 'attribute': 'pxeConfigTemplate', 'object': 'product' })
		self._mappings['UnicodeProductProperty'] = self._mappings['ProductProperty']
		self._mappings['BoolProductProperty'] = self._mappings['ProductProperty']
		self._mappings['HostGroup'] = self._mappings['Group']
	
	def backend_exit(self):
		pass
	
	def backend_createBase(self):
		if not os.path.exists(self.__baseDir):
			self._mkdir(self.__baseDir)
		if not os.path.exists(self.__clientConfigDir):
			self._mkdir(self.__clientConfigDir)
		if not os.path.exists(self.__depotConfigDir):
			self._mkdir(self.__depotConfigDir)
		if not os.path.exists(self.__productDir):
			self._mkdir(self.__productDir)
		if not os.path.exists(self.__auditDir):
			self._mkdir(self.__auditDir)
		if not os.path.exists(self.__clientTemplateDir):
			self._mkdir(self.__clientTemplateDir)
		defaultTemplate = os.path.join(self.__clientTemplateDir, self.__defaultClientTemplateName + '.ini')
		if not os.path.exists(defaultTemplate):
			self._touch(defaultTemplate)
		if not os.path.exists(self.__configFile):
			self._touch(self.__configFile)
		if not os.path.exists(self.__hostKeyFile):
			self._touch(self.__hostKeyFile)
		if not os.path.exists(self.__clientGroupsFile):
			self._touch(self.__clientGroupsFile)
		
	def backend_deleteBase(self):
		logger.info(u"Deleting base path: '%s'" % self.__baseDir)
		if os.path.exists(self.__baseDir):
			shutil.rmtree(self.__baseDir)
		if os.path.exists(self.__clientConfigDir):
			shutil.rmtree(self.__clientConfigDir)
		if os.path.exists(self.__depotConfigDir):
			shutil.rmtree(self.__depotConfigDir)
		if os.path.exists(self.__productDir):
			shutil.rmtree(self.__productDir)
		if os.path.exists(self.__auditDir):
			shutil.rmtree(self.__auditDir)
		if os.path.exists(self.__configFile):
			os.unlink(self.__configFile)
		if os.path.exists(self.__hostKeyFile):
			os.unlink(self.__hostKeyFile)
		if os.path.exists(self.__clientGroupsFile):
			os.unlink(self.__clientGroupsFile)
		
	def _mkdir(self, dirname):
		logger.info(u"Creating path: '%s'" % dirname)
		os.mkdir(dirname)
		os.chmod(dirname, 0770)
		os.chown(dirname, -1, grp.getgrnam('pcpatch')[2])
	
	def _touch(self, filename):
		logger.info(u"Creating file: '%s'" % filename)
		f = open(filename, 'w')
		f.close()
		os.chmod(filename, 0660)
		os.chown(filename, -1, grp.getgrnam('pcpatch')[2])
	
	def _escape(self, line, strList):
		line = forceUnicode(line)
		stringList = forceUnicodeList(stringList)
		for string in stringList:
			line.replace(u'%s' % string, u'\\%s' % string)
		return line
	
	def _getConfigFile(self, objType, ident, fileType):
		if (fileType == 'key'):
			return os.path.join(self.__hostKeyFile)
		
		elif (fileType == 'ini'):
			if objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
				return self.__configFile
			elif objType in ('OpsiClient'):
				return os.path.join(self.__clientConfigDir, ident['id'] + u'.ini')
			elif objType in ('OpsiDepotserver', 'OpsiConfigserver'):
				return os.path.join(self.__depotConfigDir, ident['id'], u'depot.ini')
			elif objType in ('ConfigState'):
				if ( ident['objectId'] == self.__serverId ):
					#raise Exception(u"Can't handle configStates for ConfigServer")
					return os.path.join(self.__depotConfigDir, ident['objectId'], u'depot.ini')
				elif os.path.isdir(os.path.join(self.__depotConfigDir, ident['objectId'])):
					#raise Exception(u"Can't handle configStates for DepotServer")
					return os.path.join(self.__depotConfigDir, ident['objectId'], u'depot.ini')
				else:
					return os.path.join(self.__clientConfigDir, ident['objectId'] + u'.ini')
			elif objType in ('ProductOnDepot'):
				return os.path.join(self.__depotConfigDir, ident['depotId'], u'depot.ini')
			elif objType in ('ProductOnClient'):
				return os.path.join(self.__clientConfigDir, ident['clientId'] + u'.ini')
			elif objType in ('ProductPropertyState'):
				if os.path.isdir(os.path.join(self.__depotConfigDir, ident['objectId'])):
					return os.path.join(self.__depotConfigDir, ident['objectId'], u'depot.ini')
				else:
					return os.path.join(self.__clientConfigDir, ident['objectId'] + u'.ini')
			elif objType in ('Group', 'HostGroup', 'ObjectToGroup'):
				return os.path.join(self.__clientGroupsFile)
		
		elif (fileType == 'pro'):
			pVer = u'_' + ident['productVersion'] + u'-' + ident['packageVersion']
			
			if objType == 'LocalbootProduct':
				return os.path.join(self.__productDir, ident['id'] + pVer + u'.localboot')
			elif objType == 'NetbootProduct':
				return os.path.join(self.__productDir, ident['id'] + pVer + u'.netboot')
			elif objType in ('Product', 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
				pId = u''
				if objType == 'Product':
					pId = ident['id']
				else:
					pId = ident['productId']
				
				# instead of searching the whole dir, let's check the only possible files
				if os.path.isfile(os.path.join(self.__productDir, pId + pVer + u'.localboot')):
					return os.path.join(self.__productDir, pId + pVer + u'.localboot')
				elif os.path.isfile(os.path.join(self.__productDir, pId + pVer + u'.netboot')):
					return os.path.join(self.__productDir, pId + pVer + u'.netboot')
		
		elif (fileType == 'sw'):
			if objType == 'AuditSoftware':
				return os.path.join(self.__auditDir, u'global.sw')
			elif objType == 'AuditSoftwareOnClient':
				return os.path.join(self.__auditDir, ident['clientId'] + u'.sw')
		
		elif (fileType == 'hw'):
			if objType == 'AuditHardware':
				return os.path.join(self.__auditDir, u'global.hw')
			elif objType == 'AuditHardwareOnHost':
				return os.path.join(self.__auditDir, ident['hostId'] + u'.hw')
		
		
		logger.error(u"No config-file returned! objType: '%s' fileType: '%s' filter: '%s'" % (objType, fileType, filter))
		
		return
	
	def _getIdents(self, objType, **filter):
		logger.debug(u"Getting idents for '%s' with filter '%s'" % (objType, filter))
		objIdents = []
		
		if objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
			filename = self._getConfigFile(objType, {}, 'ini')
			if os.path.isfile(filename):
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				for section in cp.sections():
					objIdents.append({'id': section})
		
		elif objType in ('OpsiClient', 'ProductOnClient'):
			for entry in os.listdir(self.__clientConfigDir):
				if not entry.lower().endswith('.ini'):
					continue
				try:
					hostId = forceHostId(entry[:-4])
					
					if objType == 'ProductOnClient':
						filename = self._getConfigFile(objType, {'clientId': hostId}, 'ini')
						iniFile = IniFile(filename = filename, ignoreCase = False)
						cp = iniFile.parse()
						for section in cp.sections():
							if section.endswith('-state'):
								objIdents.append(
									{
									'productId': section[:-6],
									'productType': cp.get(section, 'productType'),
									'clientId': hostId
									}
								)
					else:
						objIdents.append({'id': hostId})
				except:
					pass
		
		elif objType in ('OpsiDepotserver', 'OpsiConfigserver', 'ProductOnDepot'):
			for entry in os.listdir(self.__depotConfigDir):
				try:
					hostId = forceHostId(entry)
					if objType == 'OpsiConfigserver' and hostId != self.__serverId:
						continue
					
					if objType == 'ProductOnDepot':
						filename = self._getConfigFile(objType, {'depotId': hostId}, 'ini')
						iniFile = IniFile(filename = filename, ignoreCase = False)
						cp = iniFile.parse()
						for section in cp.sections():
							if section.endswith('-state'):
								objIdents.append(
									{
									'productId': section[:-6],
									'productType': cp.get(section, 'producttype'),
									'productVersion': cp.get(section, 'productversion'),
									'packageVersion': cp.get(section, 'packageversion'),
									'depotId': hostId
									}
								)
					else:
						objIdents.append({'id': hostId})
				except:
					pass
		
		elif objType in ('Product', 'LocalbootProduct', 'NetbootProduct', 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
			for entry in os.listdir(self.__productDir):
				entry = entry.lower()
				# productId, productVersion, packageVersion, propertyId
				if not ( entry.endswith('.localboot') and objType != 'NetbootProduct' ):
					if not ( entry.endswith('.netboot') and objType != 'LocalbootProduct' ):
						continue # doesn't fit: next file
				
				#example:            exampleexampleexa  _ 123.123 - 123.123  .localboot
				match = re.search('^([a-zA-Z0-9\_\.-]+)\_([\w\.]+)-([\w\.]+)\.(local|net)boot$', entry)
				if not match:
					continue
				else:
					logger.debug2(u"Found match: id='%s', productVersion='%s', packageVersion='%s'" \
						% (match.group(1), match.group(2), match.group(3)) )
				
				if objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
					objIdents.append({'id': match.group(1), 'productVersion': match.group(2), 'packageVersion': match.group(3)})
				
				elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
					filename = os.path.join(self.__productDir, entry)
					packageControlFile = PackageControlFile(filename = filename)
					if objType == 'ProductDependency':
						for productDependency in packageControlFile.getProductDependencies():
							objIdents.append(productDependency.getIdent(returnType = 'dict'))
					else:
						for productProperty in packageControlFile.getProductProperties():
							objIdents.append(productProperty.getIdent(returnType = 'dict'))
		
		elif objType in ('ConfigState', 'ProductPropertyState'):
			objectIds = []
			
			for entry in os.listdir(self.__clientConfigDir):
				if not entry.lower().endswith('.ini'):
					continue
				
				try:
					objectIds.append(forceHostId(entry[:-4]))
				except:
					pass
			
			for objectId in objectIds:
				if not self._objectHashMatches({'objectId': objectId }, **filter):
					continue
				
				filename = self._getConfigFile(objType, {'objectId': objectId}, 'ini')
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				
				if objType == 'ConfigState' and cp.has_section('generalconfig'):
					for option in cp.options('generalconfig'):
						objIdents.append(
							{
							'configId': option,
							'objectId': objectId
							}
						)
				elif objType == 'ProductPropertyState':
					for section in cp.sections():
						if not section.endswith('-install'):
							continue
						
						for option in cp.options(section):
							objIdents.append(
								{
								'productId': section[:-8],
								'propertyId': option,
								'objectId': objectId
								}
							)
		
		elif objType in ('Group', 'HostGroup', 'ObjectToGroup'):
			filename = self._getConfigFile(objType, {}, 'ini')
			if os.path.isfile(filename):
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				
				for section in cp.sections():
					if objType == 'ObjectToGroup':
						for option in cp.options(section):
							try:
								if not option in ('description', 'parentGroupId', 'notes', 'parentgroupid'):
									objIdents.append(
										{
										'groupId': section,
										'objectId': forceHostId(option)
										}
									)
							except:
								logger.error(u"_getIdents(): Found bad option '%s' in section '%s' in file '%s'" \
									% (option, section, filename))
					else:
						objIdents.append(
							{
							'id': section
							}
						)
		
		else:
			logger.warning(u"_getIdents(): Unhandled objType '%s'" % objType)
		
		if not objIdents:
			return objIdents
		
		needFilter = False
		for attribute in objIdents[0].keys():
			if filter.get(attribute):
				needFilter = True
				break
		
		if not needFilter:
			return objIdents
		
		filteredObjIdents = []
		for ident in objIdents:
			if self._objectHashMatches(ident, **filter):
				filteredObjIdents.append(ident)
		
		return filteredObjIdents
	
	def _adaptObjectHashAttributes(self, objHash, ident, attributes):
		if not attributes:
			return objHash
		for attribute in objHash.keys():
			if not attribute in attributes and not attribute in ident.keys():
				del objHash[attribute]
		return objHash
	
	def _read(self, objType, attributes, **filter):
		if filter.get('type') and objType not in forceList(filter.get('type')):
			return []
		
		if not self._mappings.has_key(objType):
			raise Exception(u"Mapping not found for object type '%s'" % objType)
			
		logger.debug(u"Filter: %s" % filter)
		logger.debug(u"Attributes: %s" % attributes)
		
		mappings = {}
		for mapping in self._mappings[objType]:
			if (not attributes or mapping['attribute'] in attributes) or mapping['attribute'] in filter.keys():
				if not mappings.has_key(mapping['fileType']):
					mappings[mapping['fileType']] = []
				
				mappings[mapping['fileType']].append(mapping)
		
		logger.debug(u"Using mappings %s" % mappings)
		
		objects = []
		for ident in self._getIdents(objType, **filter):
			objHash = dict(ident)
			
			for (fileType, mapping) in mappings.items():
				filename = self._getConfigFile(objType, ident, fileType)
				
				if not os.path.exists(os.path.dirname(filename)):
					raise BackendIOError(u"Directory '%s' not found" % os.path.dirname(filename))
				
				if (fileType == 'key'):
					hostKeys = HostKeyFile(filename = filename)
					for m in mapping:
						objHash[m['attribute']] = hostKeys.getOpsiHostKey(ident['id'])
				
				elif (fileType == 'ini') or (fileType == 'sw'):
					iniFile = IniFile(filename = filename, ignoreCase = False)
					cp = iniFile.parse()
					
					for m in mapping:
						attribute = m['attribute']
						section = '' #will be build from sectionParts
						option = m['option']
						
						sectionParts = m['section'].split(';')
						
						for i in range(len(sectionParts)):
							match = self._placeholderRegex.search(sectionParts[i])
							if match:
								replaceValue = objHash[match.group(1)]
								if objType == 'ProductOnClient':
									replaceValue.replace('LocalbootProduct', 'localboot').replace('NetbootProduct', 'netboot')
								sectionParts[i] = sectionParts[i].replace(u'<%s>' % match.group(1), replaceValue)
							
							match = self._placeholderRegex.search(option)
							if match:
								option = option.replace(u'<%s>' % match.group(1), objHash[match.group(1)])
							
							#rebuild section
							sectionParts[i] = sectionParts[i].replace(';', '\\;')
							if section == '':
								section = sectionParts[i]
							else:
								section = section + ';' + sectionParts[i]
						
						#print "=========>>>> m: %s section: %s, option: %s" % (m, section, option)
						if cp.has_option(section, option):
							value = cp.get(section, option)
							#print "=========>>>> %s section: %s, option: %s" % (value, section, option)
							if m.get('json'):
								value = fromJson(value)
							else:
								value = value.replace(u'\\n', u'\n')
							
							if objType in ('ProductOnClient') and value.find(':') != -1:
								if attribute == 'installationStatus':
									value = value.split(u':', 1)[0]
								elif attribute == 'actionRequest':
									value = value.split(u':', 1)[1]
							
							objHash[m['attribute']] = value
					logger.debug(u"Got object hash from ini file: %s" % objHash)
					
				elif (fileType == 'pro'):
					packageControlFile = PackageControlFile(filename = filename)
					
					if   objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
						objHash = packageControlFile.getProduct().toHash()
					
					elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
						knownObjects = []
						if objType in ('ProductDependency'):
							knownObjects = packageControlFile.getProductDependencies()
						else:
							knownObjects = packageControlFile.getProductProperties()
						
						for obj in knownObjects:
							objIdent = obj.getIdent(returnType = 'dict')
							matches = True
							for (key, value) in ident.items():
								if (objIdent[key] != value):
									matches = False
									break
							if matches:
								objHash = obj.toHash()
								break
				
				elif (fileType == 'hw'):
					if   objType in ('AuditHardware'):
						# objHash only has idents
						pass
					
					elif objType in ('AuditHardwareOnHost'):
						iniFile = IniFile(filename = filename, ignoreCase = False)
						cp = iniFile.parse()
						
						options = {}
						
						for section in cp.sections():
							if not section.startswith(ident['hardwareClass'] + '_'):
								continue
							
							matched = True
							for (key, value) in objHash.items():
								if not (option != 'hardwareClass' and cp.has_option(section, option) and value == cp.get(section, option)):
									matched = False
							
							if matched:
								for option in ('firstseen', 'lastseen', 'state'):
									if cp.has_option(section, option):
										objHash[option] = cp.get(section, option)
			Class = eval(objType)
			if self._objectHashMatches(Class.fromHash(objHash).toHash(), **filter):
				objHash = self._adaptObjectHashAttributes(objHash, ident, attributes)
				objects.append(Class.fromHash(objHash))
		return objects
	
	def _write(self, obj, mode='create'):
		objType = obj.getType()
		
		if (objType == 'OpsiConfigserver'):
			if (self.__serverId != obj.getId()):
				raise Exception(u"File31 backend can only handle this config server '%s', not '%s'" \
					% (self.__serverId, obj.getId()))
#		elif (objType == 'OpsiDepotserver'):
#			if os.path.isfile(self._getConfigFile('OpsiClient', {'id':obj.getId()}, 'ini')):
#				raise Exception(u"depot id is a client")
#		elif (objType == 'OpsiClient'):
#			if os.path.isfile(self._getConfigFile('OpsiDepotserver', {'id':obj.getId()}, 'ini')):
#				raise Exception(u"client id is a depot")
		
		if not self._mappings.has_key(objType):
			raise Exception(u"Mapping not found for object type '%s'" % objType)
		
		mappings = {}
		for mapping in self._mappings[objType]:
			if not mappings.has_key(mapping['fileType']):
				mappings[mapping['fileType']] = {}
			mappings[mapping['fileType']][mapping['attribute']] = mapping
		
		for (fileType, mapping) in mappings.items():
			filename = self._getConfigFile(objType, obj.getIdent(returnType = 'dict'), fileType)
			
			if not os.path.exists(os.path.dirname(filename)):
				logger.info(u"Creating path: '%s'" % os.path.dirname(filename))
				self._mkdir(os.path.dirname(filename))
			
			if (fileType == 'key'):
				if (mode == 'create') or (mode == 'update' and obj.getOpsiHostKey()):
					hostKeys = HostKeyFile(filename = filename)
					hostKeys.create(group = 'pcpatch', mode = 0660)
					hostKeys.setOpsiHostKey(obj.getId(), obj.getOpsiHostKey())
					hostKeys.generate()
			
			elif (fileType == 'ini') or (fileType == 'sw'):
				iniFile = IniFile(filename = filename, ignoreCase = False)
				iniFile.create(group = 'pcpatch', mode = 0660)
				cp = iniFile.parse()
				
				if (mode == 'create'):
					if objType in ('OpsiClient', 'OpsiDepotserver', 'OpsiConfigserver'):
						iniFile.delete()
						
						if objType in ('OpsiClient'):
							shutil.copyfile(os.path.join(self.__clientTemplateDir, self.__defaultClientTemplateName + '.ini'), filename)
						
						iniFile = IniFile(filename = filename, ignoreCase = False)
						iniFile.create(group = 'pcpatch', mode = 0660)
						cp = iniFile.parse()
					else:
						newSection = ''
						
						if   objType in ('Config', 'UnicodeConfig', 'BoolConfig', 'Group', 'HostGroup'):
							newSection = obj.getId()
						elif objType in ('ProductOnDepot', 'ProductOnClient'):
							newSection = obj.getProductId() + u'-state'
						elif objType in ('ProductPropertyState'):
							newSection = obj.getPropertyId() + u'-install'
						elif objType in ('AuditSoftware', 'AuditSoftwareOnClient'):
							idents = obj.getIdent(returnType = 'dict')
							newSection = idents['name'].replace(';', '\\;') + ';' + \
								idents['version'].replace(';', '\\;') + ';' + \
								idents['subVersion'].replace(';', '\\;') + ';' + \
								idents['language'].replace(';', '\\;') + ';' + \
								idents['architecture'].replace(';', '\\;')
							if objType == 'AuditSoftwareOnClient':
								newSection = newSection + ';' + idents['clientId'].replace(';', '\\;')
						
						if newSection != '' and cp.has_section(newSection):
							cp.remove_section(newSection)
				
				objHash = obj.toHash()
				
				for (attribute, value) in objHash.items():
					if value is None and (mode == 'update'):
						continue
					
					attributeMapping = mapping.get(attribute, mapping.get('*'))
					
					if not attributeMapping is None:
						section = ''
						option = attributeMapping['option']
						
						sectionParts = attributeMapping['section'].split(';')
						
						for i in range(len(sectionParts)):
							match = self._placeholderRegex.search(sectionParts[i])
							if match:
								replaceValue = objHash[match.group(1)]
								if objType in ('ProductOnClient'):
									replaceValue.replace('LocalbootProduct', 'localboot').replace('NetbootProduct', 'netboot')
								sectionParts[i] = sectionParts[i].replace(u'<%s>' % match.group(1), replaceValue)
							
							match = self._placeholderRegex.search(option)
							if match:
								option = option.replace(u'<%s>' % match.group(1), objHash[match.group(1)])
							
							#rebuild section
							sectionPart = sectionParts[i].replace(';', '\\;')
							
							if section == '':
								section = sectionPart
							else:
								section = section + ';' + sectionPart
						
						if objType in ('ProductOnClient'):
							if attribute in ('installationStatus', 'actionRequest'):
								(installationStatus, actionRequest) = (u'', u'')
								if cp.has_option(section, option):
									installationStatus = cp.get(section, option)
								if installationStatus.find(u':') != -1:
									(installationStatus, actionRequest) = installationStatus.split(u':', 1)
								if not value is None:
									if   (attribute == 'installationStatus'):
										installationStatus = value
									elif (attribute == 'actionRequest'):
										actionRequest = value
								value = installationStatus + u':' + actionRequest
						
						if not value is None:
							if attributeMapping.get('json'):
								value = toJson(value)
							elif ( isinstance(value, str) or isinstance(value, unicode) ):
								value = forceUnicode(value)
								value = value.replace(u"\n", u"\\n")
							
							if not cp.has_section(section):
								cp.add_section(section)
							
							cp.set(section, option, forceUnicode(value).replace('%', '%%'))
				
				iniFile.generate(cp)
			
			elif (fileType == 'pro'):
				packageControlFile = PackageControlFile(filename = filename)
				packageControlFile.create(group = 'pcpatch', mode = 0660)
				
				if objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
					if (mode == 'create'):
						packageControlFile.setProduct(obj)
					else:
						productHash = packageControlFile.getProduct().toHash()
						for (attribute, value) in obj.toHash().items():
							if value is None:
								continue
							productHash[attribute] = value
						packageControlFile.setProduct(Product.fromHash(productHash))
				
				elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
					oldList = []
					newList = []
					
					if objType == 'ProductDependency':
						oldList = packageControlFile.getProductDependencies()
					else:
						oldList = packageControlFile.getProductProperties()
					
					objInOldList = False
					for oldItem in oldList:
						if oldItem.getIdent() == obj.getIdent():
							objInOldList = True
							
							if mode == 'create':
								newList.append(obj)
							else:
								newHash = oldItem.toHash()
								for (attribute, value) in obj.toHash().items():
									if value is not None:
										newHash[attribute] = value
								
								Class = eval(objType)
								newList.append(Class.fromHash(newHash))
						else:
							newList.append(oldItem)
					
					if not objInOldList:
						newList.append(obj)
					
					if objType == 'ProductDependency':
						packageControlFile.setProductDependencies(newList)
					else:
						packageControlFile.setProductProperties(newList)
				
				packageControlFile.generate()
			
			elif (fileType == 'hw'):
				iniFile = IniFile(filename = filename, ignoreCase = False)
				iniFile.create(group = 'pcpatch', mode = 0660)
				cp = iniFile.parse()
				
				section = obj.getHardwareClass() + '_'
				sectionNr = 0
				options = {}
				
				objHashItems = obj.toHash().items()
				
				for oldSection in cp.sections():
					if not oldSection.lower().startswith(section.lower()):
						continue
					
					matched = True
					for (key, value) in objHashItems:
						if not (key != 'hardwareClass' and cp.has_option(oldSection, key) and value == cp.get(oldSection, key)):
							matched = False
					
					try:
						if matched:
							sectionNr = forceInt(oldSection[len(section):])
							break
						else:
							oldSectionNr = forceInt(oldSection[len(section):])
							if sectionNr < oldSectionNr + 1:
								sectionNr = oldSectionNr + 1
					except:
						logger.error(u"Found bad section '%s' in file '%s'" % (oldSection, filename))
				
				section = section + forceUnicode(sectionNr)
				
				if (mode == 'create') and cp.has_section(section):
					cp.remove_section(section)
				
				for (option, value) in obj.toHash().items():
					if option == 'hardwareClass':
						continue
					
					if value is None:
						if cp.has_option(section, option):
							cp.remove_option(section, option)
						continue
					
					if not cp.has_section(section):
						cp.add_section(section)
					
					cp.set(section, option, forceUnicode(value).replace('%', '%%'))
				
				iniFile.generate(cp)
	
	def _delete(self, objList):
		objType = u''
		if objList:
			#objType is not always correct, but _getConfigFile() is
			#within ifs obj.getType() from obj in objList should be used
			objType = objList[0].getType()
		
		if objType in ('OpsiClient', 'OpsiConfigserver', 'OpsiDepotserver'):
			hostKeyFile = HostKeyFile(self._getConfigFile('', {}, 'key'))
			for obj in objList:
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				hostKeyFile.deleteOpsiHostKey(obj.getId())
				#TODO: can delete configserver?
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'ini')
				if obj.getType() in ('OpsiConfigserver', 'OpsiDepotserver'):
					if os.path.isdir(os.path.dirname(filename)):
						shutil.rmtree(os.path.dirname(filename))
				elif obj.getType() in ('OpsiClient'):
					if os.path.isfile(filename):
						os.unlink(filename)
			hostKeyFile.generate()
		
		elif objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
			filename = self._getConfigFile(objType, {}, 'ini')
			iniFile = IniFile(filename = filename, ignoreCase = False)
			cp = iniFile.parse()
			for obj in objList:
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if cp.has_section(obj.getId()):
					cp.remove_section(obj.getId())
					logger.debug2(u"Removed section '%s'" % obj.getId())
			iniFile.generate(cp)
		
		elif objType in ('ConfigState'):
			#TODO: opens every file anew
			for obj in objList:
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'ini')
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if cp.has_option('generalconfig', obj.getConfigId()):
					cp.remove_option('generalconfig', obj.getConfigId())
					logger.debug2(u"Removed option in generalconfig '%s'" % obj.getConfigId())
				iniFile.generate(cp)
		
		elif objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
			for obj in objList:
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'pro' )
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if os.path.isfile(filename):
					os.unlink(filename)
					logger.debug2(u"Removed file '%s'" % filename)
		
		elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
			filenames = []
			
			# TODO: files werden nur einmal eingelesen, aber umstaendlich
			for entry in os.listdir(self.__productDir):
				entry = entry.lower()
				# productId, productVersion, packageVersion, propertyId
				if (not entry.endswith('.localboot')) and (not entry.endswith('.netboot')):
					continue
				
				#example:            exampleexampleexa  _ 123.123 - 123.123  .localboot
				match = re.search('^([a-zA-Z0-9\_\.-]+)\_([\w\.]+)-([\w\.]+)\.(local|net)boot$', entry)
				if not match:
					continue
				
				logger.debug2(u"Found match: id='%s', productVersion='%s', packageVersion='%s'" \
					% (match.group(1), match.group(2), match.group(3)) )
				
				matched = False
				for item in objList:
					if (match.group(1) == item.getProductId()):
						if (match.group(2) == item.getProductVersion()):
							if (match.group(3) == item.getPackageVersion()):
								matched = True
				
				if not matched:
					continue
				
				filenames.append(os.path.join(self.__productDir, entry))
			
			for filename in filenames:
				packageControlFile = PackageControlFile(filename = filename)
				newList = []
				oldList = []
				
				if objType == 'ProductDependency':
					oldList = packageControlFile.getProductDependencies()
				else:
					oldList = packageControlFile.getProductProperties()
				
				for obj in objList:
					logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
					for oldItem in oldList:
						if oldItem.getIdent() == obj.getIdent():
							logger.debug2(u"Removed '%s'" % obj.getIdent())
							continue
						newList.append(item)
				
				if objType == 'ProductDependency':
					packageControlFile.setProductDependencies(newList)
				else:
					packageControlFile.setProductProperties(newList)
				
				packageControlFile.generate()
		
		elif objType in ('ProductOnDepot', 'ProductOnClient'):
			filenames = []
			for obj in objList:
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'ini')
				
				inFilenames = False
				for f in filenames:
					if filename == f:
						inFilenames = True
						break
				
				if not inFilenames:
					filenames.append(filename)
			
			for filename in filenames:
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				
				for obj in objList:
					logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
					if cp.has_section(obj.getProductId() + '-state'):
						cp.remove_section(obj.getProductId() + '-state')
						logger.debug2(u"Removed section '%s'" % obj.getProductId() + '-state')
				
				iniFile.generate(cp)
		
		elif objType in ('ProductPropertyState'):
			for obj in objList:
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'ini')
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				
				if cp.has_section(obj.getProductId() + '-install'):
					cp.remove_section(obj.getProductId() + '-install')
					logger.debug2(u"Removed section '%s'" % obj.getProductId() + '-install')
				
				iniFile.generate(cp)
		
		elif objType in ('Group', 'HostGroup', 'ObjectToGroup'):
			filename = self._getConfigFile(objType, {}, 'ini')
			iniFile = IniFile(filename = filename, ignoreCase = False)
			cp = iniFile.parse()
			
			for obj in objList:
				section = u'%s' % obj.getId()
				
				logger.info(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if obj.getType() == 'ObjectToGroup':
					if cp.has_option(obj.getGroupId(), obj.getObjectId()):
						cp.remove_option(obj.getGroupId(), obj.getObjectId())
						logger.debug2(u"Removed option '%s' in section '%s'" \
							% (obj.getGroupId(), obj.getObjectId()))
				else:
					if cp.has_section(section):
						cp.remove_section(section)
						logger.debug2(u"Removed section '%s'" % section)
			
			iniFile.generate(cp)
		
		else:
			logger.warning(u"_delete(): unhandled objType: '%s'" % objType)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		logger.notice(u"Inserting host: '%s'" % host.getIdent())
		self._write(host, mode = 'create')
		logger.notice(u"Inserted host.")
	
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		logger.notice(u"Updating host: '%s'" % host.getIdent())
		self._write(host, mode = 'update')
		logger.notice(u"Updated host.")
	
	def host_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.host_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting hosts ...")
		result = self._read('OpsiDepotserver', attributes, **filter)
		opsiConfigServers = self._read('OpsiConfigserver', attributes, **filter)
		if opsiConfigServers:
			for i in range(len(result)):
				if (result[i].getId() == opsiConfigServers[0].getId()):
					result[i] = opsiConfigServers[0]
					break
		result.extend(self._read('OpsiClient', attributes, **filter))
		logger.notice(u"Got hosts.")
		
		return result
	
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		logger.notice(u"Deleting hosts ...")
		self._delete(forceObjectClassList(hosts, Host))
		logger.notice(u"Deleted hosts.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		
		logger.notice(u"Inserting config: '%s'" % config.getIdent())
		self._write(config, mode = 'create')
		logger.notice(u"Inserted config.")
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
		logger.notice(u"Updating config: '%s'" % config.getIdent())
		self._write(config, mode = 'update')
		logger.notice(u"Updated config.")
	
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting configs ...")
		result = self._read('Config', attributes, **filter)
		logger.notice(u"Returning configs.")
		
		return result
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		
		logger.notice(u"Deleting configs ...")
		self._delete(forceObjectClassList(configs, Config))
		logger.notice(u"Deleted configs.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
		
		logger.notice(u"Inserting configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'create')
		logger.notice(u"Inserted configState.")
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
		
		logger.notice(u"Updating configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'update')
		logger.notice(u"Updated configState.")
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting configStates ...")
		result = self._read('ConfigState', attributes, **filter)
		logger.notice(u"Returning configStates.")
		
		return result
	
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
		
		logger.notice(u"Deleting configStates ...")
		self._delete(forceObjectClassList(configStates, ConfigState))
		logger.notice(u"Deleted configStates.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		
		logger.notice(u"Inserting product: '%s'" % product.getIdent())
		self._write(product, mode = 'create')
		logger.notice(u"Inserted product.")
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		
		logger.notice(u"Updating product: '%s'" % product.getIdent())
		self._write(product, mode = 'update')
		logger.notice(u"Updated product.")
	
	def product_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.product_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting products ...")
		result = self._read('LocalbootProduct', attributes, **filter)
		result.extend(self._read('NetbootProduct', attributes, **filter))
		logger.notice(u"Got products.")
		
		return result
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
		
		logger.notice(u"Deleting products ...")
		self._delete(forceObjectClassList(products, Product))
		logger.notice(u"Deleted products.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		
		logger.notice(u"Inserting productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'create')
		logger.notice(u"Inserted productProperty.")
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		
		logger.notice(u"Updating productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'update')
		logger.notice(u"Updated productProperty.")
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting productProperties ...")
		result = self._read('ProductProperty', attributes, **filter)
		logger.notice(u"Got productProperties.")
		
		return result
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		
		logger.notice(u"Deleting productProperties ...")
		self._delete(forceObjectClassList(productProperties, ProductProperty))
		logger.notice(u"Deleted productProperties.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		
		logger.notice(u"Inserting productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'create')
		logger.notice(u"Inserted productDependency.")
	
	def productDependency_updateObject(self, productDependency):
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		
		logger.notice(u"Updating productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'update')
		logger.notice(u"Updated productDependency.")
	
	def productDependency_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productDependencies ...")
		result = self._read('ProductDependency', attributes, **filter)
		logger.notice(u"Got productDependencies.")
		
		return result
	
	def productDependency_deleteObjects(self, productDependencies):
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		
		logger.notice(u"Deleting productDependencies ...")
		self._delete(forceObjectClassList(productDependencies, ProductDependency))
		logger.notice(u"Deleted productDependencies.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		
		logger.notice(u"Inserting productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'create')
		logger.notice(u"Inserted productOnDepot.")
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
		
		logger.notice(u"Updating productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'update')
		logger.notice(u"Updated productOnDepot.")
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productOnDepots ...")
		result = self._read('ProductOnDepot', attributes, **filter)
		logger.notice(u"Got productOnDepots.")
		
		return result
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
		logger.notice(u"Deleting productOnDepots ...")
		self._delete(forceObjectClassList(productOnDepots, ProductOnDepot))
		logger.notice(u"Deleted productOnDepots.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		
		logger.notice(u"Inserting productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'create')
		logger.notice(u"Inserted productOnClient.")
	
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		
		logger.notice(u"Updating productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'update')
		logger.notice(u"Updated productOnClient.")
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productOnClient ...")
		result = self._read('ProductOnClient', attributes, **filter)
		logger.notice(u"Got productOnClient.")
		
		return result
	
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		
		logger.notice(u"Deleting productOnClients ...")
		self._delete(forceObjectClassList(productOnClients, ProductOnClient))
		logger.notice(u"Deleted productOnClients.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
		
		logger.notice(u"Inserting productPropertyState: '%s'" % productPropertyState.getIdent())
		self._write(productPropertyState, mode = 'create')
		logger.notice(u"Inserted productPropertyState.")
	
	def productPropertyState_updateObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
		
		logger.notice(u"Updating productPropertyState: '%s'" % productPropertyState.getIdent())
		self._write(productPropertyState, mode = 'update')
		logger.notice(u"Updated productPropertyState.")
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productPropertyStates ...")
		result = self._read('ProductPropertyState', attributes, **filter)
		logger.notice(u"Got productPropertyStates.")
		
		return result
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
		
		logger.notice(u"Deleting productPropertyStates ...")
		self._delete(forceObjectClassList(productPropertyStates, ProductPropertyState))
		logger.notice(u"Deleted productPropertyStates.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		ConfigDataBackend.group_insertObject(self, group)
		
		logger.notice(u"Inserting group: '%s'" % group.getIdent())
		self._write(group, mode = 'create')
		logger.notice(u"Inserted group.")
	
	def group_updateObject(self, group):
		ConfigDataBackend.group_updateObject(self, group)
		
		logger.notice(u"Updating group: '%s'" % group.getIdent())
		self._write(group, mode = 'update')
		logger.notice(u"Updated group.")
	
	def group_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting groups ...")
		result = self._read('Group', attributes, **filter)
		logger.notice(u"Got groups.")
		
		return result
	
	def group_deleteObjects(self, groups):
		ConfigDataBackend.group_deleteObjects(self, groups)
		
		logger.notice(u"Deleting groups ...")
		self._delete(forceObjectClassList(groups, Group))
		logger.notice(u"Deleted groups.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
		
		logger.notice(u"Inserting objectToGroup: '%s'" % objectToGroup.getIdent())
		self._write(objectToGroup, mode = 'create')
		logger.notice(u"Inserted objectToGroup.")
	
	def objectToGroup_updateObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
		
		logger.notice(u"Updating objectToGroup: '%s'" % objectToGroup.getIdent())
		self._write(objectToGroup, mode = 'update')
		logger.notice(u"Updated objectToGroup.")
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting objectToGroups ...")
		result = self._read('ObjectToGroup', attributes, **filter)
		logger.notice(u"Got objectToGroups.")
		
		return result
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		
		logger.notice(u"Deleting objectToGroups ...")
		self._delete(forceObjectClassList(objectToGroups, ObjectToGroup))
		logger.notice(u"Deleted objectToGroups.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		return
		ConfigDataBackend.auditSoftware_insertObject(self, auditSoftware)
		
		logger.notice(u"Inserting auditSoftware: '%s'" % auditSoftware.getIdent())
#		self._write(auditSoftware, mode = 'create')
		logger.notice(u"Inserted auditSoftware.")
	
	def auditSoftware_updateObject(self, auditSoftware):
		return
		ConfigDataBackend.auditSoftware_updateObject(self, auditSoftware)
		
		logger.notice(u"Updating auditSoftware: '%s'" % auditSoftware.getIdent())
#		self._write(auditSoftware, mode = 'update')
		logger.notice(u"Updated auditSoftware.")
	
	def auditSoftware_getObjects(self, attributes=[], **filter):
		return []
		ConfigDataBackend.auditSoftware_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting auditSoftwares ...")
#		result = self._read('AuditSoftware', attributes, **filter)
		result = []
		logger.notice(u"Got auditSoftwares.")
		
		return result
	
	def auditSoftware_deleteObjects(self, auditSoftwares):
		return
		ConfigDataBackend.auditSoftware_deleteObjects(self, auditSoftwares)
		
		logger.notice(u"Deleting auditSoftwares ...")
#		self._delete(forceObjectClassList(auditSoftwares, AuditSoftware))
		logger.notice(u"Deleted auditSoftwares.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		return
		ConfigDataBackend.auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient)
		
		logger.notice(u"Inserting auditSoftwareOnClient: '%s'" % auditSoftwareOnClient.getIdent())
#		self._write(auditSoftwareOnClient, mode = 'create')
		logger.notice(u"Inserted auditSoftwareOnClient.")
	
	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		return
		ConfigDataBackend.auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient)
		
		logger.notice(u"Updating auditSoftwareOnClient: '%s'" % auditSoftwareOnClient.getIdent())
#		self._write(auditSoftwareOnClient, mode = 'update')
		logger.notice(u"Updated auditSoftwareOnClient.")
	
	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		return []
		ConfigDataBackend.auditSoftwareOnClient_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting auditSoftwareOnClients ...")
#		result = self._read('AuditSoftwareOnClient', attributes, **filter)
		result = []
		logger.notice(u"Got auditSoftwareOnClients.")
		
		return result
	
	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		return
		ConfigDataBackend.auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients)
		
		logger.notice(u"Deleting auditSoftwareOnClients ...")
#		self._delete(forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient))
		logger.notice(u"Deleted auditSoftwareOnClients.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def auditHardware_insertObject(self, auditHardware):
		return
		ConfigDataBackend.auditHardware_insertObject(self, auditHardware)
		
		logger.notice(u"Inserting auditHardware: '%s'" % auditHardware.getIdent())
#		self._write(auditHardware, mode = 'create')
		logger.notice(u"Inserted auditHardware.")
	
	def auditHardware_updateObject(self, auditHardware):
		return
		ConfigDataBackend.auditHardware_updateObject(self, auditHardware)
		
		logger.notice(u"Updating auditHardware: '%s'" % auditHardware.getIdent())
#		self._write(auditHardware, mode = 'update')
		logger.notice(u"Updated auditHardware.")
	
	def auditHardware_getObjects(self, attributes=[], **filter):
		return []
		ConfigDataBackend.auditHardware_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting auditHardwares ...")
#		result = self._read('AuditHardware', attributes, **filter)
		result = []
		logger.notice(u"Got auditHardwares.")
		
		return result
	
	def auditHardware_deleteObjects(self, auditHardwares):
		return
		ConfigDataBackend.auditHardware_deleteObjects(self, auditHardwares)
		
		logger.notice(u"Deleting auditHardwares ...")
#		self._delete(forceObjectClassList(auditHardwares, AuditHardware))
		logger.notice(u"Deleted auditHardwares.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		return
		ConfigDataBackend.auditHardwareOnHost_insertObject(self, auditHardwareOnHost)
		
		logger.notice(u"Inserting auditHardwareOnHost: '%s'" % auditHardwareOnHost.getIdent())
#		self._write(auditHardwareOnHost, mode = 'create')
		logger.notice(u"Inserted auditHardwareOnHost.")
	
	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		return
		ConfigDataBackend.auditHardwareOnHost_updateObject(self, auditHardwareOnHost)
		
		logger.notice(u"Updating auditHardwareOnHost: '%s'" % auditHardwareOnHost.getIdent())
#		self._write(auditHardwareOnHost, mode = 'update')
		logger.notice(u"Updated auditHardwareOnHost.")
	
	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):
		return []
		ConfigDataBackend.auditHardwareOnHost_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting auditHardwareOnHosts ...")
#		result = self._read('AuditHardwareOnHost', attributes, **filter)
		logger.notice(u"Got auditHardwareOnHosts.")
		
		return result
	
	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):
		return
		ConfigDataBackend.auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts)
		
		logger.notice(u"Deleting auditHardwareOnHosts ...")
#		self._delete(forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost))
		logger.notice(u"Deleted auditHardwareOnHosts.")
	
	
	
	
	def _audit(self, objList, mode):
		if not mode in ('create', 'update', 'delete'):
			raise Exception(u"Wrong parameter '%s' given!" % (mode))
		
		objList = forceList(objList)
		filenames = []
		
		for obj in objList:
			fileType = ''
			if obj.getType() in ('AuditSoftware', 'AuditSoftwareOnClient'):
				fileType = 'sw'
			elif obj.getType() in ('AuditHardware', 'AuditHardwareOnHost'):
				fileType = 'hw'
			else:
				logger.error(u"Wrong type delivered: '%s' in object: %s" % (obj.getType()), obj.getIdent())
				continue
			
			filename = self._getConfigFile(obj.getType(), obj.getIdent(returnType = 'dict'), fileType)
			if mode == 'create' or os.path.isfile(filename):
				if not filename in filenames:
					filenames.append(filename)
			else:
				logger.info(u"Could not %s %s: '%s' has no config file '%s'" \
					% (mode, obj.getType(), obj.getIdent()), filename)
		
		for filename in filenames:
			iniFile = IniFile(filename = filename, ignoreCase = False)
			if (mode == 'create'):
				iniFile.create(group = 'pcpatch', mode = 0660)
			cp = iniFile.parse()
			
			remainingObjs = objList
			unprocessedObjs = []
			
			while not len(remainingObjs) > 0:
				for obj in remainingObjs:
					fileType = 'sw'
					if obj.getType() in ('AuditHardware', 'AuditHardwareOnHost'):
						fileType = 'hw'
					
					if filename != self._getConfigFile(obj.getType(), obj.getIdent(returnType = 'dict'), fileType):
						unprocessedObjs.append(obj)
					else:
						section = u''
						
						if fileType == 'hw':
							section == u'%s_' % obj.getHardwareClass()
							sectionNr = 0
							options = {}
							
							for oldSection in cp.sections():
								oldSectionNrIndex = oldSection.rfind('_') + 1
								if oldSection[:sectionNrIndex] != section:
									continue
								
								matched = True
								for (key, value) in objHashItems:
									if key == 'hardwareClass':
										continue
									if not (cp.has_option(oldSection, key) and value == cp.get(oldSection, key)):
										matched = False
								
								try:
									if matched:
										sectionNr = forceInt(oldSection[oldSectionNrIndex:])
										break
									else:
										oldSectionNr = forceInt(oldSection[oldSectionNrIndex:])
										if sectionNr < oldSectionNr + 1:
											sectionNr = oldSectionNr + 1
								except:
									logger.error(u"Found bad section '%s' in file '%s'" % (oldSection, filename))
							
							section = u'%s%s' % (section, sectionNr)
						else:
							section = u'%s;%s;%s;%s;%s' % (
								idents['name'].replace(';', '\\;'),
								idents['version'].replace(';', '\\;'),
								idents['subVersion'].replace(';', '\\;'),
								idents['language'].replace(';', '\\;'),
								idents['architecture'].replace(';', '\\;')
								)
						
						if mode in ('create', 'delete') and cp.has_section(section):
							cp.remove_section(section)
							if mode == 'create':
								cp.add_section(section)
								logger.info(u"Emptied section '%s' in file '%s'" % (section, filename))
							else:
								logger.info(u"Deleted section '%s' in file '%s'" % (section, filename))
						
						if mode in ('create', 'update'):
							for (key, value) in objHashItems:
								option = u'%s' % (key.lower())
								if value is None:
									logger.debug2(u"Ignoring key '%s' with None-value" % (key))
									continue
								if key in ('name', 'version', 'subVersion', 'language', 'architecture', 'clientId', 'hostId', 'type'):
									logger.debug2(u"Ignoring already processed key '%s'" % (key))
									continue
								
								if ( isinstance(value, str) or isinstance(value, unicode) ):
									value = u'%s' % value.replace(u'\n', u'\\n').replace(u';', u'\\;').replace(u'#', u'\\#').replace(u'%', u'%%')
								
								logger.info(u"Adding option '%s' with value '%s'" % (option, value))
								cp.set(section, option, value)
						
						iniFile.generate(cp)
				
				remainingObjs = unprocessedObjs
				unprocessedObjs = []
			
			iniFile.generate(cp)
	



