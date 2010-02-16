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
   @author: Arne Kerz <a.kerz@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.5'

import os, socket, ConfigParser, shutil, types

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Util import toJson, fromJson
from OPSI.Util.File import *
from OPSI.Util.File.Opsi import *
from OPSI.Object import *
from OPSI.Backend.Backend import *

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
		
		self.__fileUser  = u'opsiconfd'
		self.__fileGroup = u'opsiadmin'
		self.__fileMode  = 0660
		self.__dirUser   = u'opsiconfd'
		self.__dirGroup  = u'opsiadmin'
		self.__dirMode   = 0770
		
		# Parse arguments
		for (option, value) in kwargs.items():
			option = option.lower()
			if   option in ('basedir'):
				self.__baseDir = forceFilename(value)
			elif option in ('hostkeyfile'):
				self.__hostKeyFile = forceFilename(value)
		
		self.__fileUid = pwd.getpwnam(self.__fileUser)[2]
		self.__fileGid = grp.getgrnam(self.__fileGroup)[2]
		self.__dirUid  = pwd.getpwnam(self.__dirUser)[2]
		self.__dirGid  = grp.getgrnam(self.__dirGroup)[2]
		
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
			]#,
#			'AuditSoftware': [
#				{ 'fileType': 'sw', 'attribute': 'windowsSoftwareId',     'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'windowssoftwareid'     },
#				{ 'fileType': 'sw', 'attribute': 'windowsDisplayName',    'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'windowsdisplayname'    },
#				{ 'fileType': 'sw', 'attribute': 'windowsDisplayVersion', 'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'windowsdisplayversion' },
#				{ 'fileType': 'sw', 'attribute': 'installSize',           'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'installsize'           }
#			],
#			'AuditSoftwareOnClient': [
#				{ 'fileType': 'sw', 'attribute': 'uninstallString', 'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'uninstallstring' },
#				{ 'fileType': 'sw', 'attribute': 'binaryName',      'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'binaryname'      },
#				{ 'fileType': 'sw', 'attribute': 'firstseen',       'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'firstseen'       },
#				{ 'fileType': 'sw', 'attribute': 'lastseen',        'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'lastseen'        },
#				{ 'fileType': 'sw', 'attribute': 'state',           'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'state'           },
#				{ 'fileType': 'sw', 'attribute': 'usageFrequency',  'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'usagefrequency'  },
#				{ 'fileType': 'sw', 'attribute': 'lastUsed',        'section': '<name>;<version>;<subVersion>;<language>;<architecture>', 'option': 'lastused'        }
#			],
#			'AuditHardware': [
#				{ 'fileType': 'hw', 'attribute': '*' }
#			],
#			'AuditHardwareOnHost': [
#				{ 'fileType': 'hw', 'attribute': '*' }
#			]
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
		for dirname in (self.__baseDir, self.__clientConfigDir, self.__depotConfigDir, self.__productDir, self.__auditDir, self.__clientTemplateDir):
			if not os.path.isdir(dirname):
				self._mkdir(dirname)
			self._setRights(dirname)
		
		defaultTemplate = os.path.join(self.__clientTemplateDir, self.__defaultClientTemplateName + '.ini')
		for filename in (defaultTemplate, self.__configFile, self.__hostKeyFile, self.__clientGroupsFile):
			if not os.path.isfile(filename):
				self._touch(filename)
			self._setRights(filename)
		
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
	
	def _setRights(self, path):
		if os.path.isfile(path):
			logger.debug(u"Setting rights on file '%s'" % path)
			os.chmod(path, self.__fileMode)
			if (os.geteuid() == 0):
				os.chown(path, self.__fileUid, self.__fileGid)
			else:
				os.chown(path, -1, self.__fileGid)
		elif os.path.isdir(path):
			logger.debug(u"Setting rights on dir '%s'" % path)
			os.chmod(path, self.__dirMode)
			if (os.geteuid() == 0):
				os.chown(path, self.__dirUid, self.__dirGid)
			else:
				os.chown(path, -1, self.__dirGid)
		
	def _mkdir(self, dirname):
		logger.info(u"Creating path: '%s'" % dirname)
		os.mkdir(dirname)
		self._setRights(dirname)
		
	def _touch(self, filename):
		if not os.path.exists(filename):
			logger.info(u"Creating file: '%s'" % filename)
			f = open(filename, 'w')
			f.close()
		self._setRights(filename)
		
	def __escape(self, string):
		string = forceUnicode(string)
		string = string.replace(u'\n', u'\\n').replace(u';', u'\\;').replace(u'#', u'\\#').replace(u'%', u'%%')
		return string
	
	def __unescape(self, string):
		string = forceUnicode(string)
		string = string.replace(u'\\n', u'\n').replace(u'\\;', u';').replace(u'\\#', u'#').replace(u'%%', u'%')
		return string
	
	def _getConfigFile(self, objType, ident, fileType):
		filename = None
		
		if (fileType == 'key'):
			filename = self.__hostKeyFile
		
		elif (fileType == 'ini'):
			if objType in ('Config', 'UnicodeConfig', 'BoolConfig'):
				filename = self.__configFile
			elif objType in ('OpsiClient'):
				filename = os.path.join(self.__clientConfigDir, ident['id'] + u'.ini')
			elif objType in ('OpsiDepotserver', 'OpsiConfigserver'):
				filename = os.path.join(self.__depotConfigDir, ident['id'] + u'.ini')
			elif objType in ('ConfigState'):
				if os.path.isfile(os.path.join(os.path.join(self.__depotConfigDir, ident['objectId'] + u'.ini'))):
					filename = os.path.join(self.__depotConfigDir, ident['objectId'] + u'.ini')
				else:
					filename = os.path.join(self.__clientConfigDir, ident['objectId'] + u'.ini')
			elif objType in ('ProductOnDepot'):
				filename = os.path.join(self.__depotConfigDir, ident['depotId'] + u'.ini')
			elif objType in ('ProductOnClient'):
				filename = os.path.join(self.__clientConfigDir, ident['clientId'] + u'.ini')
			elif objType in ('ProductPropertyState'):
				if os.path.isfile(os.path.join(os.path.join(self.__depotConfigDir, ident['objectId'] + u'.ini'))):
					filename = os.path.join(self.__depotConfigDir, ident['objectId'] + u'.ini')
				else:
					filename = os.path.join(self.__clientConfigDir, ident['objectId'] + u'.ini')
			elif objType in ('Group', 'HostGroup', 'ObjectToGroup'):
				filename = os.path.join(self.__clientGroupsFile)
		
		elif (fileType == 'pro'):
			pVer = u'_' + ident['productVersion'] + u'-' + ident['packageVersion']
			
			if objType == 'LocalbootProduct':
				filename = os.path.join(self.__productDir, ident['id'] + pVer + u'.localboot')
			elif objType == 'NetbootProduct':
				filename = os.path.join(self.__productDir, ident['id'] + pVer + u'.netboot')
			elif objType in ('Product', 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
				pId = u''
				if objType == 'Product':
					pId = ident['id']
				else:
					pId = ident['productId']
				
				# instead of searching the whole dir, let's check the only possible files
				if os.path.isfile(os.path.join(self.__productDir, pId + pVer + u'.localboot')):
					filename = os.path.join(self.__productDir, pId + pVer + u'.localboot')
				elif os.path.isfile(os.path.join(self.__productDir, pId + pVer + u'.netboot')):
					filename = os.path.join(self.__productDir, pId + pVer + u'.netboot')
		
		elif (fileType == 'sw'):
			if objType == 'AuditSoftware':
				filename = os.path.join(self.__auditDir, u'global.sw')
			elif objType == 'AuditSoftwareOnClient':
				filename = os.path.join(self.__auditDir, ident['clientId'] + u'.sw')
		
		elif (fileType == 'hw'):
			if objType == 'AuditHardware':
				filename = os.path.join(self.__auditDir, u'global.hw')
			elif objType == 'AuditHardwareOnHost':
				filename = os.path.join(self.__auditDir, ident['hostId'] + u'.hw')
		
		if filename is None:
			raise Exception(u"No config-file returned! objType '%s', ident '%s', fileType '%s'" % (objType, ident, fileType))
		
		if objType in ('ConfigState', 'ProductOnDepot', 'ProductOnClient', 'ProductPropertyState'):
			if os.path.isfile(filename):
				return filename
			else:
				raise Exception(u"%s needs existing file! ident '%s', fileType '%s'" % (objType, ident, fileType))
		else:
			return filename
	
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
			try:
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
										'productId':   section[:-6],
										'productType': cp.get(section, 'productType'),
										'clientId':    hostId
										}
									)
						else:
							objIdents.append({'id': hostId})
					except:
						pass
			except Exception, e:
				raise BackendIOError(u"Failed to list dir '%s': %s" % (self.__clientConfigDir, e))
		
		elif objType in ('OpsiDepotserver', 'OpsiConfigserver', 'ProductOnDepot'):
			try:
				for entry in os.listdir(self.__depotConfigDir):
					try:
						hostId = forceHostId(entry[:-4])
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
										'productId':      section[:-6],
										'productType':    cp.get(section, 'producttype'),
										'productVersion': cp.get(section, 'productversion'),
										'packageVersion': cp.get(section, 'packageversion'),
										'depotId':        hostId
										}
									)
						else:
							objIdents.append({'id': hostId})
					except:
						pass
			except Exception, e:
				raise BackendIOError(u"Failed to list dir '%s': %s" % (self.__depotConfigDir, e))
		
		elif objType in ('Product', 'LocalbootProduct', 'NetbootProduct', 'ProductProperty', 'UnicodeProductProperty', 'BoolProductProperty', 'ProductDependency'):
			try:
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
			except Exception, e:
				raise BackendIOError(u"Failed to list dir '%s': %s" % (self.__productDir, e))
		
		elif objType in ('ConfigState', 'ProductPropertyState'):
			objectIds = []
			
			entries = os.listdir(self.__depotConfigDir)
			entries.extend(os.listdir(self.__clientConfigDir))
			
			for entry in entries:
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
								'productId':  section[:-8],
								'propertyId': option,
								'objectId':   objectId
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
										'groupId':  section,
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
		
		elif objType in ('AuditSoftware', 'AuditSoftwareOnClient', 'AuditHardware', 'AuditHardwareOnHost'):
			filenames = []
			
			fileType = 'sw'
			if objType in ('AuditHardware', 'AuditHardwareOnHost'):
				fileType = 'hw'
			
			if objType in ('AuditSoftware', 'AuditHardware'):
				filename = self._getConfigFile(objType, {}, fileType)
				if os.path.isfile(filename):
					filenames.append(filename)
			else:
				for entry in os.listdir(self.__auditDir):
					entry = entry.lower()
					filename = ''
					
					if (entry == 'global.sw') or (entry == 'global.hw'):
						continue
					elif not entry.endswith('.%s' % fileType):
						continue
					try:
						forceHostId(entry[:-3])
					except:
						logger.error(u"_getIdents(): Found bad file '%s'" % entry)
						continue
					filenames.append(os.path.join(self.__auditDir, entry))
					
			for filename in filenames:
				iniFile = IniFile(filename = filename)
				cp = iniFile.parse()
				
				filebase = os.path.basename(filename)[:-3]
				
				for section in cp.sections():
					objIdent = {}
					
					if objType in ('AuditSoftware', 'AuditSoftwareOnClient'):
						objIdent = {
							'name' :        None,
							'version' :     None,
							'subVersion' :  None,
							'language' :    None,
							'architecture': None
							}
						for key in objIdent.keys():
							try:
								objIdent[str(key)] = self.__unescape(cp.get(section, key.lower()))
							except:
								pass
						if (objType == 'AuditSoftwareOnClient'):
							objIdent['clientId'] = forceHostId(filebase)
					else:
						for (key, value) in cp.items(section):
							objIdent[str(key)] = self.__unescape(value)
						
						if (objType == 'AuditHardwareOnHost'):
							objIdent['hostId'] = forceHostId(filebase)
					
					objIdents.append(objIdent)
		
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
			
		logger.debug2(u"Filter: %s" % filter)
		logger.debug2(u"Attributes: %s" % attributes)
		
		mappings = {}
		for mapping in self._mappings[objType]:
			if (not attributes or mapping['attribute'] in attributes) or mapping['attribute'] in filter.keys():
				if not mappings.has_key(mapping['fileType']):
					mappings[mapping['fileType']] = []
				
				mappings[mapping['fileType']].append(mapping)
		
		logger.debug2(u"Using mappings %s" % mappings)
		
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
				
				elif (fileType == 'ini'):
					iniFile = IniFile(filename = filename, ignoreCase = False)
					cp = iniFile.parse()
					
					for m in mapping:
						attribute = m['attribute']
						section = m['section']
						option = m['option']
						
						match = self._placeholderRegex.search(section)
						if match:
							replaceValue = objHash[match.group(1)]
							if objType == 'ProductOnClient':
								replaceValue.replace('LocalbootProduct', 'localboot').replace('NetbootProduct', 'netboot')
							section = section.replace(u'<%s>' % match.group(1), replaceValue)
						
						match = self._placeholderRegex.search(option)
						if match:
							option = option.replace(u'<%s>' % match.group(1), objHash[match.group(1)])
						
						if cp.has_option(section, option):
							value = cp.get(section, option)
							if m.get('json'):
								value = fromJson(value)
							elif ( isinstance(value, str) or isinstance(value, unicode) ):
								value = self.__unescape(value)
							
							# TODO: what to return, if more than one ':'?
							if objType in ('ProductOnClient') and value.find(':') != -1:
								if attribute == 'installationStatus':
									value = value.split(u':', 1)[0]
								elif attribute == 'actionRequest':
									value = value.split(u':', 1)[1]
							
							objHash[attribute] = value
					logger.debug2(u"Got object hash from ini file: %s" % objHash)
					
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
			
			Class = eval(objType)
			if self._objectHashMatches(Class.fromHash(objHash).toHash(), **filter):
				objHash = self._adaptObjectHashAttributes(objHash, ident, attributes)
				objects.append(Class.fromHash(objHash))
		
		for obj in objects:
			logger.debug2(u"Returning object: %s" % obj.getIdent())
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
			
			if (fileType == 'key'):
				if (mode == 'create') or (mode == 'update' and obj.getOpsiHostKey()):
					if not os.path.exists(filename):
						self._touch(filename)
					hostKeys = HostKeyFile(filename = filename)
					hostKeys.setOpsiHostKey(obj.getId(), obj.getOpsiHostKey())
					hostKeys.generate()
			
			elif (fileType == 'ini'):
				iniFile = IniFile(filename = filename, ignoreCase = False)
				if not os.path.exists(filename):
					self._touch(filename)
				cp = iniFile.parse()
				
				if (mode == 'create'):
					if objType in ('OpsiClient', 'OpsiDepotserver', 'OpsiConfigserver'):
						iniFile.delete()
						
						if objType in ('OpsiClient'):
							shutil.copyfile(os.path.join(self.__clientTemplateDir, self.__defaultClientTemplateName + '.ini'), filename)
						
						self._touch(filename)
						iniFile = IniFile(filename = filename, ignoreCase = False)
						cp = iniFile.parse()
					else:
						newSection = ''
						
						if   objType in ('Config', 'UnicodeConfig', 'BoolConfig', 'Group', 'HostGroup'):
							newSection = obj.getId()
						elif objType in ('ProductOnDepot', 'ProductOnClient'):
							newSection = obj.getProductId() + u'-state'
						elif objType in ('ProductPropertyState'):
							newSection = obj.getPropertyId() + u'-install'
						
						if newSection != '' and cp.has_section(newSection):
							cp.remove_section(newSection)
				
				objHash = obj.toHash()
				
				for (attribute, value) in objHash.items():
					if value is None and (mode == 'update'):
						continue
					
					attributeMapping = mapping.get(attribute, mapping.get('*'))
					
					if not attributeMapping is None:
						section = attributeMapping['section']
						option = attributeMapping['option']
						
						match = self._placeholderRegex.search(section)
						if match:
							replaceValue = objHash[match.group(1)]
							if objType in ('ProductOnClient'):
								replaceValue.replace('LocalbootProduct', 'localboot').replace('NetbootProduct', 'netboot')
							section = section.replace(u'<%s>' % match.group(1), replaceValue)
						
						match = self._placeholderRegex.search(option)
						if match:
							option = option.replace(u'<%s>' % match.group(1), objHash[match.group(1)])
						
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
								value = self.__escape(value)
							
							if not cp.has_section(section):
								cp.add_section(section)
							
							cp.set(section, option, value)
				
				iniFile.generate(cp)
			
			elif (fileType == 'pro'):
				if not os.path.exists(filename):
					self._touch(filename)
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
	
	def _delete(self, objList):
		objType = u''
		if objList:
			#objType is not always correct, but _getConfigFile() is
			#within ifs obj.getType() from obj in objList should be used
			objType = objList[0].getType()
		
		if objType in ('OpsiClient', 'OpsiConfigserver', 'OpsiDepotserver'):
			hostKeyFile = HostKeyFile(self._getConfigFile('', {}, 'key'))
			for obj in objList:
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
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
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
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
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if cp.has_option('generalconfig', obj.getConfigId()):
					cp.remove_option('generalconfig', obj.getConfigId())
					logger.debug2(u"Removed option in generalconfig '%s'" % obj.getConfigId())
				iniFile.generate(cp)
		
		elif objType in ('Product', 'LocalbootProduct', 'NetbootProduct'):
			for obj in objList:
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'pro' )
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
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
					logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
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
					logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
					if cp.has_section(obj.getProductId() + '-state'):
						cp.remove_section(obj.getProductId() + '-state')
						logger.debug2(u"Removed section '%s'" % obj.getProductId() + '-state')
				
				iniFile.generate(cp)
		
		elif objType in ('ProductPropertyState'):
			for obj in objList:
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				filename = self._getConfigFile(
					obj.getType(), obj.getIdent(returnType = 'dict'), 'ini')
				iniFile = IniFile(filename = filename, ignoreCase = False)
				cp = iniFile.parse()
				
				section = obj.getProductId() + '-install'
				option = obj.getPropertyId()
				
				if cp.has_option(section, option):
					cp.remove_option(section, option)
					logger.debug2(u"Removed option '%s' in section '%s'" % (option, section))
				
				if (cp.has_section(section)) and (len(cp.options(section)) == 0):
					cp.remove_section(section)
					logger.debug2(u"Removed empty section '%s'" % section)
				
				iniFile.generate(cp)
		
		elif objType in ('Group', 'HostGroup', 'ObjectToGroup'):
			filename = self._getConfigFile(objType, {}, 'ini')
			iniFile = IniFile(filename = filename, ignoreCase = False)
			cp = iniFile.parse()
			
			for obj in objList:
				section = None
				if (obj.getType() == 'ObjectToGroup'):
					section = obj.getGroupId()
				else:
					section = obj.getId()
				
				logger.debug(u"Deleting %s: '%s'" % (obj.getType(), obj.getIdent()))
				if (obj.getType() == 'ObjectToGroup'):
					if cp.has_option(section, obj.getObjectId()):
						cp.remove_option(section, obj.getObjectId())
						logger.debug2(u"Removed option '%s' in section '%s'" \
							% (obj.getObjectId(), section))
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
		
		logger.info(u"Inserting host: '%s'" % host.getIdent())
		self._write(host, mode = 'create')
	
	def host_updateObject(self, host):
		ConfigDataBackend.host_updateObject(self, host)
		
		logger.info(u"Updating host: '%s'" % host.getIdent())
		self._write(host, mode = 'update')
	
	def host_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.host_getObjects(self, attributes, **filter)
		
		logger.info(u"Getting hosts ...")
		result = self._read('OpsiDepotserver', attributes, **filter)
		opsiConfigServers = self._read('OpsiConfigserver', attributes, **filter)
		
		if opsiConfigServers:
			contained = False
			for i in range(len(result)):
				if (result[i].getId() == opsiConfigServers[0].getId()):
					result[i] = opsiConfigServers[0]
					contained = True
					break
			
			if not contained:
				result.append(opsiConfigServers[0])
		result.extend(self._read('OpsiClient', attributes, **filter))
		
		return result
	
	def host_deleteObjects(self, hosts):
		ConfigDataBackend.host_deleteObjects(self, hosts)
		
		logger.info(u"Deleting hosts ...")
		self._delete(forceObjectClassList(hosts, Host))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		ConfigDataBackend.config_insertObject(self, config)
		
		logger.info(u"Inserting config: '%s'" % config.getIdent())
		self._write(config, mode = 'create')
	
	def config_updateObject(self, config):
		ConfigDataBackend.config_updateObject(self, config)
		
		logger.info(u"Updating config: '%s'" % config.getIdent())
		self._write(config, mode = 'update')
	
	def config_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.config_getObjects(self, attributes, **filter)
		
		logger.info(u"Getting configs ...")
		result = self._read('Config', attributes, **filter)
		
		return result
	
	def config_deleteObjects(self, configs):
		ConfigDataBackend.config_deleteObjects(self, configs)
		
		logger.info(u"Deleting configs ...")
		self._delete(forceObjectClassList(configs, Config))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		ConfigDataBackend.configState_insertObject(self, configState)
		
		logger.info(u"Inserting configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'create')
	
	def configState_updateObject(self, configState):
		ConfigDataBackend.configState_updateObject(self, configState)
		
		logger.info(u"Updating configState: '%s'" % configState.getIdent())
		self._write(configState, mode = 'update')
	
	def configState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.configState_getObjects(self, attributes, **filter)
		
		logger.info(u"Getting configStates ...")
		result = self._read('ConfigState', attributes, **filter)
		
		return result
	
	def configState_deleteObjects(self, configStates):
		ConfigDataBackend.configState_deleteObjects(self, configStates)
		
		logger.info(u"Deleting configStates ...")
		self._delete(forceObjectClassList(configStates, ConfigState))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		ConfigDataBackend.product_insertObject(self, product)
		
		logger.info(u"Inserting product: '%s'" % product.getIdent())
		self._write(product, mode = 'create')
	
	def product_updateObject(self, product):
		ConfigDataBackend.product_updateObject(self, product)
		
		logger.info(u"Updating product: '%s'" % product.getIdent())
		self._write(product, mode = 'update')
	
	def product_getObjects(self, attributes = [], **filter):
		ConfigDataBackend.product_getObjects(self, attributes, **filter)
		
		logger.info(u"Getting products ...")
		result = self._read('LocalbootProduct', attributes, **filter)
		result.extend(self._read('NetbootProduct', attributes, **filter))
		
		return result
	
	def product_deleteObjects(self, products):
		ConfigDataBackend.product_deleteObjects(self, products)
		
		logger.info(u"Deleting products ...")
		self._delete(forceObjectClassList(products, Product))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		ConfigDataBackend.productProperty_insertObject(self, productProperty)
		
		logger.info(u"Inserting productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'create')
	
	def productProperty_updateObject(self, productProperty):
		ConfigDataBackend.productProperty_updateObject(self, productProperty)
		
		logger.info(u"Updating productProperty: '%s'" % productProperty.getIdent())
		self._write(productProperty, mode = 'update')
	
	def productProperty_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productProperty_getObjects(self, attributes, **filter)
		
		logger.info(u"Getting productProperties ...")
		result = self._read('ProductProperty', attributes, **filter)
		
		return result
	
	def productProperty_deleteObjects(self, productProperties):
		ConfigDataBackend.productProperty_deleteObjects(self, productProperties)
		
		logger.info(u"Deleting productProperties ...")
		self._delete(forceObjectClassList(productProperties, ProductProperty))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		ConfigDataBackend.productDependency_insertObject(self, productDependency)
		
		logger.info(u"Inserting productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'create')
	
	def productDependency_updateObject(self, productDependency):
		ConfigDataBackend.productDependency_updateObject(self, productDependency)
		
		logger.info(u"Updating productDependency: '%s'" % productDependency.getIdent())
		self._write(productDependency, mode = 'update')
	
	def productDependency_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productDependency_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productDependencies ...")
		result = self._read('ProductDependency', attributes, **filter)
		
		return result
	
	def productDependency_deleteObjects(self, productDependencies):
		ConfigDataBackend.productDependency_deleteObjects(self, productDependencies)
		
		logger.info(u"Deleting productDependencies ...")
		self._delete(forceObjectClassList(productDependencies, ProductDependency))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_insertObject(self, productOnDepot)
		
		logger.info(u"Inserting productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'create')
	
	def productOnDepot_updateObject(self, productOnDepot):
		ConfigDataBackend.productOnDepot_updateObject(self, productOnDepot)
		
		logger.info(u"Updating productOnDepot: '%s'" % productOnDepot.getIdent())
		self._write(productOnDepot, mode = 'update')
	
	def productOnDepot_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnDepot_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productOnDepots ...")
		result = self._read('ProductOnDepot', attributes, **filter)
		
		return result
	
	def productOnDepot_deleteObjects(self, productOnDepots):
		ConfigDataBackend.productOnDepot_deleteObjects(self, productOnDepots)
		
		logger.info(u"Deleting productOnDepots ...")
		self._delete(forceObjectClassList(productOnDepots, ProductOnDepot))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		ConfigDataBackend.productOnClient_insertObject(self, productOnClient)
		
		logger.info(u"Inserting productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'create')
	
	def productOnClient_updateObject(self, productOnClient):
		ConfigDataBackend.productOnClient_updateObject(self, productOnClient)
		
		logger.info(u"Updating productOnClient: '%s'" % productOnClient.getIdent())
		self._write(productOnClient, mode = 'update')
	
	def productOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productOnClient_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productOnClient ...")
		result = self._read('ProductOnClient', attributes, **filter)
		
		return result
	
	def productOnClient_deleteObjects(self, productOnClients):
		ConfigDataBackend.productOnClient_deleteObjects(self, productOnClients)
		
		logger.info(u"Deleting productOnClients ...")
		self._delete(forceObjectClassList(productOnClients, ProductOnClient))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_insertObject(self, productPropertyState)
		
		logger.info(u"Inserting productPropertyState: '%s'" % productPropertyState.getIdent())
		self._write(productPropertyState, mode = 'create')
	
	def productPropertyState_updateObject(self, productPropertyState):
		ConfigDataBackend.productPropertyState_updateObject(self, productPropertyState)
		
		logger.info(u"Updating productPropertyState: '%s'" % productPropertyState.getIdent())
		self._write(productPropertyState, mode = 'update')
	
	def productPropertyState_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.productPropertyState_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting productPropertyStates ...")
		result = self._read('ProductPropertyState', attributes, **filter)
		
		return result
	
	def productPropertyState_deleteObjects(self, productPropertyStates):
		ConfigDataBackend.productPropertyState_deleteObjects(self, productPropertyStates)
		
		logger.info(u"Deleting productPropertyStates ...")
		self._delete(forceObjectClassList(productPropertyStates, ProductPropertyState))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		ConfigDataBackend.group_insertObject(self, group)
		
		logger.info(u"Inserting group: '%s'" % group.getIdent())
		self._write(group, mode = 'create')
	
	def group_updateObject(self, group):
		ConfigDataBackend.group_updateObject(self, group)
		
		logger.info(u"Updating group: '%s'" % group.getIdent())
		self._write(group, mode = 'update')
	
	def group_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.group_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting groups ...")
		result = self._read('Group', attributes, **filter)
		
		return result
	
	def group_deleteObjects(self, groups):
		ConfigDataBackend.group_deleteObjects(self, groups)
		
		logger.info(u"Deleting groups ...")
		self._delete(forceObjectClassList(groups, Group))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_insertObject(self, objectToGroup)
		
		logger.info(u"Inserting objectToGroup: '%s'" % objectToGroup.getIdent())
		self._write(objectToGroup, mode = 'create')
	
	def objectToGroup_updateObject(self, objectToGroup):
		ConfigDataBackend.objectToGroup_updateObject(self, objectToGroup)
		
		logger.info(u"Updating objectToGroup: '%s'" % objectToGroup.getIdent())
		self._write(objectToGroup, mode = 'update')
	
	def objectToGroup_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.objectToGroup_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting objectToGroups ...")
		result = self._read('ObjectToGroup', attributes, **filter)
		
		return result
	
	def objectToGroup_deleteObjects(self, objectToGroups):
		ConfigDataBackend.objectToGroup_deleteObjects(self, objectToGroups)
		
		logger.info(u"Deleting objectToGroups ...")
		self._delete(forceObjectClassList(objectToGroups, ObjectToGroup))
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_insertObject(self, auditSoftware)
		
		logger.info(u"Inserting auditSoftware: '%s'" % auditSoftware.getIdent())
		filename = self._getConfigFile('AuditSoftware', {}, 'sw')
		
		if not os.path.exists(filename):
			self._touch(filename)
		
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		
		nums = []
		for section in ini.sections():
			nums.append(int(section.split('_')[-1]))
		num = 0
		while num in nums:
			num += 1
		
		section = u'SOFTWARE_%d' % num
		ini.add_section(section)
		for (key, value) in auditSoftware.toHash().items():
			if (value is None) or (key == 'type'):
				continue
			ini.set(section, key, self.__escape(value))
		iniFile.generate(ini)
		
	def auditSoftware_updateObject(self, auditSoftware):
		ConfigDataBackend.auditSoftware_updateObject(self, auditSoftware)
		
		logger.info(u"Updating auditSoftware: '%s'" % auditSoftware.getIdent())
		filename = self._getConfigFile('AuditSoftware', {}, 'sw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		ident = auditSoftware.getIdent(returnType = 'dict')
		
		for section in ini.sections():
			found = True
			for (key, value) in ident.items():
				if (self.__unescape(ini.get(section, key.lower())) != value):
					found = False
					break
			if found:
				for (key, value) in auditSoftware.toHash().items():
					if value is None:
						continue
					ini.set(section, key, self.__escape(value))
				iniFile.generate(ini)
				return
		raise Exception(u"AuditSoftware %s not found" % auditSoftware)
		
	def auditSoftware_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftware_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting objectToGroups ...")
		result = []
		filename = self._getConfigFile('AuditSoftware', {}, 'sw')
		if not os.path.exists(filename):
			return result
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		for section in ini.sections():
			objHash = {
				"name":                  None,
				"version":               None,
				"subVersion":            None,
				"language":              None,
				"architecture":          None,
				"windowsSoftwareId":     None,
				"windowsDisplayName":    None,
				"windowsDisplayVersion": None,
				"installSize":           None
			}
			for (key, value) in objHash.items():
				try:
					objHash[key] = self.__unescape(ini.get(section, key.lower()))
				except:
					pass
			
			if self._objectHashMatches(objHash, **filter):
				#TODO: adaptObjHash?
				result.append(AuditSoftware.fromHash(objHash))
		
		return result
	
	def auditSoftware_deleteObjects(self, auditSoftwares):
		ConfigDataBackend.auditSoftware_deleteObjects(self, auditSoftwares)
		
		logger.info(u"Deleting auditSoftwares ...")
		filename = self._getConfigFile('AuditSoftware', {}, 'sw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		idents = []
		for auditSoftware in forceObjectClassList(auditSoftwares, AuditSoftware):
			idents.append(auditSoftware.getIdent(returnType = 'dict'))
		
		for section in ini.sections():
			for ident in idents:
				found = True
				for (key, value) in ident.items():
					if (self.__unescape(ini.get(section, key.lower())) != value):
						found = False
						break
				if found:
					ini.remove_section(section)
		iniFile.generate(ini)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient)
		
		logger.info(u"Inserting auditSoftwareOnClient: '%s'" % auditSoftwareOnClient.getIdent())
		filename = self._getConfigFile('AuditSoftwareOnClient', {"clientId": auditSoftwareOnClient.clientId }, 'sw')
		
		if not os.path.exists(filename):
			self._touch(filename)
		
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		
		nums = []
		for section in ini.sections():
			nums.append(int(section.split('_')[-1]))
		num = 0
		while num in nums:
			num += 1
		
		section = u'SOFTWARE_%d' % num
		ini.add_section(section)
		for (key, value) in auditSoftwareOnClient.toHash().items():
			if (value is None):
				continue
			ini.set(section, key, self.__escape(value))
		iniFile.generate(ini)
	
	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		ConfigDataBackend.auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient)
		
		logger.info(u"Updating auditSoftwareOnClient: '%s'" % auditSoftwareOnClient.getIdent())
		filename = self._getConfigFile('AuditSoftwareOnClient', {"clientId": auditSoftwareOnClient.clientId }, 'sw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		ident = auditSoftwareOnClient.getIdent(returnType = 'dict')
		
		for section in ini.sections():
			found = True
			for (key, value) in ident.items():
				if (self.__unescape(ini.get(section, key.lower())) != value):
					found = False
					break
			if found:
				for (key, value) in auditSoftwareOnClient.toHash().items():
					if value is None:
						continue
					ini.set(section, key, self.__escape(value))
				iniFile.generate(ini)
				return
		raise Exception(u"auditSoftwareOnClient %s not found" % auditSoftwareOnClient)
	
	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditSoftwareOnClient_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting auditSoftwareOnClients ...")
		filenames = {}
		for ident in self._getIdents('AuditSoftwareOnClient', **filter):
			if not ident['clientId'] in filenames.keys():
				filenames[ident['clientId']] = self._getConfigFile('AuditSoftwareOnClient', ident, 'sw')
		
		result = []
		for (clientId, filename) in filenames.items():
			if not os.path.exists(filename):
				continue
			iniFile = IniFile(filename = filename)
			ini = iniFile.parse()
			for section in ini.sections():
				objHash = {
					"name":            None,
					"version":         None,
					"subVersion":      None,
					"language":        None,
					"architecture":    None,
					"clientId":        None,
					"uninstallString": None,
					"binaryName":      None,
					"firstseen":       None,
					"lastseen":        None,
					"state":           None,
					"usageFrequency":  None,
					"lastUsed":        None
				}
				for (key, value) in objHash.items():
					try:
						objHash[key] = self.__unescape(ini.get(section, key.lower()))
					except:
						pass
				
				if self._objectHashMatches(objHash, **filter):
					result.append(AuditSoftwareOnClient.fromHash(objHash))
		
		return result
	
	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		ConfigDataBackend.auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients)
		
		logger.info(u"Deleting auditSoftwareOnClients ...")
		filenames = {}
		idents = {}
		for auditSoftwareOnClient in  forceObjectClassList(auditSoftwareOnClients, AuditSoftwareOnClient):
			ident = auditSoftwareOnClient.getIdent(returnType = 'dict')
			if not idents.has_key(ident['clientId']):
				idents[ident['clientId']] = []
			idents[ident['clientId']].append(ident)
			if not ident['clientId'] in filenames.keys():
				filenames[ident['clientId']] = self._getConfigFile('AuditSoftwareOnClient', ident, 'sw')
		
		for (clientId, filename) in filenames.items():
			iniFile = IniFile(filename = filename)
			ini = iniFile.parse()
			for section in ini.sections():
				for ident in idents[clientId]:
					found = True
					for (key, value) in ident.items():
						if (self.__unescape(ini.get(section, key.lower())) != value):
							found = False
							break
					if found:
						ini.remove_section(section)
			iniFile.generate(ini)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def auditHardware_insertObject(self, auditHardware):
		ConfigDataBackend.auditHardware_insertObject(self, auditHardware)
		
		logger.info(u"Inserting auditHardware: '%s'" % auditHardware.getIdent())
		filename = self._getConfigFile('AuditHardware', {}, 'hw')
		
		if not os.path.exists(filename):
			self._touch(filename)
		
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		
		nums = []
		for section in ini.sections():
			nums.append(int(section.split('_')[-1]))
		num = 0
		while num in nums:
			num += 1
		
		section = u'HARDWARE_%d' % num
		ini.add_section(section)
		for (key, value) in auditHardware.toHash().items():
			if (value is None) or (key == 'type'):
				continue
			ini.set(section, key.lower(), self.__escape(value))
		iniFile.generate(ini)
	
	def auditHardware_updateObject(self, auditHardware):
		ConfigDataBackend.auditHardware_updateObject(self, auditHardware)
		
		logger.info(u"Updating auditHardware: '%s'" % auditHardware.getIdent())
		filename = self._getConfigFile('AuditHardware', {}, 'hw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		ident = auditHardware.getIdent(returnType = 'dict')
		
		for section in ini.sections():
			found = True
			for (key, value) in ident.items():
				if not ini.has_option(section, key.lower()):
					continue
				if (self.__unescape(ini.get(section, key.lower())) != value):
					found = False
					break
			if not found:
				raise Exception(u"AuditHardware '%s' not found" % auditHardware.getIdent())
	
	def auditHardware_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditHardware_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting auditHardwares ...")
		result = []
		filename = self._getConfigFile('AuditHardware', {}, 'hw')
		if not os.path.exists(filename):
			return result
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		for section in ini.sections():
			objHash = {}
			for option in ini.options(section):
				if (option.lower() == 'hardwareclass'):
					objHash['hardwareClass'] = self.__unescape(ini.get(section, option))
				else:
					objHash[str(option)] = self.__unescape(ini.get(section, option))
			
			auditHardware = AuditHardware.fromHash(objHash)
			if self._objectHashMatches(auditHardware.toHash(), **filter):
				result.append(auditHardware)
		
		return result
	
	def auditHardware_deleteObjects(self, auditHardwares):
		ConfigDataBackend.auditHardware_deleteObjects(self, auditHardwares)
		
		logger.info(u"Deleting auditHardwares ...")
		filename = self._getConfigFile('AuditHardware', {}, 'hw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		idents = []
		for auditHardware in forceObjectClassList(auditHardwares, AuditHardware):
			idents.append(auditHardware.getIdent(returnType = 'dict'))
		
		for section in ini.sections():
			for ident in idents:
				found = True
				for (key, value) in ident.items():
					if not ini.has_option(section, key.lower()):
						continue
					if (self.__unescape(ini.get(section, key.lower())) != value):
						found = False
						break
				
				logger.debug2(u"Deleting auditHardware '%s'" % (ident))
				if found:
					ini.remove_section(section)
					logger.debug2(u"Removed section '%s'" % (section))
		iniFile.generate(ini)
	
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	
	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		ConfigDataBackend.auditHardwareOnHost_insertObject(self, auditHardwareOnHost)
		
		logger.info(u"Inserting auditHardwareOnHost: '%s'" % auditHardwareOnHost.getIdent())
		filename = self._getConfigFile('AuditHardwareOnHost', {"hostId": auditHardwareOnHost.hostId }, 'hw')
		
		if not os.path.exists(filename):
			self._touch(filename)
		
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		
		nums = []
		for section in ini.sections():
			nums.append(int(section.split('_')[-1]))
		num = 0
		while num in nums:
			num += 1
		
		section = u'HARDWARE_%d' % num
		ini.add_section(section)
		for (key, value) in auditHardwareOnHost.toHash().items():
			if (value is None) or (key == 'hostId'):
				continue
			ini.set(section, key.lower(), self.__escape(value))
		iniFile.generate(ini)
	
	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		ConfigDataBackend.auditHardwareOnHost_updateObject(self, auditHardwareOnHost)
		
		logger.info(u"Updating auditHardwareOnHost: '%s'" % auditHardwareOnHost.getIdent())
		filename = self._getConfigFile('AuditHardwareOnHost', {"hostId": auditHardwareOnHost.hostId }, 'hw')
		iniFile = IniFile(filename = filename)
		ini = iniFile.parse()
		ident = auditHardwareOnHost.getIdent(returnType = 'dict')
		
		updated = False
		for section in ini.sections():
			found = True
			for (key, value) in ident.items():
				key = key.lower()
				if key == 'hostid':
					continue
				if value is None and not ini.has_option(section, key):
					continue
				if (not ini.has_option(section, key)) or (not self.__unescape(ini.get(section, key) == value)):
					found = False
					break
			if found:
				for (key, value) in auditHardwareOnHost.toHash().items():
					if value is None:
						continue
					ini.set(section, key.lower(), self.__escape(value))
				iniFile.generate(ini)
				return
		raise Exception(u"auditHardwareOnHost %s not found" % auditHardwareOnHost)
	
	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):
		ConfigDataBackend.auditHardwareOnHost_getObjects(self, attributes=[], **filter)
		
		logger.info(u"Getting auditHardwareOnHosts ...")
		filenames = {}
		for ident in self._getIdents('AuditHardwareOnHost', **filter):
			if not ident['hostId'] in filenames.keys():
				filenames[ident['hostId']] = self._getConfigFile('AuditHardwareOnHost', ident, 'hw')
		
		result = []
		for (hostId, filename) in filenames.items():
			if not os.path.exists(filename):
				continue
			iniFile = IniFile(filename = filename)
			ini = iniFile.parse()
			for section in ini.sections():
				objHash = {
				'hostId': hostId
				}
				for option in ini.options(section):
					if option.lower() == u'hardwareclass':
						objHash['hardwareClass'] = self.__unescape(ini.get(section, option))
					else:
						objHash[str(option)] = self.__unescape(ini.get(section, option))
				
				auditHardwareOnHost = AuditHardwareOnHost.fromHash(objHash)
				if self._objectHashMatches(auditHardwareOnHost.toHash(), **filter):
					result.append(auditHardwareOnHost)
		
		return result
	
	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):
		ConfigDataBackend.auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts)
		
		logger.info(u"Deleting auditHardwareOnHosts ...")
		items = {}
		for auditHardwareOnHost in forceObjectClassList(auditHardwareOnHosts, AuditHardwareOnHost):
			ident = auditHardwareOnHost.getIdent(returnType = 'dict')
			filename = self._getConfigFile('AuditHardwareOnHost', ident, 'hw')
			if filename in items.keys():
				items[filename].append(ident)
			else:
				items[filename] = ident
		
		for filename in items.keys():
			idents = forceList(items[filename])
			iniFile = IniFile(filename = filename)
			ini = iniFile.parse()
			
			sections = []
			
			for section in ini.sections():
				for ident in idents:
					found = True
					for (key, value) in ident.items():
						key = key.lower()
						if key == 'hostid':
							continue
						if value is None and not ini.has_option(section, key):
							continue
						if (not ini.has_option(section, key)) or (not self.__unescape(ini.get(section, key) == value)):
							found = False
							break
					if found:
						sections.append(section)
						break
			
			for section in sections:
				ini.remove_section(section)
				logger.debug2(u"Removed section '%s'" % (section))
			
			if len(sections) > 0:
				iniFile.generate(ini)
		
	
	
	








