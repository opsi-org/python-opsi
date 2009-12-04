

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
			'Config': [                                                               # TODO: placeholders
				{ 'fileType': 'ini', 'attribute': 'type'                  , 'section': '<id>', 'option': 'type',           'json': False     },
				{ 'fileType': 'ini', 'attribute': 'description'           , 'section': '<id>', 'option': 'description', 'json': False         },
				{ 'fileType': 'ini', 'attribute': 'editable'              , 'section': '<id>', 'option': 'editable' , 'json': False           },
				{ 'fileType': 'ini', 'attribute': 'multiValue'            , 'section': '<id>', 'option': 'multivalue' , 'json': False         },
				{ 'fileType': 'ini', 'attribute': 'possibleValues'        , 'section': '<id>', 'option': 'possiblevalues', 'json': True      },
				{ 'fileType': 'ini', 'attribute': 'defaultValues'         , 'section': '<id>', 'option': 'defaultvalues' , 'json': True      },
			],
			'OpsiClient': [
				{ 'fileType': 'key', 'attribute': 'opsiHostKey' },
				{ 'fileType': 'ini', 'attribute': 'description',     'section': 'info', 'option': 'description'     },
				{ 'fileType': 'ini', 'attribute': 'notes',           'section': 'info', 'option': 'notes'           },
				{ 'fileType': 'ini', 'attribute': 'hardwareAddress', 'section': 'info', 'option': 'hardwareaddress' },
				{ 'fileType': 'ini', 'attribute': 'ipAddress',       'section': 'info', 'option': 'ipaddress'       },
				{ 'fileType': 'ini', 'attribute': 'inventoryNumber', 'section': 'info', 'option': 'inventorynumber' },
				{ 'fileType': 'ini', 'attribute': 'created',         'section': 'info', 'option': 'created'         },
				{ 'fileType': 'ini', 'attribute': 'lastSeen',        'section': 'info', 'option': 'lastseen'        },
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
			'LocalbootProduct': [
				{ 'fileType': 'lbp', 'attribute': '*', 'object': 'product' },
			],
			'NetbootProduct': [
				{ 'fileType': 'nbp', 'attribute': '*', 'object': 'product' },
			]
		}
		self._mappings['UnicodeConfig'] = self._mappings['Config']
		self._mappings['BoolConfig'] = self._mappings['Config']
		self._mappings['OpsiConfigserver'] = self._mappings['OpsiDepotserver']

	
	def _getConfigFile(self, objType, ident, fileType):
		if objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
			if (fileType == 'ini'):
				return self.__configFile
		elif objType in ('OpsiClient'):
			if (fileType == 'ini'):
				return os.path.join(self.__clientConfigDir, ident['id'] + u'.ini')
			if (fileType == 'key'):
				return os.path.join(self.__hostKeyFile)
		elif objType in ('OpsiDepotserver', 'OpsiConfigserver'):
			if (fileType == 'ini'):
				return os.path.join(self.__depotConfigDir, ident['id'], u'depot.ini')
			if (fileType == 'key'):
				return os.path.join(self.__hostKeyFile)
		elif objType in ('LocalbootProduct', 'NetbootProduct'):
			if (fileType == 'lbp'):
				return os.path.join(
					self.__productDir,
					ident['id'] + u'_' +
					ident['productVersion'] + u'-' +
					ident['packageVersion'] + u'.localboot'
				)
			if (fileType == 'nbp'):
				return os.path.join(
					self.__productDir,
					ident['id'] + u'_' +
					ident['productVersion'] + u'-' +
					ident['packageVersion'] + u'.netboot'
				)
	
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
		
		elif objType in ('OpsiDepotserver', 'OpsiConfigserver'):
			for entry in os.listdir(self.__depotConfigDir):
				try:
					hostId = forceHostId(entry)
					if objType in ('OpsiConfigserver') and (hostId != self.__serverId):
						continue
					objIdents.append({'id': hostId})
				except:
					pass
		
		elif objType in ('LocalbootProduct', 'NetbootProduct'):
			for entry in os.listdir(self.__productDir):
				if not entry.lower().endswith('.localboot'):
					if not entry.lower().endswith('.netboot'):
						continue
				
				#example:            exampleexampleexa  _ 123.123 - 123.123  .localboot
				match = re.search('^([a-zA-Z0-9\_\.-]+)\_([\w\.]+)-([\w\.]+)\.(local|net)boot$', )
				if not match:
					continue
				
				logger.debug2(u"Found match: id='%s', productVersion='%s', packageVersion='%s'" \
					% (match.group(1), match.group(2), match.group(3)) )
				objIdents.append({'id': match.group(1), 'productVersion': match.group(2), 'packageVersion': match.group(3)})
		
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
			for filterValue in forceList(filter[attribute]):
				logger.debug2(u"Testing match of filter value '%s' of attribute '%s' with value '%s'" % \
					(filterValue, attribute, value))
				if type(filterValue) is bool:
					try:
						value = forceBool(value)
					except:
						continue
				if (filterValue == value):
					matched = True
					break
				if type(filterValue) is list: # TODO: int
					if not type(value) is list:
						continue
					if len(filterValue) != len(value):
						continue
					allElementsMatched = True
					for v in value:
						if not v in filterValue:
							allElementsMatched = False
							break
					matched = allElementsMatched
					if matched:
						break
					continue
				if type(value) is list:
					if filterValue in value:
						matched = True
						break
					continue
				if type(filterValue) in (types.NoneType, types.BooleanType): # TODO: int
					continue
				if re.search('^%s$' % filterValue.replace('*', '.*'), value):
					matched = True
					break
			if matched:
				logger.debug(u"Value '%s' matched filter '%s', attribute '%s'" % \
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
		
		mappings = {}
		for mapping in self._mappings[objType]:
			if (not attributes or mapping['attribute'] in attributes) or mapping['attribute'] in filter.keys():
				if not mappings.has_key(mapping['fileType']):
					mappings[mapping['fileType']] = []
				
				mappings[mapping['fileType']].append(mapping)
		
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
				
				elif (fileType == 'lbp' or fileType == 'nbp'):
					packageControlFile = PackageControlFile(filename = filename)
					if (mapping['*']['object'] == 'product'):
						objHash = packageControlFile.getProduct().toHash()
			
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
				if (mode == 'create'):
					if not objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
						iniFile.delete()
				iniFile.create()
				cp = iniFile.parse()
				if objType in ('Config', 'UnicodeConfig', 'BoolConfig') and (mode == 'create'):
					if cp.has_section(obj.getId()):
						cp.remove_section(obj.getId())
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
							section = obj.getId()
						
						if ( not cp.has_section(section) ):
							cp.add_section(section)
						
						cp.set(section, mapping[attribute]['option'], forceUnicode(value))
				iniFile.generate(cp)
			
			elif (fileType == 'lbp' or fileType == 'nbp'):
				packageControlFile = PackageControlFile(filename = filename)
				if (mapping['*']['object'] == 'product'):
					if (mode == 'create'):
						packageControlFile.setProduct(obj)
					else:
						productHash = packageControlFile.getProduct().toHash()
						for (attribute, value) in obj.toHash().items():
							if value is None:
								continue
							productHash[attribute] = value
						packageControlFile.setProduct(Product.fromHash(productHash))
					packageControlFile.generate()
	
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
		self._write(host, mode = 'create')
	
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		host = forceObjectClass(host, Host)
		logger.info(u'Updating Host: %s' % host.getId())
		self._write(host, mode = 'update')
	
	def host_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.host_getObjects(self, attributes, **filter)
		
		result = self._read('OpsiDepotserver', attributes, **filter)
		opsiConfigServers = self._read('OpsiConfigserver', attributes, **filter)
		
		if opsiConfigServers:
			for i in range(len(result)):
				if (result[i].getId() == opsiConfigServers[0].getId()):
					result[i] = opsiConfigServers[0]
					break
		
		result.extend(self._read('OpsiClient', attributes, **filter))
		return result
	
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		for host in forceObjectClassList(hosts, Host):
			hostKeys = HostKeyFile(self._getConfigFile(host.getType(), {'id': host.getId()}, 'key'))
			hostKeys.deleteOpsiHostKey(host.getId())
			hostKeys.generate()
			
			if host.getType() in ('OpsiConfigserver', 'OpsiDepotserver'):
				configDir = os.path.join(self.__depotConfigDir, host.getId())
				if os.path.exists(configDir):
					shutil.rmtree(configDir)
			elif host.getType() in ('OpsiClient'):
				configFile = self._getConfigFile(host.getType(), {'id': host.getId()}, 'ini')
				if os.path.exists(configFile):
					os.unlink(configFile)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		
		print "--------------------------------------------------------- config_insertObject", config.toHash()
		
		config = forceObjectClass(config, Config)
		logger.info(u'Creating config: %s' % config.getId())
		self._write(config, mode = 'create')
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
		print "--------------------------------------------------------- config_updateObject"
		
		config = forceObjectClass(config, Config)
		logger.info(u'Updating config: %s' % config.getId())
		self._write(config, mode = 'update')
	
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes, **filter)
		
		print "--------------------------------------------------------- config_getObjects"
		
		result = self._read('Config', attributes, **filter)
		
		print "#########################################################attrib", attributes
		print "#########################################################filter", filter
		
		for config in result:
			print "###", config
		
		return result
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		
		print "--------------------------------------------------------- config_deleteObjects"
		
		
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		
		product = forceObjectClass(product, Product)
		self._write(product, mode = 'create')
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		
		product = forceObjectClass(product, Product)
		logger.info(u'Updating Product: %s' % product.getId())
		self._write(product, mode = 'update')
	
	def product_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.product_getObjects(self, attributes = [], **filter)
		
		result = self._read('Product', attributes, **filter)
		return result
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
		
		for product in forceObjectClassList(products, Product):
			if product.getType() in ('LocalbootProduct', 'NetbootProduct'):
				configFile = self._getConfigFile(
					product.getType(),
					{
						'id': product.getId(),
						'productVersion': product.getProductVersion(),
						'packageVersion': product.getPackageVersion()
					},
					'ini'
				)
				if os.path.exists(configFile):
					os.unlink(configFile)
	
	
	
	
	
	
	
	
	
	
	



