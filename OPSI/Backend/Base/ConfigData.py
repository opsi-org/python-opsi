# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Configuration data holding backend.
"""

# pylint: disable=too-many-lines

import platform
import codecs
import collections
import copy as pycopy
import json
import os
import re
import shutil

from opsicommon.logging import logger, secret_filter
from opsicommon.license import get_default_opsi_license_pool

from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Exceptions import (
	BackendBadValueError, BackendMissingDataError, BackendReferentialIntegrityError
)
from OPSI.Types import (
	forceBool, forceFilename, forceHostId, forceInt, forceLanguageCode,
	forceObjectClass, forceObjectClassList, forceObjectId, forceUnicode,
	forceUnicodeList, forceUnicodeLower
)
from OPSI.Object import (
	getPossibleClassAttributes,
	AuditSoftware, AuditSoftwareOnClient, AuditSoftwareToLicensePool,
	AuditHardware, AuditHardwareOnHost, Config, ConfigState, Group, Host,
	LicenseContract, LicenseOnClient, LicensePool, ObjectToGroup, OpsiClient,
	OpsiDepotserver, Product, ProductDependency, ProductOnDepot,
	ProductOnClient, ProductProperty, ProductPropertyState, SoftwareLicense,
	SoftwareLicenseToLicensePool
)
from OPSI.Util import blowfishEncrypt, blowfishDecrypt, getfqdn, removeUnit
from OPSI.Util.File import ConfigFile
from OPSI.Util.Log import truncateLogData

from .Backend import Backend


__all__ = ('ConfigDataBackend', )

OPSI_PASSWD_FILE = '/etc/opsi/passwd'
LOG_DIR = '/var/log/opsi'
LOG_TYPES = {  # key = logtype, value = requires objectId for read
	'bootimage': True,
	'clientconnect': True,
	'instlog': True,
	'opsiconfd': False,
	'userlogin': True,
	'winpe': True,
}
_PASSWD_LINE_REGEX = re.compile(r'^\s*([^:]+)\s*:\s*(\S+)\s*$')
OPSI_HARDWARE_CLASSES = []

DEFAULT_MAX_LOGFILE_SIZE = 5000000
if platform.system().lower() == 'linux':
	try:
		with open(os.path.join('/etc', 'opsi', 'opsiconfd.conf')) as opsiconfd_config:
			for _line in opsiconfd_config:
				if _line.strip().startswith('max-log-size'):
					_, logSize = _line.strip().split('=', 1)
					logSize = removeUnit(logSize.strip())
					logger.debug("Setting max log size to %s MB", logSize)
					DEFAULT_MAX_LOGFILE_SIZE = int(logSize)*1000*1000
					break
			else:
				raise ValueError("No custom setting found.")
	except Exception as max_log_err:  # pylint: disable=broad-except
		logger.debug("Failed to set MAX LOG SIZE from config: %s", max_log_err)


class ConfigDataBackend(Backend):  # pylint: disable=too-many-public-methods
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
		self._auditHardwareConfigFile = '/etc/opsi/hwaudit/opsihwaudit.conf'
		self._auditHardwareConfigLocalesDir = '/etc/opsi/hwaudit/locales'
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
				logger.info('Logsize limited to: %s', self._maxLogfileSize)

		if not self._depotId:
			self._depotId = getfqdn()
		self._depotId = forceHostId(self._depotId)

	def _testFilterAndAttributes(self, Class, attributes, **filter):  # pylint: disable=redefined-builtin,invalid-name,no-self-use
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

		This can be something like creating a directory structure to setting up a database.
		"""

	def backend_deleteBase(self):
		"""
		Deleting the base of the backend.

		This is the place to undo all the things that were created by \
*backend_createBase*.
		"""

	def backend_getSystemConfiguration(self):  # pylint: disable=no-self-use
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
				"types": list(LOG_TYPES)
			}
		}

	def getOpsiCACert(self) -> str:  # pylint: disable=invalid-name,no-self-use
		return None

	def _get_client_info(self):
		return {
			"macos": 0,
			"linux": 0,
			"windows": len(self.host_getObjects(attributes=['id'], type='OpsiClient'))
		}

	def backend_getOpsiLicensingInfo(
		self,
		licenses: bool = False,
		legacy_modules: bool = False,
		dates: bool = False
	):
		"""
		Returns opsi licensing information.
		"""
		pool = get_default_opsi_license_pool(
			license_file_path=self._opsi_license_path,
			modules_file_path=self._opsiModulesFile,
			client_info=self._get_client_info
		)
		info = {
			"client_numbers": pool.client_numbers,
			"available_modules": [
				module_id for module_id, info in pool.get_modules().items() if info["available"]
			]
		}
		if licenses:
			licenses = pool.get_licenses()
			info["licenses"] = [ lic.to_dict(serializable=True, with_state=True) for lic in licenses ]
		if legacy_modules:
			info["legacy_modules"] = pool.get_legacy_modules()
		if dates:
			info["dates"] = {}
			for at_date in pool.get_relevant_dates():
				info["dates"][str(at_date)] = {
					"modules": pool.get_modules(at_date=at_date)
				}
		return info

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
			raise BackendBadValueError("Unknown log type '%s'" % logType)

		if not objectId:
			raise BackendBadValueError("Writing {0} log requires an objectId".format(logType))
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
				amountToReadFromLog = max(self._maxLogfileSize - len(data), 0)
				if 0 <= amountToReadFromLog < currentLogSize:
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

	def log_read(self, logType, objectId=None, maxSize=0):  # pylint: disable=no-self-use
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
			raise BackendBadValueError('Unknown log type {0!r}'.format(logType))

		if objectId:
			objectId = forceObjectId(objectId)
			logFile = os.path.join(LOG_DIR, logType, '{0}.log'.format(objectId))
		else:
			if LOG_TYPES[logType]:
				raise BackendBadValueError("Log type {0!r} requires objectId".format(logType))

			logFile = os.path.join(LOG_DIR, logType, 'opsiconfd.log')

		try:
			with codecs.open(logFile, 'r', 'utf-8', 'replace') as log:
				data = log.read()
		except IOError as ioerr:
			if ioerr.errno == 2:  # This is "No such file or directory"
				return ''

			raise

		if len(data) > maxSize > 0:
			return truncateLogData(data, maxSize)

		return data

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Users                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def user_getCredentials(self, username='pcpatch', hostId=None):
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

		result = {'password': '', 'rsaPrivateKey': ''}

		cf = ConfigFile(filename=self._opsiPasswdFile)
		for line in cf.parse():
			match = _PASSWD_LINE_REGEX.search(line)
			if match is None:
				continue

			if match.group(1) == username:
				result['password'] = match.group(2)
				break

		if not result['password']:
			raise BackendMissingDataError("Username '%s' not found in '%s'" % (username, self._opsiPasswdFile))

		depot = self.host_getObjects(id=self._depotId)
		if not depot:
			raise BackendMissingDataError("Depot {0!r} not found in backend".format(self._depotId))
		depot = depot[0]
		if not depot.opsiHostKey:
			raise BackendMissingDataError("Host key for depot {0!r} not found".format(self._depotId))

		result['password'] = blowfishDecrypt(depot.opsiHostKey, result['password'])

		if username == 'pcpatch':
			try:
				import pwd  # pylint: disable=import-outside-toplevel
				idRsa = os.path.join(pwd.getpwnam(username)[5], '.ssh', 'id_rsa')
				with open(idRsa, 'r') as file:
					result['rsaPrivateKey'] = file.read()
			except Exception as err:  # pylint: disable=broad-except
				logger.debug(err)

		if hostId:
			host = self._context.host_getObjects(id=hostId)
			try:
				host = host[0]
			except IndexError as err:
				raise BackendMissingDataError(f"Host '{hostId}' not found in backend") from err

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
		secret_filter.add_secrets(password)

		if '"' in password:
			raise ValueError("Character '\"' not allowed in password")

		try:
			depot = self._context.host_getObjects(id=self._depotId)
			depot = depot[0]
		except IndexError as err:
			raise BackendMissingDataError(f"Depot {self._depotId} not found in backend {self._context}") from err

		encodedPassword = blowfishEncrypt(depot.opsiHostKey, password)

		cf = ConfigFile(filename=self._opsiPasswdFile)
		lines = []
		try:
			for line in cf.readlines():
				match = _PASSWD_LINE_REGEX.search(line)
				if not match or match.group(1) != username:
					lines.append(line.rstrip())
		except FileNotFoundError:
			pass

		lines.append(f'{username}:{encodedPassword}')
		cf.open('w')
		cf.writelines(lines)
		cf.close()

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Hosts                                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def host_insertObject(self, host):  # pylint: disable=no-self-use
		host = forceObjectClass(host, Host)
		host.setDefaults()

	def host_updateObject(self, host):  # pylint: disable=no-self-use
		host = forceObjectClass(host, Host)

	def host_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.host_getObjects(attributes, **filter)]

	def host_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(Host, attributes, **filter)
		return []

	def host_deleteObjects(self, hosts):
		for host in forceObjectClassList(hosts, Host):
			# Remove from groups
			self._context.objectToGroup_deleteObjects(
				self._context.objectToGroup_getObjects(
					groupType='HostGroup',
					objectId=host.id
				)
			)

			if isinstance(host, OpsiClient):
				# Remove product states
				self._context.productOnClient_deleteObjects(
					self._context.productOnClient_getObjects(clientId=host.id)
				)
			elif isinstance(host, OpsiDepotserver):
				# This is also true for OpsiConfigservers
				# Remove products
				self._context.productOnDepot_deleteObjects(
					self._context.productOnDepot_getObjects(depotId=host.id)
				)
			# Remove product property states
			self._context.productPropertyState_deleteObjects(
				self._context.productPropertyState_getObjects(objectId=host.id)
			)
			# Remove config states
			self._context.configState_deleteObjects(
				self._context.configState_getObjects(objectId=host.id)
			)

			if isinstance(host, OpsiClient):
				# Remove audit softwares
				self._context.auditSoftwareOnClient_deleteObjects(
					self._context.auditSoftwareOnClient_getObjects(
						clientId=host.id
					)
				)

			# Remove audit hardwares
			self._context.auditHardwareOnHost_deleteObjects(
				self._context.auditHardwareOnHost_getObjects(hostId=host.id)
			)

			if isinstance(host, OpsiClient):
				# Free software licenses
				self._context.licenseOnClient_deleteObjects(
					self._context.licenseOnClient_getObjects(clientId=host.id)
				)

				softwareLicenses = self._context.softwareLicense_getObjects(boundToHost=host.id)
				softwareLicenses = softwareLicenses or []
				for softwareLicense in softwareLicenses:
					softwareLicense.boundToHost = None
					self._context.softwareLicense_insertObject(softwareLicense)

	def host_getTLSCertificate(self, hostId: str) -> str:  # pylint: disable=invalid-name,unused-argument,no-self-use
		return None

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Configs                                                                                   -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def config_insertObject(self, config):  # pylint: disable=no-self-use
		config = forceObjectClass(config, Config)
		config.setDefaults()

	def config_updateObject(self, config):  # pylint: disable=no-self-use
		config = forceObjectClass(config, Config)

	def config_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.config_getObjects(attributes, **filter)]

	def config_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(Config, attributes, **filter)
		return []

	def config_deleteObjects(self, configs):
		ids = [config.id for config in forceObjectClassList(configs, Config)]

		if ids:
			self._context.configState_deleteObjects(
				self._context.configState_getObjects(
					configId=ids,
					objectId=[]
				)
			)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ConfigStates                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def configState_insertObject(self, configState):
		configState = forceObjectClass(configState, ConfigState)
		configState.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			configIds = [config.id for config in self._context.config_getObjects(attributes=['id'])]

			if configState.configId not in configIds:
				raise BackendReferentialIntegrityError("Config with id '%s' not found" % configState.configId)

	def configState_updateObject(self, configState):  # pylint: disable=no-self-use
		configState = forceObjectClass(configState, ConfigState)

	def configState_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.configState_getObjects(attributes, **filter)]

	def configState_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ConfigState, attributes, **filter)
		return []

	def configState_deleteObjects(self, configStates):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Products                                                                                  -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def product_insertObject(self, product):  # pylint: disable=no-self-use
		product = forceObjectClass(product, Product)
		product.setDefaults()

	def product_updateObject(self, product):  # pylint: disable=no-self-use
		product = forceObjectClass(product, Product)

	def product_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.product_getObjects(attributes, **filter)]

	def product_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(Product, attributes, **filter)
		return []

	def product_deleteObjects(self, products):
		productByIdAndVersion = collections.defaultdict(lambda: collections.defaultdict(list))
		for product in forceObjectClassList(products, Product):
			productByIdAndVersion[product.id][product.productVersion].append(product.packageVersion)

			self._context.productProperty_deleteObjects(
				self._context.productProperty_getObjects(
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)
			self._context.productDependency_deleteObjects(
				self._context.productDependency_getObjects(
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)
			self._context.productOnDepot_deleteObjects(
				self._context.productOnDepot_getObjects(
					productId=product.id,
					productVersion=product.productVersion,
					packageVersion=product.packageVersion
				)
			)

		for (productId, versions) in productByIdAndVersion.items():
			allProductVersWillBeDeleted = True
			for product in self._context.product_getObjects(attributes=['id', 'productVersion', 'packageVersion'], id=productId):
				if product.packageVersion not in versions.get(product.productVersion, []):
					allProductVersWillBeDeleted = False
					break

			if not allProductVersWillBeDeleted:
				continue

			# Remove from groups, when allProductVerionsWillBeDelted
			self._context.objectToGroup_deleteObjects(
				self._context.objectToGroup_getObjects(
					groupType='ProductGroup',
					objectId=productId
				)
			)
			self._context.productOnClient_deleteObjects(
				self._context.productOnClient_getObjects(productId=productId)
			)
			self._context.productPropertyState_deleteObjects(
				self._context.productPropertyState_getObjects(productId=productId)
			)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductProperties                                                                         -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productProperty_insertObject(self, productProperty):
		productProperty = forceObjectClass(productProperty, ProductProperty)
		productProperty.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(
					attributes=['id', 'productVersion', 'packageVersion'],
					id=productProperty.productId,
					productVersion=productProperty.productVersion,
					packageVersion=productProperty.packageVersion):

				raise BackendReferentialIntegrityError(
					"Product with id '{0}', productVersion '{1}', "
					"packageVersion '{2}' not found".format(
						productProperty.productId,
						productProperty.productVersion,
						productProperty.packageVersion
					)
				)

	def productProperty_updateObject(self, productProperty):  # pylint: disable=no-self-use
		productProperty = forceObjectClass(productProperty, ProductProperty)

	def productProperty_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.productProperty_getObjects(attributes, **filter)]

	def productProperty_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ProductProperty, attributes, **filter)
		return []

	def productProperty_deleteObjects(self, productProperties):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductDependencies                                                                       -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productDependency_insertObject(self, productDependency):
		productDependency = forceObjectClass(productDependency, ProductDependency)
		productDependency.setDefaults()
		if not productDependency.getRequiredAction() and not productDependency.getRequiredInstallationStatus():
			raise BackendBadValueError("Either a required action or a required installation status must be given")
		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(
					attributes=['id', 'productVersion', 'packageVersion'],
					id=productDependency.productId,
					productVersion=productDependency.productVersion,
					packageVersion=productDependency.packageVersion):

				raise BackendReferentialIntegrityError(
					"Product with id '{0}', productVersion '{1}', "
					"packageVersion '{2}' not found".format(
						productDependency.productId,
						productDependency.productVersion,
						productDependency.packageVersion
					)
				)

	def productDependency_updateObject(self, productDependency):  # pylint: disable=no-self-use
		productDependency = forceObjectClass(productDependency, ProductDependency)

	def productDependency_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.productDependency_getObjects(attributes, **filter)]

	def productDependency_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ProductDependency, attributes, **filter)
		return []

	def productDependency_deleteObjects(self, productDependencies):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnDepots                                                                           -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnDepot_insertObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)
		productOnDepot.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(
				attributes=['id', 'productVersion', 'packageVersion'],
				id=productOnDepot.productId,
				productVersion=productOnDepot.productVersion,
				packageVersion=productOnDepot.packageVersion):

				raise BackendReferentialIntegrityError(
					"Product with id '{0}', productVersion '{1}', "
					"packageVersion '{2}' not found".format(
						productOnDepot.productId,
						productOnDepot.productVersion,
						productOnDepot.packageVersion
					)
				)

	def productOnDepot_updateObject(self, productOnDepot):
		productOnDepot = forceObjectClass(productOnDepot, ProductOnDepot)

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.product_getObjects(
				attributes=['id', 'productVersion', 'packageVersion'],
				id=productOnDepot.productId,
				productVersion=productOnDepot.productVersion,
				packageVersion=productOnDepot.packageVersion):

				raise BackendReferentialIntegrityError(
					"Product with id '{0}', productVersion '{1}', "
					"packageVersion '{2}' not found".format(
						productOnDepot.productId,
						productOnDepot.productVersion,
						productOnDepot.packageVersion
					)
				)

	def productOnDepot_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.productOnDepot_getObjects(attributes, **filter)]

	def productOnDepot_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ProductOnDepot, attributes, **filter)
		return []

	def productOnDepot_deleteObjects(self, productOnDepots):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productOnClient_insertObject(self, productOnClient):  # pylint: disable=no-self-use
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)
		productOnClient.setDefaults()

		if (productOnClient.installationStatus == 'installed') and (not productOnClient.productVersion or not productOnClient.packageVersion):
			raise BackendReferentialIntegrityError(
				f"Cannot set installationStatus for product '{productOnClient.productId}'"
				f", client '{productOnClient.clientId}' to 'installed' without productVersion and packageVersion"
			)

		if productOnClient.installationStatus != 'installed':
			productOnClient.productVersion = None
			productOnClient.packageVersion = None

	def productOnClient_updateObject(self, productOnClient):  # pylint: disable=no-self-use
		productOnClient = forceObjectClass(productOnClient, ProductOnClient)

	def productOnClient_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.productOnClient_getObjects(attributes, **filter)]

	def productOnClient_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ProductOnClient, attributes, **filter)
		return []

	def productOnClient_deleteObjects(self, productOnClients):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   ProductPropertyStates                                                                     -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def productPropertyState_insertObject(self, productPropertyState):
		productPropertyState = forceObjectClass(productPropertyState, ProductPropertyState)
		productPropertyState.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.productProperty_getObjects(
				attributes=['productId', 'propertyId'],
				productId=productPropertyState.productId,
				propertyId=productPropertyState.propertyId):

				raise BackendReferentialIntegrityError("ProductProperty with id '%s' for product '%s' not found"
					% (productPropertyState.propertyId, productPropertyState.productId))

	def productPropertyState_updateObject(self, productPropertyState):  # pylint: disable=no-self-use
		productPropertyState = forceObjectClass(productPropertyState, ProductPropertyState)

	def productPropertyState_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.productPropertyState_getObjects(attributes, **filter)]

	def productPropertyState_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ProductPropertyState, attributes, **filter)
		return []

	def productPropertyState_deleteObjects(self, productPropertyStates):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   Groups                                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def group_insertObject(self, group):
		group = forceObjectClass(group, Group)
		group.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			if group.parentGroupId and not self._context.group_getObjects(attributes=['id'], id=group.parentGroupId):
				raise BackendReferentialIntegrityError("Parent group '%s' of group '%s' not found" % (group.parentGroupId, group.id))

	def group_updateObject(self, group):  # pylint: disable=no-self-use
		group = forceObjectClass(group, Group)

	def group_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.group_getObjects(attributes, **filter)]

	def group_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
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
	def objectToGroup_insertObject(self, objectToGroup):  # pylint: disable=no-self-use
		objectToGroup = forceObjectClass(objectToGroup, ObjectToGroup)
		objectToGroup.setDefaults()

	def objectToGroup_updateObject(self, objectToGroup):  # pylint: disable=no-self-use
		objectToGroup = forceObjectClass(objectToGroup, ObjectToGroup)

	def objectToGroup_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.objectToGroup_getObjects(attributes, **filter)]

	def objectToGroup_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(ObjectToGroup, attributes, **filter)
		return []

	def objectToGroup_deleteObjects(self, objectToGroups):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseContracts                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseContract_insertObject(self, licenseContract):  # pylint: disable=no-self-use
		licenseContract = forceObjectClass(licenseContract, LicenseContract)
		licenseContract.setDefaults()

	def licenseContract_updateObject(self, licenseContract):  # pylint: disable=no-self-use
		licenseContract = forceObjectClass(licenseContract, LicenseContract)

	def licenseContract_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.licenseContract_getObjects(attributes, **filter)]

	def licenseContract_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(LicenseContract, attributes, **filter)
		return []

	def licenseContract_deleteObjects(self, licenseContracts):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   SoftwareLicenses                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def softwareLicense_insertObject(self, softwareLicense):
		softwareLicense = forceObjectClass(softwareLicense, SoftwareLicense)
		softwareLicense.setDefaults()
		if not softwareLicense.licenseContractId:
			raise BackendBadValueError("License contract missing")

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.licenseContract_getObjects(attributes=['id'], id=softwareLicense.licenseContractId):
				raise BackendReferentialIntegrityError("License contract with id '%s' not found" % softwareLicense.licenseContractId)

	def softwareLicense_updateObject(self, softwareLicense):  # pylint: disable=no-self-use
		softwareLicense = forceObjectClass(softwareLicense, SoftwareLicense)

	def softwareLicense_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.softwareLicense_getObjects(attributes, **filter)]

	def softwareLicense_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(SoftwareLicense, attributes, **filter)
		return []

	def softwareLicense_deleteObjects(self, softwareLicenses):
		softwareLicenseIds = [softwareLicense.id for softwareLicense in forceObjectClassList(softwareLicenses, SoftwareLicense)]

		self._context.softwareLicenseToLicensePool_deleteObjects(
			self._context.softwareLicenseToLicensePool_getObjects(
				softwareLicenseId=softwareLicenseIds
			)
		)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicensePools                                                                              -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licensePool_insertObject(self, licensePool):  # pylint: disable=no-self-use
		licensePool = forceObjectClass(licensePool, LicensePool)
		licensePool.setDefaults()

	def licensePool_updateObject(self, licensePool):  # pylint: disable=no-self-use
		licensePool = forceObjectClass(licensePool, LicensePool)

	def licensePool_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.licensePool_getObjects(attributes, **filter)]

	def licensePool_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(LicensePool, attributes, **filter)
		return []

	def licensePool_deleteObjects(self, licensePools):
		licensePoolIds = [licensePool.id for licensePool in forceObjectClassList(licensePools, LicensePool)]

		if licensePoolIds:
			softwareLicenseToLicensePools = self._context.softwareLicenseToLicensePool_getObjects(licensePoolId=licensePoolIds)
			if softwareLicenseToLicensePools:
				raise BackendReferentialIntegrityError("Refusing to delete license pool(s) %s, one ore more licenses/keys refer to pool: %s" % \
					(licensePoolIds, softwareLicenseToLicensePools))

			self._context.auditSoftwareToLicensePool_deleteObjects(
				self._context.auditSoftwareToLicensePool_getObjects(
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
		softwareLicenseToLicensePool.setDefaults()

		if self._options['additionalReferentialIntegrityChecks']:
			if not self._context.softwareLicense_getObjects(attributes=['id'], id=softwareLicenseToLicensePool.softwareLicenseId):
				raise BackendReferentialIntegrityError("Software license with id '%s' not found" % softwareLicenseToLicensePool.softwareLicenseId)
			if not self._context.licensePool_getObjects(attributes=['id'], id=softwareLicenseToLicensePool.licensePoolId):
				raise BackendReferentialIntegrityError("License with id '%s' not found" % softwareLicenseToLicensePool.licensePoolId)

	def softwareLicenseToLicensePool_updateObject(self, softwareLicenseToLicensePool):  # pylint: disable=no-self-use
		softwareLicenseToLicensePool = forceObjectClass(softwareLicenseToLicensePool, SoftwareLicenseToLicensePool)

	def softwareLicenseToLicensePool_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.softwareLicenseToLicensePool_getObjects(attributes, **filter)]

	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(SoftwareLicenseToLicensePool, attributes, **filter)
		return []

	def softwareLicenseToLicensePool_deleteObjects(self, softwareLicenseToLicensePools):
		softwareLicenseIds = [
			softwareLicenseToLicensePool.softwareLicenseId for
			softwareLicenseToLicensePool in forceObjectClassList(softwareLicenseToLicensePools, SoftwareLicenseToLicensePool)
		]

		if softwareLicenseIds:
			licenseOnClients = self._context.licenseOnClient_getObjects(softwareLicenseId=softwareLicenseIds)
			if licenseOnClients:
				raise BackendReferentialIntegrityError("Refusing to delete softwareLicenseToLicensePool(s), one ore more licenses in use: %s"\
					% licenseOnClients)

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   LicenseOnClients                                                                          -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def licenseOnClient_insertObject(self, licenseOnClient):  # pylint: disable=no-self-use
		licenseOnClient = forceObjectClass(licenseOnClient, LicenseOnClient)
		licenseOnClient.setDefaults()

	def licenseOnClient_updateObject(self, licenseOnClient):  # pylint: disable=no-self-use
		licenseOnClient = forceObjectClass(licenseOnClient, LicenseOnClient)

	def licenseOnClient_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.licenseOnClient_getObjects(attributes, **filter)]

	def licenseOnClient_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(LicenseOnClient, attributes, **filter)
		return []

	def licenseOnClient_deleteObjects(self, licenseOnClients):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftware_insertObject(self, auditSoftware):  # pylint: disable=no-self-use
		auditSoftware = forceObjectClass(auditSoftware, AuditSoftware)
		auditSoftware.setDefaults()

	def auditSoftware_updateObject(self, auditSoftware):  # pylint: disable=no-self-use
		auditSoftware = forceObjectClass(auditSoftware, AuditSoftware)

	def auditSoftware_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.auditSoftware_getObjects(attributes, **filter)]

	def auditSoftware_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(AuditSoftware, attributes, **filter)
		return []

	def auditSoftware_deleteObjects(self, auditSoftwares):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareToLicensePools                                                               -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareToLicensePool_insertObject(self, auditSoftwareToLicensePool):  # pylint: disable=no-self-use
		auditSoftwareToLicensePool = forceObjectClass(auditSoftwareToLicensePool, AuditSoftwareToLicensePool)
		auditSoftwareToLicensePool.setDefaults()

	def auditSoftwareToLicensePool_updateObject(self, auditSoftwareToLicensePool):  # pylint: disable=no-self-use
		auditSoftwareToLicensePool = forceObjectClass(auditSoftwareToLicensePool, AuditSoftwareToLicensePool)

	def auditSoftwareToLicensePool_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.auditSoftwareToLicensePool_getObjects(attributes, **filter)]

	def auditSoftwareToLicensePool_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(AuditSoftwareToLicensePool, attributes, **filter)
		return []

	def auditSoftwareToLicensePool_deleteObjects(self, auditSoftwareToLicensePools):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditSoftwareOnClients                                                                    -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditSoftwareOnClient_insertObject(self, auditSoftwareOnClient):  # pylint: disable=no-self-use
		auditSoftwareOnClient = forceObjectClass(auditSoftwareOnClient, AuditSoftwareOnClient)
		auditSoftwareOnClient.setDefaults()

	def auditSoftwareOnClient_updateObject(self, auditSoftwareOnClient):  # pylint: disable=no-self-use
		auditSoftwareOnClient = forceObjectClass(auditSoftwareOnClient, AuditSoftwareOnClient)

	def auditSoftwareOnClient_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.auditSoftwareOnClient_getObjects(attributes, **filter)]

	def auditSoftwareOnClient_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		self._testFilterAndAttributes(AuditSoftwareOnClient, attributes, **filter)
		return []

	def auditSoftwareOnClient_deleteObjects(self, auditSoftwareOnClients):
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwares                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardware_insertObject(self, auditHardware):  # pylint: disable=no-self-use
		auditHardware = forceObjectClass(auditHardware, AuditHardware)
		auditHardware.setDefaults()

	def auditHardware_updateObject(self, auditHardware):  # pylint: disable=no-self-use
		auditHardware = forceObjectClass(auditHardware, AuditHardware)

	def auditHardware_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.auditHardware_getObjects(attributes, **filter)]

	def auditHardware_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value,unused-argument,no-self-use
		return []

	def auditHardware_deleteObjects(self, auditHardwares):  # pylint: disable=no-self-use
		pass

	def auditHardware_getConfig(self, language=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		if self._auditHardwareConfigFile.endswith('.json'):
			try:
				with codecs.open(self._auditHardwareConfigFile, 'r', 'utf8') as file:
					return json.loads(file.read())
			except Exception as err:  # pylint: disable=broad-except
				logger.warning("Failed to read audit hardware configuration from file '%s': %s", self._auditHardwareConfigFile, err)
				return []

		if not language:
			language = 'en_US'
		language = forceLanguageCode(language).replace('-', '_')

		localeFile = os.path.join(self._auditHardwareConfigLocalesDir, language)
		if not os.path.exists(localeFile):
			logger.error("No translation file found for language %s, falling back to en_US", language)
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
					logger.trace("Failed to read translation: %s", verr)
			del lf
		except Exception as err:  # pylint: disable=broad-except
			logger.error("Failed to read translation file for language %s: %s", language, err)

		def __inheritFromSuperClasses(classes, _class, scname=None):  # pylint: disable=unused-private-member
			if not scname:  # pylint: disable=too-many-nested-blocks
				for _scname in _class['Class'].get('Super', []):
					__inheritFromSuperClasses(classes, _class, _scname)
			else:
				for cl in classes:
					if cl['Class'].get('Opsi') == scname:
						clcopy = pycopy.deepcopy(cl)
						__inheritFromSuperClasses(classes, clcopy)
						newValues = []
						for newValue in clcopy['Values']:
							foundAt = -1
							for i, currentValue in enumerate(_class['Values']):
								if currentValue['Opsi'] == newValue['Opsi']:
									if not currentValue.get('UI'):
										_class['Values'][i]['UI'] = newValue.get('UI', '')
									foundAt = i
									break
							if foundAt > -1:
								newValue = _class['Values'][foundAt]
								del _class['Values'][foundAt]
							newValues.append(newValue)
						newValues.extend(_class['Values'])
						_class['Values'] = newValues
						break
				else:
					logger.error("Super class '%s' of class '%s' not found", scname, _class['Class'].get('Opsi'))

		classes = []
		try:  # pylint: disable=too-many-nested-blocks
			with open(self._auditHardwareConfigFile) as hwcFile:
				exec(hwcFile.read())  # pylint: disable=exec-used

			for i, currentClassConfig in enumerate(OPSI_HARDWARE_CLASSES):
				opsiClass = currentClassConfig['Class']['Opsi']
				if currentClassConfig['Class']['Type'] == 'STRUCTURAL':
					if locale.get(opsiClass):
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = locale[opsiClass]
					else:
						logger.error("No translation for class '%s' found", opsiClass)
						OPSI_HARDWARE_CLASSES[i]['Class']['UI'] = opsiClass

				for j, currentValue in enumerate(currentClassConfig['Values']):
					opsiProperty = currentValue['Opsi']
					try:
						OPSI_HARDWARE_CLASSES[i]['Values'][j]['UI'] = locale[opsiClass + '.' + opsiProperty]
					except KeyError:
						pass

			for owc in OPSI_HARDWARE_CLASSES:
				try:
					if owc['Class'].get('Type') == 'STRUCTURAL':
						logger.debug("Found STRUCTURAL hardware class '%s'", owc['Class'].get('Opsi'))
						ccopy = pycopy.deepcopy(owc)
						if 'Super' in ccopy['Class']:
							__inheritFromSuperClasses(OPSI_HARDWARE_CLASSES, ccopy)
							del ccopy['Class']['Super']
						del ccopy['Class']['Type']

						# Fill up empty display names
						for j, currentValue in enumerate(ccopy.get('Values', [])):
							if not currentValue.get('UI'):
								logger.warning("No translation found for hardware audit configuration property '%s.%s' in %s",
									ccopy['Class']['Opsi'], currentValue['Opsi'], localeFile
								)
								ccopy['Values'][j]['UI'] = currentValue['Opsi']

						classes.append(ccopy)
				except Exception as err:  # pylint: disable=broad-except
					logger.error("Error in config file '%s': %s", self._auditHardwareConfigFile, err)
		except Exception as err:  # pylint: disable=broad-except
			logger.warning("Failed to read audit hardware configuration from file '%s': %s", self._auditHardwareConfigFile, err)

		return classes

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   AuditHardwareOnHosts                                                                      -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def auditHardwareOnHost_insertObject(self, auditHardwareOnHost):
		auditHardwareOnHost = forceObjectClass(auditHardwareOnHost, AuditHardwareOnHost)
		auditHardwareOnHost.setDefaults()
		self._context.auditHardware_insertObject(AuditHardware.fromHash(auditHardwareOnHost.toHash()))

	def auditHardwareOnHost_updateObject(self, auditHardwareOnHost):  # pylint: disable=no-self-use
		auditHardwareOnHost = forceObjectClass(auditHardwareOnHost, AuditHardwareOnHost)

	def auditHardwareOnHost_getHashes(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value
		return [obj.toHash() for obj in self.auditHardwareOnHost_getObjects(attributes, **filter)]

	def auditHardwareOnHost_getObjects(self, attributes=[], **filter):  # pylint: disable=redefined-builtin,dangerous-default-value,unused-argument,no-self-use
		return []

	def auditHardwareOnHost_deleteObjects(self, auditHardwareOnHosts):  # pylint: disable=no-self-use
		pass

	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	# -   direct access                                                                            -
	# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
	def getData(self, query):  # pylint: disable=no-self-use
		return query

	def getRawData(self, query):  # pylint: disable=no-self-use
		return query
