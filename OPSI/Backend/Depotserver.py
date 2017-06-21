# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2017 uib GmbH <info@uib.de>

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
Depotserver backend.

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os

from OPSI.Exceptions import (BackendBadValueError, BackendConfigurationError,
	BackendError, BackendIOError, BackendMissingDataError,
	BackendTemporaryError, BackendUnaccomplishableError)
from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Types import (forceBool, forceDict, forceFilename, forceHostId,
	forceUnicode, forceUnicodeLower)
from OPSI.Types import forceProductId as forceProductIdFunc
from OPSI.Object import ProductOnDepot, ProductPropertyState
from OPSI.Backend.Backend import LOG_DIR, OPSI_GLOBAL_CONF, ExtendedBackend
from OPSI.System import getDiskSpaceUsage
from OPSI.Util.Product import ProductPackageFile
from OPSI.Util import (compareVersions, getfqdn, md5sum, librsyncSignature,
	librsyncPatchFile, librsyncDeltaFile, removeDirectory)
from OPSI.Util.File import ZsyncFile

__all__ = ('DepotserverBackend', 'DepotserverPackageManager')

logger = Logger()


class DepotserverBackend(ExtendedBackend):
	def __init__(self, backend, **kwargs):
		self._name = 'depotserver'

		ExtendedBackend.__init__(self, backend)

		self._packageLog = os.path.join(LOG_DIR, 'package.log')
		self._sshRSAPublicKeyFile = u'/etc/ssh/ssh_host_rsa_key.pub'

		self._depotId = forceHostId(getfqdn(conf=OPSI_GLOBAL_CONF))
		if not self._context.host_getIdents(id=self._depotId):  # pylint: disable=maybe-no-member
			raise BackendMissingDataError(u"Depot '%s' not found in backend" % self._depotId)
		self._packageManager = DepotserverPackageManager(self)

	def depot_getHostRSAPublicKey(self):
		with open(self._sshRSAPublicKeyFile, 'r') as publicKey:
			return forceUnicode(publicKey.read())

	def depot_getMD5Sum(self, filename, forceCalculation=False):
		checksum = None
		try:
			if not forceBool(forceCalculation):
				hashFile = filename + '.md5'

				try:
					with open(hashFile) as fileHandle:
						checksum = fileHandle.read()

					logger.info(u"Using pre-calculated MD5sum from '{0}'.", hashFile)
				except (OSError, IOError):
					pass

			if not checksum:
				checksum = md5sum(filename)

			logger.info(u"MD5sum of file '{0}' is '{1}'", filename, checksum)
			return checksum
		except Exception as error:
			raise BackendIOError(u"Failed to get md5sum: %s" % error)

	def depot_librsyncSignature(self, filename):
		try:
			return librsyncSignature(filename)
		except Exception as e:
			raise BackendIOError(u"Failed to get librsync signature: %s" % e)

	def depot_librsyncPatchFile(self, oldfile, deltafile, newfile):
		try:
			return librsyncPatchFile(oldfile, deltafile, newfile)
		except Exception as e:
			raise BackendIOError(u"Failed to patch file: %s" % e)

	def depot_librsyncDeltaFile(self, filename, signature, deltafile):
		try:
			librsyncDeltaFile(filename, signature, deltafile)
		except Exception as e:
			raise BackendIOError(u"Failed to create librsync delta file: %s" % e)

	def depot_getDiskSpaceUsage(self, path):
		if os.name != 'posix':
			raise NotImplementedError(u"Not implemented for non-posix os")

		try:
			return getDiskSpaceUsage(path)
		except Exception as e:
			raise BackendIOError(u"Failed to get disk space usage: %s" % e)

	def depot_installPackage(self, filename, force=False, propertyDefaultValues={}, tempDir=None, forceProductId=None, suppressPackageContentFileGeneration=False):
		self._packageManager.installPackage(filename,
			force=force, propertyDefaultValues=propertyDefaultValues,
			tempDir=tempDir, forceProductId=forceProductId,
			suppressPackageContentFileGeneration=suppressPackageContentFileGeneration
		)

	def depot_uninstallPackage(self, productId, force=False, deleteFiles=True):
		self._packageManager.uninstallPackage(productId, force, deleteFiles)

	def depot_createMd5SumFile(self, filename, md5sumFilename):
		if not os.path.exists(filename):
			raise BackendIOError(u"File not found: %s" % filename)
		logger.info(u"Creating md5sum file '%s'" % md5sumFilename)
		md5 = md5sum(filename)
		with open(md5sumFilename, 'w') as md5file:
			md5file.write(md5)

	def depot_createZsyncFile(self, filename, zsyncFilename):
		if not os.path.exists(filename):
			raise BackendIOError(u"File not found: %s" % filename)
		logger.info(u"Creating zsync file '%s'" % zsyncFilename)
		zsyncFile = ZsyncFile(zsyncFilename)
		zsyncFile.generate(filename)


class DepotserverPackageManager(object):
	def __init__(self, depotBackend):
		if not isinstance(depotBackend, DepotserverBackend):
			raise BackendConfigurationError(u"DepotserverPackageManager needs instance of DepotserverBackend as backend, got %s" % depotBackend.__class__.__name__)
		self._depotBackend = depotBackend
		logger.setLogFile(self._depotBackend._packageLog, object=self)

	def installPackage(self, filename, force=False, propertyDefaultValues={}, tempDir=None, forceProductId=None, suppressPackageContentFileGeneration=False):
		depotId = self._depotBackend._depotId
		logger.info(u"=================================================================================================")
		if forceProductId:
			forceProductId = forceProductIdFunc(forceProductId)
			logger.notice(u"Installing package file '{filename}' as '{productId}' on depot '{depotId}'",
				filename=filename, depotId=depotId, productId=forceProductId
			)
		else:
			logger.notice(u"Installing package file '%s' on depot '%s'" % (filename, depotId))

		try:
			filename = forceFilename(filename)
			force = forceBool(force)
			propertyDefaultValues = forceDict(propertyDefaultValues)
			for propertyId in propertyDefaultValues:
				if propertyDefaultValues[propertyId] is None:
					propertyDefaultValues[propertyId] = []

			if tempDir:
				tempDir = forceFilename(tempDir)
			else:
				tempDir = None

			if not os.path.isfile(filename):
				raise BackendIOError(u"Package file '{0}' does not exist or can not be accessed.".format(filename))
			if not os.access(filename, os.R_OK):
				raise BackendIOError(u"Read access denied for package file '%s'" % filename)

			depots = self._depotBackend._context.host_getObjects(id=depotId)
			if not depots:
				raise BackendMissingDataError(u"Depot '%s' not found in backend" % depotId)
			depot = depots[0]

			depotLocalUrl = depot.getDepotLocalUrl()
			if not depotLocalUrl.startswith(u'file:///'):
				raise BackendBadValueError(u"Value '%s' not allowed for depot local url (has to start with 'file:///')" % depotLocalUrl)
			clientDataDir = depotLocalUrl[7:]

			ppf = ProductPackageFile(filename, tempDir=tempDir)
			ppf.setClientDataDir(clientDataDir)
			ppf.getMetaData()

			try:
				product = ppf.packageControlFile.getProduct()
				if forceProductId:
					logger.info(u"Forcing product id '{0}'", forceProductId)
					product.setId(forceProductId)
					ppf.packageControlFile.setProduct(product)

				productId = product.getId()

				logger.info(u"Creating product in backend")
				self._depotBackend._context.product_createObjects(product)

				logger.notice(u"Locking product '%s' on depot '%s'" % (product.getId(), depotId))
				productOnDepot = ProductOnDepot(
					productId=productId,
					productType=product.getType(),
					productVersion=product.getProductVersion(),
					packageVersion=product.getPackageVersion(),
					depotId=depotId,
					locked=True
				)
				productOnDepots = self._depotBackend._context.productOnDepot_getObjects(depotId=depotId, productId=productId)
				if productOnDepots and productOnDepots[0].getLocked():
					logger.notice(u"Product currently locked on depot '%s'" % depotId)
					if not force:
						raise BackendTemporaryError(u"Product currently locked on depot '%s'" % depotId)
					logger.warning(u"Installation of locked product forced")
				logger.info(u"Creating product on depot %s" % productOnDepot)
				self._depotBackend._context.productOnDepot_createObjects(productOnDepot)

				logger.info(u"Checking package dependencies")
				self.checkDependencies(ppf)

				logger.info(u"Running preinst script")
				for line in ppf.runPreinst(({'DEPOT_ID': depotId})):
					logger.info(u"[preinst] {0}", line)

				logger.info(u"Deleting old client-data dir")
				ppf.deleteProductClientDataDir()

				logger.info(u"Unpacking package files")
				ppf.extractData()

				logger.info(u"Updating product dependencies of product %s" % product)
				currentProductDependencies = {}
				productDependencies = []
				for productDependency in self._depotBackend._context.productDependency_getObjects(
							productId=productId,
							productVersion=product.getProductVersion(),
							packageVersion=product.getPackageVersion()):
					ident = productDependency.getIdent(returnType='unicode')
					currentProductDependencies[ident] = productDependency

				for productDependency in ppf.packageControlFile.getProductDependencies():
					if forceProductId:
						productDependency.productId = productId

					ident = productDependency.getIdent(returnType='unicode')
					try:
						del currentProductDependencies[ident]
					except KeyError:
						pass  # Dependency does currently not exist.
					productDependencies.append(productDependency)

				self._depotBackend._context.productDependency_createObjects(productDependencies)
				if currentProductDependencies:
					self._depotBackend._context.productDependency_deleteObjects(
						currentProductDependencies.values()
					)

				logger.info(u"Updating product properties of product %s" % product)
				currentProductProperties = {}
				productProperties = []
				for productProperty in self._depotBackend._context.productProperty_getObjects(
							productId=productId,
							productVersion=product.getProductVersion(),
							packageVersion=product.getPackageVersion()):
					ident = productProperty.getIdent(returnType='unicode')
					currentProductProperties[ident] = productProperty

				for productProperty in ppf.packageControlFile.getProductProperties():
					if forceProductId:
						productProperty.productId = productId

					ident = productProperty.getIdent(returnType='unicode')
					try:
						del currentProductProperties[ident]
					except KeyError:
						pass  # Property not found - everyhing okay
					productProperties.append(productProperty)
				self._depotBackend._context.productProperty_createObjects(productProperties)

				for productProperty in productProperties:
					# Adjust property default values
					if productProperty.editable or not productProperty.possibleValues:
						continue
					newValues = []
					for v in propertyDefaultValues.get(productProperty.propertyId, []):
						if v in productProperty.possibleValues:
							newValues.append(v)

					if not newValues and productProperty.defaultValues:
						newValues = productProperty.defaultValues
					propertyDefaultValues[productProperty.propertyId] = newValues

				if currentProductProperties.values():
					self._depotBackend._context.productProperty_deleteObjects(
						currentProductProperties.values()
					)

				logger.info(u"Deleting product property states of product %s on depot '%s'" % (productId, depotId))
				self._depotBackend._context.productPropertyState_deleteObjects(
					self._depotBackend._context.productPropertyState_getObjects(
						productId=productId,
						objectId=depotId
					)
				)

				logger.info(u"Deleting not needed property states of product %s" % productId)
				productPropertyStates = self._depotBackend._context.productPropertyState_getObjects(productId=productId)
				baseProperties = self._depotBackend._context.productProperty_getObjects(productId=productId)

				productPropertyIds = None
				productPropertyStatesToDelete = None
				productPropertyIds = [productProperty.propertyId for productProperty in baseProperties]
				productPropertyStatesToDelete = [ppState for ppState in productPropertyStates if ppState.propertyId not in productPropertyIds]
				logger.debug(u"Following productPropertyStates are marked to delete: '%s'" % productPropertyStatesToDelete)
				if productPropertyStatesToDelete:
					self._depotBackend._context.productPropertyState_deleteObjects(productPropertyStatesToDelete)

				logger.info(u"Setting product property states in backend")
				productPropertyStates = []
				for productProperty in productProperties:
					productPropertyStates.append(
						ProductPropertyState(
							productId=productId,
							propertyId=productProperty.propertyId,
							objectId=depotId,
							values=productProperty.defaultValues
						)
					)

				for productPropertyState in productPropertyStates:
					if productPropertyState.propertyId in propertyDefaultValues:
						try:
							productPropertyState.setValues(propertyDefaultValues[productPropertyState.propertyId])
						except Exception as installationError:
							logger.error(u"Failed to set default values to %s for productPropertyState %s: %s" \
									% (propertyDefaultValues[productPropertyState.propertyId], productPropertyState, installationError) )
				self._depotBackend._context.productPropertyState_createObjects(productPropertyStates)

				logger.info(u"Running postinst script")
				for line in ppf.runPostinst({'DEPOT_ID': depotId}):
					logger.info(u"[postinst] {0}", line)

				if not suppressPackageContentFileGeneration:
					ppf.createPackageContentFile()
				else:
					logger.debug("Suppressed generation of package content file.")

				ppf.setAccessRights()
				ppf.cleanup()

				logger.notice(u"Unlocking product '%s_%s-%s' on depot '%s'" \
							% (productOnDepot.getProductId(), productOnDepot.getProductVersion(), productOnDepot.getPackageVersion(), depotId))
				productOnDepot.setLocked(False)
				self._depotBackend._context.productOnDepot_updateObject(productOnDepot)

				# Clean up products
				productIdents = set()
				for productOnDepot in self._depotBackend._context.productOnDepot_getObjects(productId=productOnDepot.productId):
					productIdent = u"%s;%s;%s" % (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion)
					productIdents.add(productIdent)

				deleteProducts = []
				for product in self._depotBackend._context.product_getObjects(id=productOnDepot.productId):
					if product.getIdent(returnType='unicode') not in productIdents:
						deleteProducts.append(product)

				if deleteProducts:
					self._depotBackend._context.product_deleteObjects(deleteProducts)

				# Clean up productPropertyStates
				productPropertiesToCleanup = {}
				for productProperty in productProperties:
					if productProperty.editable or not productProperty.possibleValues:
						continue
					productPropertiesToCleanup[productProperty.propertyId] = productProperty

				if productPropertiesToCleanup:
					clientIds = []
					for clientToDepot in self._depotBackend._context.configState_getClientToDepotserver(depotIds=depotId):
						if clientToDepot['clientId'] not in clientIds:
							clientIds.append(clientToDepot['clientId'])

					if clientIds:
						deleteProductPropertyStates = []
						updateProductPropertyStates = []
						for productPropertyState in self._depotBackend._context.productPropertyState_getObjects(
										objectId=clientIds,
										productId=productOnDepot.getProductId(),
										propertyId=productPropertiesToCleanup.keys()):
							changed = False
							newValues = []
							for v in productPropertyState.values:
								productProperty = productPropertiesToCleanup[productPropertyState.propertyId]
								if v in productProperty.possibleValues:
									newValues.append(v)
									continue

								if productProperty.getType() == 'BoolProductProperty' and forceBool(v) in productProperty.possibleValues:
									newValues.append(forceBool(v))
									changed = True
									continue
								elif productProperty.getType() == 'UnicodeProductProperty':
									newValue = None
									for pv in productProperty.possibleValues:
										if forceUnicodeLower(pv) == forceUnicodeLower(v):
											newValue = pv
											break
									if newValue:
										newValues.append(newValue)
										changed = True
										continue
								changed = True

							if changed:
								if not newValues:
									logger.debug(u"Properties changed: marking productPropertyState %s for deletion" % productPropertyState)
									deleteProductPropertyStates.append(productPropertyState)
								else:
									productPropertyState.setValues(newValues)
									logger.debug(u"Properties changed: marking productPropertyState %s for update" % productPropertyState)
									updateProductPropertyStates.append(productPropertyState)

						if deleteProductPropertyStates:
							self._depotBackend._context.productPropertyState_deleteObjects(deleteProductPropertyStates)
						if updateProductPropertyStates:
							self._depotBackend._context.productPropertyState_updateObjects(updateProductPropertyStates)
			except Exception as installingPackageError:
				logger.debug(u"Failed to install the package :(")
				logger.logException(installingPackageError, logLevel=LOG_DEBUG)
				try:
					ppf.cleanup()
				except Exception as cleanupError:
					logger.error("Cleanup failed: {0!r}", cleanupError)

				raise installingPackageError
		except Exception as installationError:
			logger.logException(installationError)
			raise BackendError(u"Failed to install package '%s' on depot '%s': %s" % (filename, depotId, installationError))

	def uninstallPackage(self, productId, force=False, deleteFiles=True):
		depotId = self._depotBackend._depotId
		logger.info(u"=================================================================================================")
		logger.notice(u"Uninstalling product '%s' on depot '%s'" % (productId, depotId))
		try:
			productId = forceProductIdFunc(productId)
			force = forceBool(force)
			deleteFiles = forceBool(deleteFiles)

			depot = self._depotBackend._context.host_getObjects(type='OpsiDepotserver', id=depotId)[0]
			productOnDepots = self._depotBackend._context.productOnDepot_getObjects(depotId=depotId, productId=productId)
			if not productOnDepots:
				raise BackendBadValueError("Product '%s' is not installed on depot '%s'" % (productId, depotId))

			logger.notice(u"Locking product '%s' on depot '%s'" % (productId, depotId))

			productOnDepot = productOnDepots[0]
			if productOnDepot.getLocked():
				logger.notice(u"Product currently locked on depot '%s'" % depotId)
				if not force:
					raise BackendTemporaryError(u"Product currently locked on depot '%s'" % depotId)
				logger.warning(u"Uninstallation of locked product forced")
			productOnDepot.setLocked(True)
			self._depotBackend._context.productOnDepot_updateObject(productOnDepot)

			logger.debug("Deleting product '%s'" % productId)

			if deleteFiles:
				if not depot.depotLocalUrl.startswith('file:///'):
					raise BackendBadValueError(u"Value '%s' not allowed for depot local url (has to start with 'file:///')" % depot.depotLocalUrl)

				for f in os.listdir(depot.depotLocalUrl[7:]):
					if (f.lower() == productId.lower()):
						clientDataDir = os.path.join(depot.depotLocalUrl[7:], f)
						logger.info("Deleting client data dir '%s'" % clientDataDir)
						removeDirectory(clientDataDir)

			self._depotBackend._context.productOnDepot_deleteObjects(productOnDepot)
		except Exception as e:
			logger.logException(e)
			raise BackendError(u"Failed to uninstall product '%s' on depot '%s': %s" % (productId, depotId, e))

	def checkDependencies(self, productPackageFile):
		for dependency in productPackageFile.packageControlFile.getPackageDependencies():
			productOnDepots = self._depotBackend._context.productOnDepot_getObjects(depotId=self._depotBackend._depotId, productId=dependency['package'])
			if not productOnDepots:
				raise BackendUnaccomplishableError(u"Dependent package '%s' not installed" % dependency['package'])

			if not dependency['version']:
				logger.info(u"Fulfilled product dependency '%s'" % dependency)
				continue

			productOnDepot = productOnDepots[0]
			availableVersion = productOnDepot.getProductVersion() + u'-' + productOnDepot.getPackageVersion()

			if compareVersions(availableVersion, dependency['condition'], dependency['version']):
				logger.info(u"Fulfilled package dependency %s (available version: %s)" % (dependency, availableVersion))
			else:
				raise BackendUnaccomplishableError(u"Unfulfilled package dependency %s (available version: %s)" % (dependency, availableVersion))
