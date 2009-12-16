

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
from OPSI.Util.File import *
from OPSI.Util.File.Opsi import *
from Object import *
from Backend import *

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

# ======================================================================================================
# =                                   CLASS FILE31BACKEND                                              =
# ======================================================================================================
class File31Backend(ConfigDataBackend):
	
	def __init__(self, **kwargs):
		ConfigDataBackend.__init__(self, **kwargs)
		
		self.__baseDir = '/tmp/file31'
		self.__clientConfigDir = os.path.join(self.__baseDir, 'clients')
		self.__depotConfigDir  = os.path.join(self.__baseDir, 'depots')
		self.__productDir = os.path.join(self.__baseDir, 'products')
		self.__hostKeyFile = os.path.join(self.__baseDir, 'pckeys')
		self.__configFile = os.path.join(self.__baseDir, 'config.ini')
		
		#self._defaultDomain = u'uib.local'
		
		# Get hostid of localhost
		self.__serverId = socket.getfqdn()
		if (self.__serverId.count('.') < 2):
			raise Exception(u"Failed to get fqdn: %s" % self.__serverId)
		self.__serverId = self.__serverId.lower()
		
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
				{ 'fileType': 'ini', 'attribute': '*' }
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
				{ 'fileType': 'ini', 'attribute': 'productType',    'section': '<id>', 'option': 'producttype',    'json': False },
				{ 'fileType': 'ini', 'attribute': 'productVersion', 'section': '<id>', 'option': 'productversion', 'json': False },
				{ 'fileType': 'ini', 'attribute': 'packageVersion', 'section': '<id>', 'option': 'packageversion', 'json': False },
				{ 'fileType': 'ini', 'attribute': 'depotId',        'section': '<id>', 'option': 'depotid',        'json': False }
			],
			'ProductOnClient': [
				{ 'fileType': 'ini', 'attribute': '*' }
			],
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
					raise Exception(u"Can't handle configStates for ConfigServer")
				else: # should be client (# TODO: depot unhandled)
					return os.path.join(self.__clientConfigDir, ident['objectId'] + u'.ini')
			elif objType in ('ProductOnDepot'):
				return os.path.join(self.__depotConfigDir, ident['depotId'], u'depot.ini')
		
		elif (fileType == 'pro'):
			ver = u'_' + ident['productVersion'] + u'-' + ident['packageVersion']
			
			if objType == 'LocalbootProduct':
				return os.path.join(self.__productDir, ident['id'] + ver + u'.localboot')
			elif objType == 'NetbootProduct':
				return os.path.join(self.__productDir, ident['id'] + ver + u'.netboot')
			elif objType in ('Product', 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
				id = u''
				if objType == 'Product':
					id = ident['id']
				else:
					id = ident['productId']
				
				# instead of searching the whole dir, let's check the only possible files
				if os.path.isfile(os.path.join(self.__productDir, id + ver + u'.localboot')):
					return os.path.join(self.__productDir, id + ver + u'.localboot')
				elif os.path.isfile(os.path.join(self.__productDir, id + ver + u'.netboot')):
					return os.path.join(self.__productDir, id + ver + u'.netboot')
		
		logger.error(u"No config-file returned! objType: '%s' fileType: '%s' filter: '%s'" % (objType, fileType, filter))
		
		return
	
	def _getIdents(self, objType, **filter):
		objIdents = []
		
		if objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
			iniFile = IniFile(filename = self.__configFile)
			iniFile.create()
			cp = iniFile.parse()
			for section in cp.sections():
				objIdents.append({'id': section})
		
		elif objType in ('OpsiClient'):
			for entry in os.listdir(self.__clientConfigDir):
				if not entry.lower().endswith('.ini'):
					continue
				try:
					objIdents.append({'id': forceHostId(entry[:-4])})
				except:
					pass
		
		elif objType in ('OpsiDepotserver', 'OpsiConfigserver', 'ProductOnDepot'):
			for entry in os.listdir(self.__depotConfigDir):
				try:
					hostId = forceHostId(entry)
					if objType in ('OpsiConfigserver') and (hostId != self.__serverId):
						continue
					
					if objType == 'ProductOnDepot':
						iniFile = IniFile(filename = self._getConfigFile('OpsiDepotserver', {'id': hostId}, 'ini'))
						iniFile.create()
						cp = iniFile.parse()
						for section in cp.sections():
							if section.endswith('-state'):
								objIdents.append(
									{
									'productId': section[:-6],
									'productType': cp.get(section, 'producttype'),
									'productVersion': cp.get(section, 'productversion'),
									'packageVersion': cp.get(section, 'packageversion'),
									'depotId': cp.get(section, 'depotid')
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
				if not ( entry.endswith('.localboot') and objType !='NetbootProduct' ):
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
							objIdents.append(productDependency.toHash())
					else:
						for productProperty in packageControlFile.getProductProperties():
							objIdents.append(productProperty.toHash())
		
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
		
	def _objectHashMatches(self, objHash, **filter):
		matchedAll = True
		for (attribute, value) in objHash.items():
			if not filter.get(attribute):
				continue
			matched = False
			logger.comment(u"Testing match of filter '%s' of attribute '%s' with value '%s'" % \
				(filter[attribute], attribute, value))
			for filterValue in forceList(filter[attribute]):
				if (filterValue == value):
					matched = True
					break
				if type(value) is list:
					if filterValue in value:
						matched = True
						break
					continue
				if type(filterValue) in (types.NoneType, types.BooleanType): # TODO: int
					# TODO: still necessary?
					continue
				if re.search('^%s$' % filterValue.replace('*', '.*'), value):
					matched = True
					break
			if matched:
				logger.comment(u"Value '%s' matched filter '%s', attribute '%s'" % \
					(value, filter[attribute], attribute))
			else:
				matchedAll = False
				break
		return matchedAll
	
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
				
				if (fileType == 'key'):
					hostKeys = HostKeyFile(filename = filename)
					for m in mapping:
						objHash[m['attribute']] = hostKeys.getOpsiHostKey(ident['id'])
				
				elif (fileType == 'ini'):
					iniFile = IniFile(filename = filename)
					cp = iniFile.parse()
					
					for m in mapping:
						try:
							# TODO: think about placeholders <..>
							section = ''
							if objType in ('ProductOnDepot'):
								section = m['section'].replace('<id>', objHash.get('productId') + '-state')
							else:
								section = m['section'].replace('<id>', objHash.get('id'))
							value = cp.get(section, m['option'])
							if m.get('json'):
								value = fromJson(value)
							else:
								value = value.replace(u'\\n', u'\n')
							objHash[m['attribute']] = value
						except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
							logger.info(u"No option '%s' within section '%s' in '%s'" \
								% (m['option'], section, filename))
							objHash[m['attribute']] = None
				
				elif (fileType == 'pro'):
					packageControlFile = PackageControlFile(filename = filename)
					if   objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
						objHash = packageControlFile.getProduct().toHash()
					
					elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty'):
						# TODO: no boolproperty?
						for productProperty in packageControlFile.getProductProperties():
							tmpHash = productProperty.toHash()
							if self._objectHashMatches(tmpHash, **filter):
								objHash = tmpHash
					
					elif objType in ('ProductDependency'):
						for productDependency in packageControlFile.getProductDependencies():
							tmpHash = productDependency.toHash()
							if self._objectHashMatches(tmpHash, **filter):
								objHash = tmpHash
								print "matches"
			
			if self._objectHashMatches(objHash, **filter):
				Class = eval(objType)
				objHash = self._adaptObjectHashAttributes(objHash, ident, attributes)
				objects.append(Class.fromHash(objHash))
		return objects
	
	def _write(self, obj, mode='create'):
		objType = obj.getType()
		if (objType == 'OpsiConfigserver') and (self.__serverId != obj.getId()):
			raise Exception(u"File31 backend can only handle config server '%s'" % self.__serverId)
		
		if not self._mappings.has_key(objType):
			raise Exception(u"Mapping not found for object type '%s'" % objType)
		
		mappings = {}
		for mapping in self._mappings[objType]:
			if not mappings.has_key(mapping['fileType']):
				mappings[mapping['fileType']] = {}
			mappings[mapping['fileType']][mapping['attribute']] = mapping
		
		for (fileType, mapping) in mappings.items():
			filename = self._getConfigFile(obj.getType(), obj.getIdent(returnType = 'dict'), fileType)
			
			if not os.path.exists(os.path.dirname(filename)):
				logger.info(u"Creating path: '%s'" % os.path.dirname(filename))
				os.mkdir(os.path.dirname(filename))
			
			if (fileType == 'key'):
				hostKeys = HostKeyFile(filename = filename)
				hostKeys.create()
				hostKeys.setOpsiHostKey(obj.getId(), obj.getOpsiHostKey())
				hostKeys.generate()
			
			elif (fileType == 'ini'):
				iniFile = IniFile(filename = filename)
				if objType in ('OpsiClient', 'OpsiDepotserver', 'OpsiConfigserver') and (mode == 'create'):
					iniFile.delete()
					iniFile.create()
				
				cp = iniFile.parse()
				
				if objType in ('Config', 'UnicodeConfig', 'BoolConfig') and (mode == 'create'):
					if cp.has_section(obj.getId()):
						cp.remove_section(obj.getId())
				
				if objType in ('ProductOnDepot') and (mode == 'create'):
					if cp.has_section(obj.getProductId() + u'-state'):
						cp.remove_section(obj.getProductId() + u'-state')
				
				for (attribute, value) in obj.toHash().items():
					if value is None:
						continue
					
					if mapping.has_key(attribute):
						section = mapping[attribute]['section']
						if mapping[attribute].get('json'):
							value = toJson(value)
						elif ( isinstance(value, str) or isinstance(value, unicode) ):
							value = value.replace(u'\n', u'\\n').replace(u'%', u'')
						# TODO: think about placeholders <..>
						if ( section == '<id>'):
							if objType in ('ProductOnDepot'):
								section = obj.getProductId() + u'-state'
							else:
								section = obj.getId()
						
						if not cp.has_section(section):
							cp.add_section(section)
							print "added", section
						
						print "set: ", mapping[attribute]['option'], "with", value
						cp.set(section, mapping[attribute]['option'], forceUnicode(value))
						print "done"
				
				iniFile.generate(cp)
			
			elif (fileType == 'pro'):
				packageControlFile = PackageControlFile(filename = filename)
				
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
					for item in oldList:
						print "item in oldList:"
						print item
						print
						if item.getIdent() == obj.getIdent():
							objInOldList = True
							if mode == 'create':
								newList.append(obj)
							else:
								itemHash = item.toHash()
								newHash = {}
								for (attribute, value) in obj.toHash().items():
									if value is None:
										print "value is NONE, setting old value", value, "/", attribute
										newHash[attribute] = itemHash[attribute]
									else:
										print "value is NOT NONE, setting new value", value, "/", attribute
										newHash[attribute] = value
								newList.append(Object.fromHash(newHash))
						else:
							newList.append(item)
					
					if not objInOldList:
						newList.append(obj)
					
					if objType == 'ProductDependency':
						packageControlFile.setProductDependencies(newList)
################
						print "before generate"
						for p in packageControlFile.getProductDependencies():
							print p
################
					else:
						packageControlFile.setProductProperties(newList)
				
				packageControlFile.generate()
################
				if objType == 'ProductDependency':
					for p in packageControlFile.getProductDependencies():
						print "---", p
					print "after generate"
					pack = PackageControlFile(filename = filename)
					for p in pack.getProductDependencies():
						print p
################
	
	def _delete(self, objList):
		objType = u''
		if objList:
			objType = objList[0].getType()
		
		if objType in ('OpsiClient', 'OpsiConfigserver', 'OpsiDepotserver'):
			hostKeys = HostKeyFile(self._getConfigFile('', '', 'key'))
			for host in objList:
				logger.info(u"Deleting host: '%s'" % host.getId())
				hostKeys.deleteOpsiHostKey(host.getId())
				if host.getType() in ('OpsiConfigserver', 'OpsiDepotserver'):
					configDir = os.path.join(self.__depotConfigDir, host.getId())
					if os.path.isdir(configDir):
						shutil.rmtree(configDir)
				elif host.getType() in ('OpsiClient'):
					configFile = self._getConfigFile(host.getType(), {'id': host.getId()}, 'ini')
					if os.path.isfile(configFile):
						os.unlink(configFile)
			hostKeys.generate()
		
		elif objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
			iniFile = IniFile(filename = self._getConfigFile('Config', [], 'ini'))
			iniFile.create()
			cp = iniFile.parse()
			for config in objList:
				logger.info(u"Deleting config: '%s'" % config.getId())
				if cp.has_section(config.getId()):
					cp.remove_section(config.getId())
				else:
					logger.warning(u"Cannot delete non existant section '%s'" % config.getId())
			iniFile.generate(cp)
		
		elif objType in ('ConfigState'):
			for configState in objList:
				logger.info(u"Deleting configState in host: '%s'" % configState.getIdent())
				iniFile = IniFile(filename = self._getConfigFile(
					'ConfigState',
					configState.getIdent(returnType = 'dict'),
					'ini')
				)
				cp = iniFile.parse()
				if cp.has_section(configState.getConfigId()):
					cp.remove_section(configState.getConfigId())
				iniFile.generate(cp)
		
		elif objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
			for product in objList:
				fileType = ''
				logger.info(u"Deleting product: '%s'" % product.getId())
				configFile = self._getConfigFile( product.getType(), product.getIdent(), 'pro' )
				if os.path.isfile(configFile):
					os.unlink(configFile)
		
		elif objType in ('ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
			filenames = []
			
			# TODO: files werden nur einmal eingelesen, aber umstaendlich. wird's getestet?
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
					print "listing productdependencies"
					oldList = packageControlFile.getProductDependencies()
				else:
					print "listing productproperties"
					oldList = packageControlFile.getProductProperties()
				
				print "searching..."
				
				for oldItem in oldList:
					for item in objList:
						print "actual", oldItem
						print "to delete", item
						if oldItem.getIdent() == item.getIdent():
							logger.info(u"Deleting %s: '%s'" \
								% (objType, oldItem.getIdent()))
							continue
						newList.append(item)
				
				if objType == 'ProductDependency':
					packageControlFile.setProductDependencies(newList)
				else:
					packageControlFile.setProductProperties(newList)
				
				packageControlFile.generate()
		
		elif objType in ('ProductOnDepot'):
			for productOnDepot in objList:
				logger.info(u"Deleting productOnDepot: '%s'" % productOnDepot.getIdent())
				# TODO: delete
		
		elif objType in ('ProductOnClient'):
			for productOnDepot in objList:
				logger.info(u"Deleting productOnDepot: '%s'" % productOnDepot.getIdent())
				# TODO: delete
		
		else:
			print "unhandled objType: '%s'" % objType
		
	
	def base_create(self):
		os.mkdir(self.__baseDir)
		os.mkdir(self.__clientConfigDir)
		os.mkdir(self.__depotConfigDir)
		os.mkdir(self.__productDir)
	
	def base_delete(self):
		if os.path.exists(self.__baseDir):
			shutil.rmtree(self.__baseDir)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		ConfigDataBackend.host_insertObject(self, host)
		
		host = forceObjectClass(host, Host)
		
		logger.notice(u"Inserting host: '%s'" % host.getId())
		self._write(host, mode = 'create')
		logger.notice(u"Inserted host: '%s'" % host.getId())
	
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		host = forceObjectClass(host, Host)
		
		logger.notice(u"Updating host: '%s'" % host.getId())
		self._write(host, mode = 'update')
		logger.notice(u"Updated host: '%s'" % host.getId())
	
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
		
		hosts = forceObjectClassList(hosts, Host)
		
		logger.notice(u"Deleting hosts ...")
		self._delete(hosts)
		logger.notice(u"Deleted hosts.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		
		config = forceObjectClass(config, Config)
		
		logger.notice(u"Inserting config: '%s'" % config.getId())
		self._write(config, mode = 'create')
		logger.notice(u"Inserted config: '%s'" % config.getId())
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
		config = forceObjectClass(config, Config)
		
		logger.notice(u"Updating config: '%s'" % config.getId())
		self._write(config, mode = 'update')
		logger.notice(u"Updated config: '%s'" % config.getId())
	
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting configs ...")
		result = self._read('Config', attributes, **filter)
		logger.notice(u"Returning configs.")
		
		return result
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		
		configs = forceObjectClassList(configs, Config)
		
		logger.notice(u"Deleting configs ...")
		self._delete(configs)
		logger.notice(u"Deleted configs.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
		
		configState = forceObjectClass(configState, ConfigState)
		
		logger.notice(u"Inserting configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'create')
		logger.notice(u"Inserted configState: '%s'" % configState.getIdent())
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
		
		configState = forceObjectClass(configState, ConfigState)
		
		logger.notice(u"Updating configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'update')
		logger.notice(u"Updated configState: '%s'" % configState.getIdent())
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting configStates ...")
		result = self._read('ConfigState', attributes, **filter)
		logger.notice(u"Returning configStates.")
		
		return result
	
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
		
		configStates = forceObjectClassList(configStates, ConfigState)
		logger.notice(u"Deleting configStates ...")
		self._delete(configStates)
		logger.notice(u"Deleted configStates.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		
		product = forceObjectClass(product, Product)
		
		logger.notice(u"Inserting product: '%s'" % product.getId())
		self._write(product, mode = 'create')
		logger.notice(u"Inserted product.")
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		
		product = forceObjectClass(product, Product)
		
		logger.notice(u"Updating product: '%s'" % product.getId())
		self._write(product, mode = 'update')
		logger.notice(u"Updated product: '%s'" % product.getId())
	
	def product_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.product_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting products ...")
		result = self._read('LocalbootProduct', attributes, **filter)
		result.extend(self._read('NetbootProduct', attributes, **filter))
		logger.notice(u"Got products.")
		
		return result
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
		
		products = forceObjectClassList(products, Product)
		
		logger.notice(u"Deleting products ...")
		self._delete(products)
		logger.notice(u"Deleted products.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		
		productProperty = forceObjectClass(productProperty, ProductProperty)
		
		logger.notice(u"Inserting productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'create')
		logger.notice(u"Inserted productProperty.")
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		
		productProperty = forceObjectClass(productProperty, ProductProperty)
		
		logger.notice(u"Updating productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'update')
		logger.notice(u"Updated productProperty: '%s'" % productProperty.getIdent())
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes, **filter)
		
		logger.notice(u"Getting productProperties ...")
		result = self._read('ProductProperty', attributes, **filter)
		logger.notice(u"Got productProperties.")
		
		return result
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		
		productProperties = forceObjectClassList(productProperties, ProductProperty)
		
		logger.notice(u"Deleting productProperties ...")
		self._delete(productProperties)
		logger.notice(u"Deleted productProperties.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		
		productDependency = forceObjectClass(productDependency, ProductDependency)
		
		logger.notice(u"Inserting productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'create')
		logger.notice(u"Inserted productDependency.")
	
	def productDependency_updateObject(self, productDependency):
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		
		productDependency = forceObjectClass(productDependency, ProductDependency)
		
		logger.notice(u"Updating productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'update')
		logger.notice(u"Updated productDependency: '%s'" % productDependency.getIdent())
	
	def productDependency_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productDependencies ...")
		result = self._read('ProductDependency', attributes, **filter)
		logger.notice(u"Got productDependencies.")
		
		return result
	
	def productDependency_deleteObjects(self, productDependencies):
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		
		productDependencies = forceObjectClassList(productDependencies, ProductDependency)
		
		logger.notice(u"Deleting productDependencies ...")
		self._delete(productDependencies)
		logger.notice(u"Deleted productDependencies.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		
		logger.notice(u"Inserting productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'create')
		logger.notice(u"Inserted productOnDepot.")
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
		
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		
		logger.notice(u"Updating productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'update')
		logger.notice(u"Updated productOnDepot: '%s'" % productOnDepot.getIdent())
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productOnDepots ...")
		result = self._read('ProductOnDepot', attributes, **filter)
		logger.notice(u"Got productOnDepots.")
		
		return result
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
		productOnDepots = forceObjectClassList(productOnDepots, ProductOnDepot)
		
		logger.notice(u"Deleting productOnDepots ...")
		self._delete(productOnDepots)
		logger.notice(u"Deleted productOnDepots.")
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		
		logger.notice(u"Inserting productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'create')
		logger.notice(u"Inserted productOnClient.")
	
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		
		logger.notice(u"Updating productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'update')
		logger.notice(u"Updated productOnClient: '%s'" % productOnClient.getIdent())
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		
		logger.notice(u"Getting productOnClient ...")
		result = self._read('ProductOnClient', attributes, **filter)
		logger.notice(u"Got productOnClient.")
		
		return result
	
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		
		productOnClients = forceObjectClassList(productOnClients, ProductOnClient)
		
		logger.notice(u"Deleting productOnClients ...")
		self._delete(productOnClients)
		logger.notice(u"Deleted productOnClients.")
	


