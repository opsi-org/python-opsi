# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Configuration data holding backend.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Erol Ueluekmen <e.ueluekmen@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import codecs
import collections
import copy as pycopy
import json
import os
import re
import shutil

from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Logger import Logger
from OPSI.Exceptions import (
	BackendBadValueError, BackendMissingDataError,
	BackendReferentialIntegrityError)
from OPSI.Types import (
	forceBool, forceFilename, forceHostId, forceInt, forceLanguageCode,
	forceObjectClass, forceObjectClassList, forceObjectId, forceUnicode,
	forceUnicodeList, forceUnicodeLower)
from OPSI.Object import (
	getPossibleClassAttributes,
	AuditSoftware, AuditSoftwareOnClient, AuditSoftwareToLicensePool,
	AuditHardware, AuditHardwareOnHost, Config, ConfigState, Group, Host,
	LicenseContract, LicenseOnClient, LicensePool, ObjectToGroup, OpsiClient,
	OpsiDepotserver, Product, ProductDependency, ProductOnDepot,
	ProductOnClient, ProductProperty, ProductPropertyState, SoftwareLicense,
	SoftwareLicenseToLicensePool)
from OPSI.Util import blowfishEncrypt, blowfishDecrypt, getfqdn, removeUnit
from OPSI.Util.File import ConfigFile
from OPSI.Util.Log import truncateLogData

from .Backend import Backend

__all__ = ('ConfigDataBackend', )

OPSI_PASSWD_FILE = u'/etc/opsi/passwd'
LOG_DIR = u'/var/log/opsi'
LOG_TYPES = {  # key = logtype, value = requires objectId for read
	'bootimage': True,
	'clientconnect': True,
	'instlog': True,
	'opsiconfd': False,
	'userlogin': True,
	'winpe': True,
}
_PASSWD_LINE_REGEX = re.compile(r'^\s*([^:]+)\s*:\s*(\S+)\s*$')

logger = Logger()

try:
	with open(os.path.join('/etc', 'opsi', 'opsiconfd.conf')) as config:
		for line in config:
			if line.strip().startswith('max-log-size'):
				_, logSize = line.strip().split('=', 1)
				logSize = removeUnit(logSize.strip())
				logger.debug("Setting max log size to {0} MB", logSize)
				DEFAULT_MAX_LOGFILE_SIZE = int(logSize)*1000*1000 
				break
		else:
			raise ValueError("No custom setting found.")
except Exception as error:
	logger.debug("Failed to set MAX LOG SIZE from config: {0}".format(error))
	DEFAULT_MAX_LOGFILE_SIZE = 5000000


class ConfigDataBackend(Backend):
	"""
	Base class for backends holding data.

	These backends should keep data integrity intact but not alter the data.
	"""

	option_defaults = {
		**Backend.option_defaults,
		**{
			'additionalReferentialIntegrityChecks': True
		}
	}

	def __init__(self, **kwargs):
		"""
		Constructor.

		Keyword arguments can differ between implementation.
		:param audithardwareconfigfile: Location of the hardware audit \
configuration file.
		:param audihardwareconfiglocalesdir: Location of the directory \
containing the localisation of the hardware audit.
		:param opsipasswdfile: Location of opsis own passwd file.
		:param depotid: Id of the current depot.
		:param maxlogsize: Maximum size of a logfile.
		"""
		Backend.__init__(self, **kwargs)
		self._auditHardwareConfigFile = u'/etc/opsi/hwaudit/opsihwaudit.conf'
		self._auditHardwareConfigLocalesDir = u'/etc/opsi/hwaudit/locales'
		self._opsiPasswdFile = OPSI_PASSWD_FILE
		self._maxLogfileSize = DEFAULT_MAX_LOGFILE_SIZE
		self._depotId = None

		for (option, value) in kwargs.items():
			option = option.lower()
			if option == 'audithardwareconfigfile':
				self._auditHardwareConfigFile = forceFilename(value)
			elif option == 'audithardwareconfiglocalesdir':
				self._auditHardwareConfigLocalesDir = forceFilename(value)
			elif option == 'opsipasswdfile':
				self._opsiPasswdFile = forceFilename(value)
			elif option in ('depotid', 'serverid'):
				self._depotId = value
			elif option == 'maxlogsize':
				self._maxLogfileSize = forceInt(value)
				logger.info(u'Logsize limited to: {0}'.format(self._maxLogfileSize))

		if not self._depotId:
			self._depotId = getfqdn()
		self._depotId = forceHostId(self._depotId)

	def _testFilterAndAttributes(self, Class, attributes, **filter):
		if not attributes:
			if not filter:
				return

			attributes = []

		possibleAttributes = getPossibleClassAttributes(Class)

		for attribute in forceUnicodeList(attributes):
			if attribute not in possibleAttributes:
				raise BackendBadValueError("Class {0!r} has no attribute '{1}'".format(Class, attribute))

		for attribute in filter:
			if attribute not in possibleAttributes:
				raise BackendBadValueError("Class {0!r} has no attribute '{1}'".format(Class, attribute))

	def backend_createBase(self):
		"""
		Setting up the base for the backend to store its data.

		This can be something like creating a directory structure to setting up a databse.
		"""

	def backend_deleteBase(self):
		"""
		Deleting the base of the backend.

		This is the place to undo all the things that were created by \
*backend_createBase*.
		"""

	def backend_getSystemConfiguration(self):
		"""
		Returns current system configuration.

		This holds information about server-side settings that may be
		relevant for clients.

		Under the key `log` information about log settings will be
		returned in form of a dict.
		In it under `size_limit` you will find the amount of bytes
		currently allowed as maximum log size.
		Under `types` you will find a list with currently supported log
		types.

		:rtype: dict
		"""
		return {
			"log": {
				"size_limit": DEFAULT_MAX_LOGFILE_SIZE,
				"types": [logType for logType in LOG_TYPES]
			}
		}

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Logs                                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def log_write(self, logType, data, objectId=None, append=False):
		"""
		Write log data into the corresponding log file.

		:param logType: Type of log. \
Currently supported: *bootimage*, *clientconnect*, *instlog*, *opsiconfd* or *userlogin*.
		:param data: Log content
		:type data: Unicode
		:param objectId: Specialising of ``logType``
		:param append: Changes the behaviour to either append or \
overwrite the log.
		:type append: bool
		"""
		logType = forceUnicode(logType)
		if logType not in LOG_TYPES:
			raise BackendBadValueError(u"Unknown log type '%s'" % logType)

		if not objectId:
			raise BackendBadValueError(u"Writing {0} log requires an objectId".format(logType))
		objectId = forceObjectId(objectId)

		limitFileSize = self._maxLogfileSize > 0
		data = forceUnicode(data)
		logFile = os.path.join(LOG_DIR, logType, '{0}.log'.format(objectId))

		if not os.path.exists(os.path.dirname(logFile)):
			os.mkdir(os.path.dirname(logFile), 0o2770)

		logWriteMode = "w"
		if forceBool(append):
			logWriteMode = "a"
			if limitFileSize and os.path.exists(logFile):
				currentLogSize = os.stat(logFile).st_size
				amountToReadFromLog = self._maxLogfileSize - len(data)
				if 0 < amountToReadFromLog < currentLogSize:
					logWriteMode = "w"
					with codecs.open(logFile, 'r', 'utf-8', 'replace') as log:
						log.seek(currentLogSize - amountToReadFromLog)
						oldData = log.read()
						idx = oldData.find("\n")
						if idx > 0:
							oldData = oldData[idx+1:]
						data = oldData + data
		
		if limitFileSize and len(data) > self._maxLogfileSize:
			data = truncateLogData(data, self._maxLogfileSize)

		with codecs.open(logFile, logWriteMode, 'utf-8', 'replace') as log:
			log.write(data)

		try:
			shutil.chown(logFile, group=OPSI_ADMIN_GROUP)
		except LookupError:
			# Group could not be found
			pass

		os.chmod(logFile, 0o640)

	def log_read(self, logType, objectId=None, maxSize=0):
		"""
		Return the content of a log.

		:param logType: Type of log. \
Currently supported: *bootimage*, *clientconnect*, *instlog*, *opsiconfd* or *userlogin*.
		:type data: Unicode
		:param objectId: Specialising of ``logType``
		:param maxSize: Limit for the size of returned characters in bytes. \
Setting this to `0` disables limiting.
		"""
		logType = forceUnicode(logType)
		maxSize = int(maxSize)
		
		if logType not in LOG_TYPES:
			raise BackendBadValueError(u'Unknown log type {0!r}'.format(logType))

		if objectId:
			objectId = forceObjectId(objectId)
			logFile = os.path.join(LOG_DIR, logType, '{0}.log'.format(objectId))
		else:
			if LOG_TYPES[logType]:
				raise BackendBadValueError(u"Log type {0!r} requires objectId".format(logType))

			logFile = os.path.join(LOG_DIR, logType, 'opsiconfd.log')

		try:
			with codecs.open(logFile, 'r', 'utf-8', 'replace') as log:
				data = log.read()
		except IOError as ioerr:
			if ioerr.errno == 2:  # This is "No such file or directory"
				return u''

			raise

		if maxSize > 0 and len(data) > maxSize:
			return truncateLogData(data, maxSize)

		return data

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Users                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def user_getCredentials(self, username=u'pcpatch', hostId=None):
		"""
		Get the credentials of an opsi user.
		The information is stored in ``/etc/opsi/passwd``.

		:param hostId: Optional value that should be the calling host.
		:return: Dict with the keys *password* and *rsaPrivateKey*. \
If this is called with an valid hostId the data will be encrypted with \
the opsi host key.
		:rtype: dict
		"""
		username = forceUnicodeLower(username)
		if hostId:
			hostId = forceHostId(hostId)

		result = {'password': u'', 'rsaPrivateKey': u''}

		cf = ConfigFile(filename=self._opsiPasswdFile)
		for line in cf.parse():
			match = _PASSWD_LINE_REGEX.search(line)
			if match is None:
				continue

			if match.group(1) == username:
				result['password'] = match.group(2)
				break

		if not result['password']:
			raise BackendMissingDataError(u"Username '%s' not found in '%s'" % (username, self._opsiPasswdFile))

		depot = self.host_getObjects(id=self._depotId)
		if not depot:
			raise BackendMissingDataError(u"Depot {0!r} not found in backend".format(self._depotId))
		depot = depot[0]
		if not depot.opsiHostKey:
			raise BackendMissingDataError(u"Host key for depot {0!r} not found".format(self._depotId))

		result['password'] = blowfishDecrypt(depot.opsiHostKey, result['password'])

		if username == 'pcpatch':
			try:
				import pwd
				idRsa = os.path.join(pwd.getpwnam(username)[5], u'.ssh', u'id_rsa')
				with open(idRsa, 'r') as f:
					result['rsaPrivateKey'] = f.read()
			except Exception as e:
				logger.debug(e)

		if hostId:
			host = self._context.host_getObjects(id=hostId)  # pylint: disable=maybe-no-member
			try:
				host = host[0]
			except IndexError:
				raise BackendMissingDataError(u"Host %r not found in backend" % hostId)

			result['password'] = blowfishEncrypt(host.opsiHostKey, result['password'])
			if result['rsaPrivateKey']:
				result['rsaPrivateKey'] = blowfishEncrypt(host.opsiHostKey, result['rsaPrivateKey'])

		return result

	def user_setCredentials(self, username, password):
		"""
		Set the password of an opsi user.
		The information is stored in ``/etc/opsi/passwd``.
		The password will be encrypted with the opsi host key of the \
depot where the method is.
		"""
		username = forceUnicodeLower(username)
		password = forceUnicode(password)

		try:
			depot = self._context.host_getObjects(id=self._depotId)  # pylint: disable=maybe-no-member
			depot = depot[0]
		except IndexError:
			raise BackendMissingDataError(u"Depot {0!r} not found in backend {1}".format(self._depotId, self._context))

		encodedPassword = blowfishEncrypt(depot.opsiHostKey, password)

		cf = ConfigFile(filename=self._opsiPasswdFile)
		lines = []
		try:
			for line in cf.readlines():
				match = _PASSWD_LINE_REGEX.search(line)
				if not match or (match.group(1) != username):
					lines.append(line.rstrip())
		except FileNotFoundError:
			pass

		lines.append(u'%s:%s' % (username, encodedPassword))
		cf.open('w')
		cf.writelines(lines)
		cf.close()

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):
		host = forceObjectClass(host, Host)
		host.setDefaults()  # pylint: disable=maybe-no-member

	def host_updateObject(self, host):
		host = forceObjectClass(host, Host)

	def host_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.host_getObjects(attributes, **filter)]

	def host_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Host, attributes, **filter)
		return []

	def host_deleteObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			# Remove from groups
			self._context.objectToGroup_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.objectToGroup_getObjects(  # pylint: disable=maybe-no-member
					groupType='HostGroup',
					objectId=host.id
				)
			)

			if isinstance(host, OpsiClient):
				# Remove product states
				self._context.productOnClient_deleteObjects(  # pylint: disable=maybe-no-member
					self._context.productOnClient_getObjects(clientId=host.id)  # pylint: disable=maybe-no-member
				)
			elif isinstance(host, OpsiDepotserver):
				# This is also true for OpsiConfigservers
				# Remove products
				self._context.productOnDepot_deleteObjects(  # pylint: disable=maybe-no-member
					self._context.productOnDepot_getObjects(depotId=host.id)  # pylint: disable=maybe-no-member
				)
			# Remove product property states
			self._context.productPropertyState_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productPropertyState_getObjects(objectId=host.id)  # pylint: disable=maybe-no-member
			)
			# Remove config states
			self._context.configState_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.configState_getObjects(objectId=host.id)  # pylint: disable=maybe-no-member
			)

			if isinstance(host, OpsiClient):
				# Remove audit softwares
				self._context.auditSoftwareOnClient_deleteObjects(  # pylint: disable=maybe-no-member
					self._context.auditSoftwareOnClient_getObjects(  # pylint: disable=maybe-no-member
						clientId=host.id
					)
				)

			# Remove audit hardwares
			self._context.auditHardwareOnHost_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.auditHardwareOnHost_getObjects(hostId=host.id)  # pylint: disable=maybe-no-member
			)

			if isinstance(host, OpsiClient):
				# Free software licenses
				self._context.licenseOnClient_deleteObjects(  # pylint: disable=maybe-no-member
					self._context.licenseOnClient_getObjects(clientId=host.id)  # pylint: disable=maybe-no-member
				)

				softwareLicenses = self._context.softwareLicense_getObjects(boundToHost=host.id)  # pylint: disable=maybe-no-member
				softwareLicenses = softwareLicenses or []
				for softwareLicense in softwareLicenses:
					softwareLicense.boundToHost = None
					self._context.softwareLicense_insertObject(softwareLicense)  # pylint: disable=maybe-no-member

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):
		config = forceObjectClass(config, Config)
		config.setDefaults()  # pylint: disable=maybe-no-member

	def config_updateObject(self, config):
		config = forceObjectClass(config, Config)

	def config_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.config_getObjects(attributes, **filter)]

	def config_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Config, attributes, **filter)
		return []

	def config_deleteObjects(self, configs):
		ids = [config.id for config in forceObjectClassList(configs, Config)]

		if ids:
			self._context.configState_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.configState_getObjects(  # pylint: disable=maybe-no-member
					configId=ids,
					objectId=[]
				)
			)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		configState = forceObjectClass(configState, ConfigState)
		configState.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			configIds = [config.id for config in self._context.config_getObjects(attributes=['id'])]  # pylint: disable=maybe-no-member

			if configState.configId not in configIds:  # pylint: disable=maybe-no-member
				raise BackendReferentialIntegrityError(u"Config with id '%s' not found" % configState.configId)  # pylint: disable=maybe-no-member

	def configState_updateObject(self, configState):
		configState = forceObjectClass(configState, ConfigState)

	def configState_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.configState_getObjects(attributes, **filter)]

	def configState_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ConfigState, attributes, **filter)
		return []

	def configState_deleteObjects(self, configStates):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):
		product = forceObjectClass(product, Product)
		product.setDefaults()  # pylint: disable=maybe-no-member

	def product_updateObject(self, product):
		product = forceObjectClass(product, Product)

	def product_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.product_getObjects(attributes, **filter)]

	def product_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Product, attributes, **filter)
		return []

	def product_deleteObjects(self, products):
		productByIdAndVersion = collections.defaultdict(lambda: collections.defaultdict(list))
		for product in forceObjectClassList(products, Product):
			productByIdAndVersion[product.id][product.productVersion].append(product.packageVersion)

			self._context.productProperty_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productProperty_getObjects(  # pylint: disable=maybe-no-member
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)
			self._context.productDependency_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productDependency_getObjects(  # pylint: disable=maybe-no-member
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)
			self._context.productOnDepot_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productOnDepot_getObjects(  # pylint: disable=maybe-no-member
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)

		for (productId, versions) in productByIdAndVersion.items():
			allProductVersionsWillBeDeleted = True
			for product in self._context.product_getObjects(attributes=['id', 'productVersion', 'packageVersion'], id=productId):  # pylint: disable=maybe-no-member
				if product.packageVersion not in versions.get(product.productVersion, []):
					allProductVersionsWillBeDeleted = False
					break

			if not allProductVersionsWillBeDeleted:
				continue

			# Remove from groups, when allProductVerionsWillBeDelted
			self._context.objectToGroup_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.objectToGroup_getObjects(  # pylint: disable=maybe-no-member
					groupType='ProductGroup',
					objectId=productId
				)
			)
			self._context.productOnClient_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productOnClient_getObjects(productId=productId)  # pylint: disable=maybe-no-member
			)
			self._context.productPropertyState_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.productPropertyState_getObjects(productId=productId)  # pylint: disable=maybe-no-member
			)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		productProperty = forceObjectClass(productProperty, ProductProperty)
		productProperty.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(  # pylint: disable=maybe-no-member
					attributes=['id', 'productVersion', 'packageVersion'],
					id=productProperty.productId,  # pylint: disable=maybe-no-member
					productVersion=productProperty.productVersion,  # pylint: disable=maybe-no-member
					packageVersion=productProperty.packageVersion):  # pylint: disable=maybe-no-member

				raise BackendReferentialIntegrityError(
					u"Product with id '{0}', productVersion '{1}', "
					u"packageVersion '{2}' not found".format(
						productProperty.productId,  # pylint: disable=maybe-no-member
						productProperty.productVersion,  # pylint: disable=maybe-no-member
						productProperty.packageVersion  # pylint: disable=maybe-no-member
					)
				)

	def productProperty_updateObject(self, productProperty):
		productProperty = forceObjectClass(productProperty, ProductProperty)

	def productProperty_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.productProperty_getObjects(attributes, **filter)]

	def productProperty_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductProperty, attributes, **filter)
		return []

	def productProperty_deleteObjects(self, productProperties):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		productDependency = forceObjectClass(productDependency, ProductDependency)
		productDependency.setDefaults()  # pylint: disable=maybe-no-member
		if not productDependency.getRequiredAction() and not productDependency.getRequiredInstallationStatus():  # pylint: disable=maybe-no-member
			raise BackendBadValueError(u"Either a required action or a required installation status must be given")
		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(  # pylint: disable=maybe-no-member
					attributes=['id', 'productVersion', 'packageVersion'],
					id=productDependency.productId,  # pylint: disable=maybe-no-member
					productVersion=productDependency.productVersion,  # pylint: disable=maybe-no-member
					packageVersion=productDependency.packageVersion):  # pylint: disable=maybe-no-member

				raise BackendReferentialIntegrityError(
					u"Product with id '{0}', productVersion '{1}', "
					u"packageVersion '{2}' not found".format(
						productDependency.productId,  # pylint: disable=maybe-no-member
						productDependency.productVersion,  # pylint: disable=maybe-no-member
						productDependency.packageVersion  # pylint: disable=maybe-no-member
					)
				)

	def productDependency_updateObject(self, productDependency):
		productDependency = forceObjectClass(productDependency, ProductDependency)

	def productDependency_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.productDependency_getObjects(attributes, **filter)]

	def productDependency_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductDependency, attributes, **filter)
		return []

	def productDependency_deleteObjects(self, productDependencies):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		productOnDepot.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(  # pylint: disable=maybe-no-member
				attributes=['id', 'productVersion', 'packageVersion'],
				id=productOnDepot.productId,  # pylint: disable=maybe-no-member
				productVersion=productOnDepot.productVersion,  # pylint: disable=maybe-no-member
				packageVersion=productOnDepot.packageVersion):  # pylint: disable=maybe-no-member

				raise BackendReferentialIntegrityError(
					u"Product with id '{0}', productVersion '{1}', "
					u"packageVersion '{2}' not found".format(
						productOnDepot.productId,  # pylint: disable=maybe-no-member
						productOnDepot.productVersion,  # pylint: disable=maybe-no-member
						productOnDepot.packageVersion  # pylint: disable=maybe-no-member
					)
				)

	def productOnDepot_updateObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(  # pylint: disable=maybe-no-member
				attributes=['id', 'productVersion', 'packageVersion'],
				id=productOnDepot.productId,  # pylint: disable=maybe-no-member
				productVersion=productOnDepot.productVersion,  # pylint: disable=maybe-no-member
				packageVersion=productOnDepot.packageVersion):  # pylint: disable=maybe-no-member

				raise BackendReferentialIntegrityError(
					u"Product with id '{0}', productVersion '{1}', "
					u"packageVersion '{2}' not found".format(
						productOnDepot.productId,  # pylint: disable=maybe-no-member
						productOnDepot.productVersion,  # pylint: disable=maybe-no-member
						productOnDepot.packageVersion  # pylint: disable=maybe-no-member
					)
				)

	def productOnDepot_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.productOnDepot_getObjects(attributes, **filter)]

	def productOnDepot_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnDepot, attributes, **filter)
		return []

	def productOnDepot_deleteObjects(self, productOnDepots):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		productOnClient.setDefaults()  # pylint: disable=maybe-no-member

		if (productOnClient.installationStatus == 'installed') and (not productOnClient.productVersion or not productOnClient.packageVersion):  # pylint: disable=maybe-no-member
			raise BackendReferentialIntegrityError(u"Cannot set installationStatus for product '%s', client '%s' to 'installed' without productVersion and packageVersion" \
				% (productOnClient.productId, productOnClient.clientId))  # pylint: disable=maybe-no-member

		if productOnClient.installationStatus != 'installed':  # pylint: disable=maybe-no-member
			productOnClient.productVersion = None
			productOnClient.packageVersion = None

	def productOnClient_updateObject(self, productOnClient):
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)

	def productOnClient_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.productOnClient_getObjects(attributes, **filter)]

	def productOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductOnClient, attributes, **filter)
		return []

	def productOnClient_deleteObjects(self, productOnClients):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		productPropertyState = forceObjectClass(productPropertyState, ProductPropertyState)
		productPropertyState.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.productProperty_getObjects(  # pylint: disable=maybe-no-member
				attributes=['productId', 'propertyId'],
				productId=productPropertyState.productId,  # pylint: disable=maybe-no-member
				propertyId=productPropertyState.propertyId):  # pylint: disable=maybe-no-member

				raise BackendReferentialIntegrityError(u"ProductProperty with id '%s' for product '%s' not found"
					% (productPropertyState.propertyId, productPropertyState.productId))  # pylint: disable=maybe-no-member

	def productPropertyState_updateObject(self, productPropertyState):
		productPropertyState = forceObjectClass(productPropertyState, ProductPropertyState)

	def productPropertyState_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.productPropertyState_getObjects(attributes, **filter)]

	def productPropertyState_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ProductPropertyState, attributes, **filter)
		return []

	def productPropertyState_deleteObjects(self, productPropertyStates):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		group = forceObjectClass(group, Group)
		group.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			if group.parentGroupId and not self._context.group_getObjects(attributes=['id'], id=group.parentGroupId):  # pylint: disable=maybe-no-member
				raise BackendReferentialIntegrityError(u"Parent group '%s' of group '%s' not found" % (group.parentGroupId, group.id))  # pylint: disable=maybe-no-member

	def group_updateObject(self, group):
		group = forceObjectClass(group, Group)

	def group_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.group_getObjects(attributes, **filter)]

	def group_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(Group, attributes, **filter)
		return []

	def group_deleteObjects(self, groups):
		for group in forceObjectClassList(groups, Group):
			matchingMappings = self._context.objectToGroup_getObjects(
				groupType=group.getType(),
				groupId=group.id
			)
			self._context.objectToGroup_deleteObjects(matchingMappings)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ObjectToGroups                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def objectToGroup_insertObject(self, objectToGroup):
		objectToGroup = forceObjectClass(objectToGroup, ObjectToGroup)
		objectToGroup.setDefaults()  # pylint: disable=maybe-no-member

	def objectToGroup_updateObject(self, objectToGroup):
		objectToGroup = forceObjectClass(objectToGroup, ObjectToGroup)

	def objectToGroup_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.objectToGroup_getObjects(attributes, **filter)]

	def objectToGroup_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(ObjectToGroup, attributes, **filter)
		return []

	def objectToGroup_deleteObjects(self, objectToGroups):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_insertObject(self, licenseContract):
		licenseContract = forceObjectClass(licenseContract, LicenseContract)
		licenseContract.setDefaults()  # pylint: disable=maybe-no-member

	def licenseContract_updateObject(self, licenseContract):
		licenseContract = forceObjectClass(licenseContract, LicenseContract)

	def licenseContract_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.licenseContract_getObjects(attributes, **filter)]

	def licenseContract_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicenseContract, attributes, **filter)
		return []

	def licenseContract_deleteObjects(self, licenseContracts):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_insertObject(self, softwareLicense):
		softwareLicense = forceObjectClass(softwareLicense, SoftwareLicense)
		softwareLicense.setDefaults()  # pylint: disable=maybe-no-member
		if not softwareLicense.licenseContractId:  # pylint: disable=maybe-no-member
			raise BackendBadValueError(u"License contract missing")

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.licenseContract_getObjects(attributes=['id'], id=softwareLicense.licenseContractId):  # pylint: disable=maybe-no-member
				raise BackendReferentialIntegrityError(u"License contract with id '%s' not found" % softwareLicense.licenseContractId)  # pylint: disable=maybe-no-member

	def softwareLicense_updateObject(self, softwareLicense):
		softwareLicense = forceObjectClass(softwareLicense, SoftwareLicense)

	def softwareLicense_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.softwareLicense_getObjects(attributes, **filter)]

	def softwareLicense_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(SoftwareLicense, attributes, **filter)
		return []

	def softwareLicense_deleteObjects(self, softwareLicenses):
		softwareLicenseIds = [softwareLicense.id for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense)]

		self._context.softwareLicenseToLicensePool_deleteObjects(  # pylint: disable=maybe-no-member
			self._context.softwareLicenseToLicensePool_getObjects(  # pylint: disable=maybe-no-member
				softwareLicenseId=softwareLicenseIds
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePools                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_insertObject(self, licensePool):
		licensePool = forceObjectClass(licensePool, LicensePool)
		licensePool.setDefaults()  # pylint: disable=maybe-no-member

	def licensePool_updateObject(self, licensePool):
		licensePool = forceObjectClass(licensePool, LicensePool)

	def licensePool_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.licensePool_getObjects(attributes, **filter)]

	def licensePool_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicensePool, attributes, **filter)
		return []

	def licensePool_deleteObjects(self, licensePools):
		licensePoolIds = [licensePool.id for licensePool in forceObjectClassList(licensePools, LicensePool)]

		if licensePoolIds:
			softwareLicenseToLicensePools = self._context.softwareLicenseToLicensePool_getObjects(licensePoolId=licensePoolIds)  # pylint: disable=maybe-no-member
			if softwareLicenseToLicensePools:
				raise BackendReferentialIntegrityError(u"Refusing to delete license pool(s) %s, one ore more licenses/keys refer to pool: %s" % \
					(licensePoolIds, softwareLicenseToLicensePools))

			self._context.auditSoftwareToLicensePool_deleteObjects(  # pylint: disable=maybe-no-member
				self._context.auditSoftwareToLicensePool_getObjects(  # pylint: disable=maybe-no-member
					name=[],
					version=[],
					subVersion=[],
					language=[],
					architecture=[],
					licensePoolId=licensePoolIds
				)
			)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenseToLicensePools                                                             -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool):
		softwareLicenseToLicensePool = forceObjectClass(softwareLicenseToLicensePool, SoftwareLicenseToLicensePool)
		softwareLicenseToLicensePool.setDefaults()  # pylint: disable=maybe-no-member

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.softwareLicense_getObjects(attributes=['id'], id=softwareLicenseToLicensePool.softwareLicenseId):  # pylint: disable=maybe-no-member
				raise BackendReferentialIntegrityError(u"Software license with id '%s' not found" % softwareLicenseToLicensePool.softwareLicenseId)  # pylint: disable=maybe-no-member
			if not self._context.licensePool_getObjects(attributes=['id'], id=softwareLicenseToLicensePool.licensePoolId):  # pylint: disable=maybe-no-member
				raise BackendReferentialIntegrityError(u"License with id '%s' not found" % softwareLicenseToLicensePool.licensePoolId)  # pylint: disable=maybe-no-member

	def softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool):
		softwareLicenseToLicensePool = forceObjectClass(softwareLicenseToLicensePool, SoftwareLicenseToLicensePool)

	def softwareLicenseToLicensePool_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.softwareLicenseToLicensePool_getObjects(attributes, **filter)]

	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(SoftwareLicenseToLicensePool, attributes, **filter)
		return []

	def softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools):
		softwareLicenseIds = [softwareLicenseToLicensePool.softwareLicenseId for softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool)]

		if softwareLicenseIds:
			licenseOnClients = self._context.licenseOnClient_getObjects(softwareLicenseId=softwareLicenseIds)  # pylint: disable=maybe-no-member
			if licenseOnClients:
				raise BackendReferentialIntegrityError(u"Refusing to delete softwareLicenseToLicensePool(s), one ore more licenses in use: %s"\
					% licenseOnClients)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_insertObject(self, licenseOnClient):
		licenseOnClient = forceObjectClass(licenseOnClient, LicenseOnClient)
		licenseOnClient.setDefaults()  # pylint: disable=maybe-no-member

	def licenseOnClient_updateObject(self, licenseOnClient):
		licenseOnClient = forceObjectClass(licenseOnClient, LicenseOnClient)

	def licenseOnClient_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.licenseOnClient_getObjects(attributes, **filter)]

	def licenseOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(LicenseOnClient, attributes, **filter)
		return []

	def licenseOnClient_deleteObjects(self, licenseOnClients):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):
		auditSoftware = forceObjectClass(auditSoftware, AuditSoftware)
		auditSoftware.setDefaults()  # pylint: disable=maybe-no-member

	def auditSoftware_updateObject(self, auditSoftware):
		auditSoftware = forceObjectClass(auditSoftware, AuditSoftware)

	def auditSoftware_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.auditSoftware_getObjects(attributes, **filter)]

	def auditSoftware_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(AuditSoftware, attributes, **filter)
		return []

	def auditSoftware_deleteObjects(self, auditSoftwares):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareToLicensePools                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareToLicensePool_insertObject(self, auditSoftwareToLicensePool):
		auditSoftwareToLicensePool = forceObjectClass(auditSoftwareToLicensePool, AuditSoftwareToLicensePool)
		auditSoftwareToLicensePool.setDefaults()  # pylint: disable=maybe-no-member

	def auditSoftwareToLicensePool_updateObject(self, auditSoftwareToLicensePool):
		auditSoftwareToLicensePool = forceObjectClass(auditSoftwareToLicensePool, AuditSoftwareToLicensePool)

	def auditSoftwareToLicensePool_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.auditSoftwareToLicensePool_getObjects(attributes, **filter)]

	def auditSoftwareToLicensePool_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(AuditSoftwareToLicensePool, attributes, **filter)
		return []

	def auditSoftwareToLicensePool_deleteObjects(self, auditSoftwareToLicensePools):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):
		auditSoftwareOnClient = forceObjectClass(auditSoftwareOnClient, AuditSoftwareOnClient)
		auditSoftwareOnClient.setDefaults()  # pylint: disable=maybe-no-member

	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):
		auditSoftwareOnClient = forceObjectClass(auditSoftwareOnClient, AuditSoftwareOnClient)

	def auditSoftwareOnClient_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.auditSoftwareOnClient_getObjects(attributes, **filter)]

	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):
		self._testFilterAndAttributes(AuditSoftwareOnClient, attributes, **filter)
		return []

	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardware_insertObject(self, auditHardware):
		auditHardware = forceObjectClass(auditHardware, AuditHardware)
		auditHardware.setDefaults()  # pylint: disable=maybe-no-member

	def auditHardware_updateObject(self, auditHardware):
		auditHardware = forceObjectClass(auditHardware, AuditHardware)

	def auditHardware_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.auditHardware_getObjects(attributes, **filter)]

	def auditHardware_getObjects(self, attributes=[], **filter):
		return []

	def auditHardware_deleteObjects(self, auditHardwares):
		pass

	def auditHardware_getConfig(self, language=None):
		if self._auditHardwareConfigFile.endswith('.json'):
			try:
				with codecs.open(self._auditHardwareConfigFile, 'r', 'utf8') as f:
					return json.loads(f.read())
			except Exception as e:
				logger.warning(u"Failed to read audit hardware configuration from file '%s': %s" % (self._auditHardwareConfigFile, e))
				return []

		if not language:
			language = 'en_US'
		language = forceLanguageCode(language).replace('-', '_')

		localeFile = os.path.join(self._auditHardwareConfigLocalesDir, language)
		if not os.path.exists(localeFile):
			logger.error(u"No translation file found for language %s, falling back to en_US" % language)
			language = 'en_US'
			localeFile = os.path.join(self._auditHardwareConfigLocalesDir, language)

		locale = {}
		try:
			lf = ConfigFile(localeFile)
			for line in lf.parse():
				try:
					identifier, translation = line.split('=', 1)
					locale[identifier.strip()] = translation.strip()
				except ValueError as verr:
					logger.debug2(u"Failed to read translation: {0!r}", verr)
			del lf
		except Exception as e:
			logger.error(u"Failed to read translation file for language {0}: {1}", language, e)

		def __inheritFromSuperClasses(classes, c, scname=None):
			if not scname:
				for scname in c['Class'].get('Super', []):
					__inheritFromSuperClasses(classes, c, scname)
			else:
				for cl in classes:
					if cl['Class'].get('Opsi') == scname:
						clcopy = pycopy.deepcopy(cl)
						__inheritFromSuperClasses(classes, clcopy)
						newValues = []
						for newValue in clcopy['Values']:
							foundAt = -1
							for i, currentValue in enumerate(c['Values']):
								if currentValue['Opsi'] == newValue['Opsi']:
									if not currentValue.get('UI'):
										c['Values'][i]['UI'] = newValue.get('UI', '')
									foundAt = i
									break
							if foundAt > -1:
								newValue = c['Values'][foundAt]
								del c['Values'][foundAt]
							newValues.append(newValue)
						newValues.extend(c['Values'])
						c['Values'] = newValues
						break
				else:
					logger.error(u"Super class '%s' of class '%s' not found!" % (scname, c['Class'].get('Opsi')))

		classes = []
		try:
			with open(self._auditHardwareConfigFile) as hwcFile:
				exec(hwcFile.read())

			for i, currentClassConfig in enumerate(OPSI_HARDWARE_CLASSES):
				opsiClass = currentClassConfig['Class']['Opsi']
				if currentClassConfig['Class']['Type'] == 'STRUCTURAL':
					if locale.get(opsiClass):
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = locale[opsiClass]
					else:
						logger.error(u"No translation for class '%s' found" % opsiClass)
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = opsiClass

				for j, currentValue in enumerate(currentClassConfig['Values']):
					opsiProperty = currentValue['Opsi']
					try:
						OPSI_HARDWARE_CLASSES[i]['Values'][j]['UI'] = locale[opsiClass + '.' + opsiProperty]
					except KeyError:
						pass

			for c in OPSI_HARDWARE_CLASSES:
				try:
					if c['Class'].get('Type') == 'STRUCTURAL':
						logger.debug(u"Found STRUCTURAL hardware class '%s'" % c['Class'].get('Opsi'))
						ccopy = pycopy.deepcopy(c)
						if 'Super' in ccopy['Class']:
							__inheritFromSuperClasses(OPSI_HARDWARE_CLASSES, ccopy)
							del ccopy['Class']['Super']
						del ccopy['Class']['Type']

						# Fill up empty display names
						for j, currentValue in enumerate(ccopy.get('Values', [])):
							if not currentValue.get('UI'):
								logger.warning("No translation for property '%s.%s' found" % (ccopy['Class']['Opsi'], currentValue['Opsi']))
								ccopy['Values'][j]['UI'] = currentValue['Opsi']

						classes.append(ccopy)
				except Exception as e:
					logger.error(u"Error in config file '%s': %s" % (self._auditHardwareConfigFile, e))
		except Exception as e:
			logger.warning(u"Failed to read audit hardware configuration from file '%s': %s" % (self._auditHardwareConfigFile, e))

		return classes

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		auditHardwareOnHost = forceObjectClass(auditHardwareOnHost, AuditHardwareOnHost)
		auditHardwareOnHost.setDefaults()  # pylint: disable=maybe-no-member
		self._context.auditHardware_insertObject(AuditHardware.fromHash(auditHardwareOnHost.toHash()))  # pylint: disable=maybe-no-member

	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):
		auditHardwareOnHost = forceObjectClass(auditHardwareOnHost, AuditHardwareOnHost)

	def auditHardwareOnHost_getHashes(self, attributes=[], **filter):
		return [obj.toHash() for obj in self.auditHardwareOnHost_getObjects(attributes, **filter)]

	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):
		return []

	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   direct access                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def getData(self, query):
		return query

	def getRawData(self, query):
		return query
