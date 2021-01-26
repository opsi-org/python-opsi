# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2019 uib GmbH <info@uib.de>

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
:license: GNU Affero General Public License version 3
"""

import os
from contextlib import contextmanager

from OPSI.Backend.Base import ExtendedBackend
from OPSI.Exceptions import (
	BackendBadValueError, BackendConfigurationError,
	BackendError, BackendIOError, BackendMissingDataError,
	BackendTemporaryError, BackendUnaccomplishableError)
from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Types import (
	forceBool, forceDict, forceFilename, forceHostId,
	forceUnicode, forceUnicodeLower
)
from OPSI.Types import forceProductId as forceProductIdFunc
from OPSI.Object import ProductOnDepot, ProductPropertyState
from OPSI.System import getDiskSpaceUsage
from OPSI.Util.Product import ProductPackageFile
from OPSI.Util import compareVersions, getfqdn, md5sum, removeDirectory
from OPSI.Util.File import ZsyncFile
from OPSI.Config import FILE_ADMIN_GROUP

import opsicommon.logging

if os.name == "posix":
	import grp

__all__ = ('DepotserverBackend', 'DepotserverPackageManager')

logger = Logger()


class DepotserverBackend(ExtendedBackend):
	def __init__(self, backend, **kwargs):
		self._name = 'depotserver'

		ExtendedBackend.__init__(self, backend, **kwargs)

		self._sshRSAPublicKeyFile = '/etc/ssh/ssh_host_rsa_key.pub'

		self._depotId = forceHostId(getfqdn())
		if not self._context.host_getIdents(id=self._depotId):  # pylint: disable=maybe-no-member
			raise BackendMissingDataError(f"Depot '{self._depotId}' not found in backend")
		self._packageManager = DepotserverPackageManager(self)

	def depot_getHostRSAPublicKey(self):
		with open(self._sshRSAPublicKeyFile, 'r') as publicKey:
			return forceUnicode(publicKey.read())

	def depot_getMD5Sum(self, filename, forceCalculation=False):  # pylint: disable=invalid-name,no-self-use
		checksum = None
		try:
			if not forceBool(forceCalculation):
				hashFile = filename + '.md5'

				try:
					with open(hashFile) as fileHandle:
						checksum = fileHandle.read()

					logger.info("Using pre-calculated MD5sum from '%s'.", hashFile)
				except (OSError, IOError):
					pass

			if not checksum:
				checksum = md5sum(filename)

			logger.info("MD5sum of file '%s' is '%s'", filename, checksum)
			return checksum
		except Exception as err:
			raise BackendIOError(f"Failed to get md5sum: {err}") from err

	def depot_librsyncSignature(self, filename):  # pylint: disable=no-self-use
		from OPSI.Util.Sync import librsyncSignature  # pylint: disable=import-outside-toplevel

		try:
			return librsyncSignature(filename)
		except Exception as err:
			raise BackendIOError(f"Failed to get librsync signature: {err}") from err

	def depot_librsyncPatchFile(self, oldfile, deltafile, newfile):  # pylint: disable=no-self-use
		from OPSI.Util.Sync import librsyncPatchFile  # pylint: disable=import-outside-toplevel

		try:
			return librsyncPatchFile(oldfile, deltafile, newfile)
		except Exception as err:
			raise BackendIOError(f"Failed to patch file: {err}") from err

	def depot_librsyncDeltaFile(self, filename, signature, deltafile):  # pylint: disable=no-self-use
		from OPSI.Util.Sync import librsyncDeltaFile  # pylint: disable=import-outside-toplevel

		try:
			librsyncDeltaFile(filename, signature, deltafile)
		except Exception as err:
			raise BackendIOError(f"Failed to create librsync delta file: {err}") from err

	def depot_getDiskSpaceUsage(self, path):  # pylint: disable=no-self-use
		if os.name != 'posix':
			raise NotImplementedError("Not implemented for non-posix os")

		try:
			return getDiskSpaceUsage(path)
		except Exception as err:
			raise BackendIOError("Failed to get disk space usage: {err}") from err

	def depot_installPackage(  # pylint: disable=too-many-arguments
		self, filename, force=False, propertyDefaultValues=None, tempDir=None,
		forceProductId=None, suppressPackageContentFileGeneration=False
	):
		with opsicommon.logging.log_context({'instance' : 'package_install'}):
			self._packageManager.installPackage(filename,
				force=force, propertyDefaultValues=propertyDefaultValues or {},
				tempDir=tempDir, forceProductId=forceProductId,
				suppressPackageContentFileGeneration=suppressPackageContentFileGeneration
			)

	def depot_uninstallPackage(self, productId, force=False, deleteFiles=True):
		self._packageManager.uninstallPackage(productId, force, deleteFiles)

	def depot_createMd5SumFile(self, filename, md5sumFilename):  # pylint: disable=invalid-name,no-self-use
		if not os.path.exists(filename):
			raise BackendIOError(f"File not found: {filename}")
		logger.info("Creating md5sum file '%s'", md5sumFilename)
		md5 = md5sum(filename)
		with open(md5sumFilename, 'w') as md5file:
			md5file.write(md5)
		if os.name == "posix":
			os.chown(md5sumFilename, -1, grp.getgrnam(FILE_ADMIN_GROUP)[2])
			os.chmod(md5file, 0o660)

	def depot_createZsyncFile(self, filename, zsyncFilename):  # pylint: disable=no-self-use
		if not os.path.exists(filename):
			raise BackendIOError(f"File not found: {filename}")
		logger.info("Creating zsync file '%s'", zsyncFilename)
		zsyncFile = ZsyncFile(zsyncFilename)
		zsyncFile.generate(filename)
		if os.name == "posix":
			os.chown(zsyncFilename, -1, grp.getgrnam(FILE_ADMIN_GROUP)[2])
			os.chmod(zsyncFilename, 0o660)


class DepotserverPackageManager:
	def __init__(self, depotBackend):
		if not isinstance(depotBackend, DepotserverBackend):
			raise BackendConfigurationError(
				"DepotserverPackageManager needs instance of DepotserverBackend as backend, "
				f"got {depotBackend.__class__.__name__}"
			)
		self._depotBackend = depotBackend

	def installPackage(  # pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements
		self, filename, force=False, propertyDefaultValues=None, tempDir=None,
		forceProductId=None, suppressPackageContentFileGeneration=False
	):
		propertyDefaultValues = propertyDefaultValues or {}

		@contextmanager
		def productPackageFile(filename, tempDir, depotId):
			try:
				depots = self._depotBackend._context.host_getObjects(id=depotId)  # pylint: disable=protected-access
				depot = depots[0]
				del depots
			except IndexError as err:
				raise BackendMissingDataError(f"Depot '{depotId}' not found in backend") from err

			depotLocalUrl = depot.getDepotLocalUrl()
			if not depotLocalUrl or not depotLocalUrl.startswith('file:///'):
				raise BackendBadValueError("Value '%s' not allowed for depot local url (has to start with 'file:///')" % depotLocalUrl)
			clientDataDir = depotLocalUrl[7:]

			ppf = ProductPackageFile(filename, tempDir=tempDir)
			ppf.setClientDataDir(clientDataDir)
			ppf.getMetaData()

			try:
				yield ppf
				ppf.setAccessRights()
			finally:
				try:
					ppf.cleanup()
				except Exception as err:  # pylint: disable=broad-except
					logger.error("Cleanup failed: %s", err)

		@contextmanager
		def lockProduct(backend, product, depotId, forceInstallation):
			productId = product.getId()
			logger.debug("Checking for locked product '%s' on depot '%s'", productId, depotId)
			productOnDepots = backend.productOnDepot_getObjects(depotId=depotId, productId=productId)
			try:
				if productOnDepots[0].getLocked():
					logger.notice("Product '%s' currently locked on depot '%s'", productId, depotId)
					if not forceInstallation:
						raise BackendTemporaryError("Product '{}' currently locked on depot '{}'".format(productId, depotId))
					logger.warning("Installation of locked product forced")
			except IndexError:
				pass

			logger.notice("Locking product '%s' on depot '%s'", productId, depotId)
			productOnDepot = ProductOnDepot(
				productId=productId,
				productType=product.getType(),
				productVersion=product.getProductVersion(),
				packageVersion=product.getPackageVersion(),
				depotId=depotId,
				locked=True
			)
			logger.info("Creating product on depot %s", productOnDepot)
			backend.productOnDepot_createObjects(productOnDepot)

			try:
				yield productOnDepot
			except Exception as err:
				logger.warning("Installation error. Not unlocking product '%s' on depot '%s'.", productId, depotId)
				raise err

			logger.notice(
				"Unlocking product '%s' %s-%s on depot '%s'",
				productOnDepot.getProductId(),
				productOnDepot.getProductVersion(),
				productOnDepot.getPackageVersion(),
				depotId
			)
			productOnDepot.setLocked(False)
			backend.productOnDepot_updateObject(productOnDepot)

		@contextmanager
		def runPackageScripts(productPackageFile, depotId):
			logger.info("Running preinst script")
			for line in productPackageFile.runPreinst(({'DEPOT_ID': depotId})):
				logger.info("[preinst] %s", line)

			yield

			logger.info("Running postinst script")
			for line in productPackageFile.runPostinst({'DEPOT_ID': depotId}):
				logger.info("[postinst] %s", line)

		def cleanUpProducts(backend, productId):
			productIdents = set()
			for productOnDepot in backend.productOnDepot_getObjects(productId=productId):
				productIdent = "%s;%s;%s" % (productOnDepot.productId, productOnDepot.productVersion, productOnDepot.packageVersion)
				productIdents.add(productIdent)

			deleteProducts = set(
				product
				for product in backend.product_getObjects(id=productId)
				if product.getIdent(returnType='unicode') not in productIdents
			)

			if deleteProducts:
				backend.product_deleteObjects(deleteProducts)

		def cleanUpProductPropertyStates(backend, productProperties, depotId, productOnDepot):  # pylint: disable=too-many-locals
			productPropertiesToCleanup = {}
			for productProperty in productProperties:
				if productProperty.editable or not productProperty.possibleValues:
					continue
				productPropertiesToCleanup[productProperty.propertyId] = productProperty

			if productPropertiesToCleanup:  # pylint: disable=too-many-nested-blocks
				clientIds = set(
					clientToDepot['clientId']
					for clientToDepot in backend.configState_getClientToDepotserver(depotIds=depotId)
				)

				if clientIds:
					deleteProductPropertyStates = []
					updateProductPropertyStates = []
					states = backend.productPropertyState_getObjects(
						objectId=clientIds,
						productId=productOnDepot.getProductId(),
						propertyId=list(productPropertiesToCleanup.keys())
					)

					for productPropertyState in states:
						changed = False
						newValues = []
						for value in productPropertyState.values:
							productProperty = productPropertiesToCleanup[productPropertyState.propertyId]
							if value in productProperty.possibleValues:
								newValues.append(value)
								continue

							if productProperty.getType() == 'BoolProductProperty' and forceBool(value) in productProperty.possibleValues:
								newValues.append(forceBool(value))
								changed = True
								continue

							if productProperty.getType() == 'UnicodeProductProperty':
								newValue = None
								for possibleValue in productProperty.possibleValues:
									if forceUnicodeLower(possibleValue) == forceUnicodeLower(value):
										newValue = possibleValue
										break

								if newValue is not None:
									newValues.append(newValue)
									changed = True
									continue

							changed = True

						if changed:
							if not newValues:
								logger.debug("Properties changed: marking productPropertyState %s for deletion", productPropertyState)
								deleteProductPropertyStates.append(productPropertyState)
							else:
								productPropertyState.setValues(newValues)
								logger.debug("Properties changed: marking productPropertyState %s for update", productPropertyState)
								updateProductPropertyStates.append(productPropertyState)

					if deleteProductPropertyStates:
						backend.productPropertyState_deleteObjects(deleteProductPropertyStates)
					if updateProductPropertyStates:
						backend.productPropertyState_updateObjects(updateProductPropertyStates)

		depotId = self._depotBackend._depotId  # pylint: disable=protected-access
		logger.info("=================================================================================================")
		if forceProductId:
			forceProductId = forceProductIdFunc(forceProductId)
			logger.notice("Installing package file '%s' as '%s' on depot '%s'", filename, forceProductId, depotId)
		else:
			logger.notice("Installing package file '%s' on depot '%s'", filename, depotId)

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
				raise BackendIOError("Package file '{0}' does not exist or can not be accessed.".format(filename))
			if not os.access(filename, os.R_OK):
				raise BackendIOError("Read access denied for package file '%s'" % filename)

			try:
				dataBackend = self._depotBackend._context  # pylint: disable=protected-access

				with productPackageFile(filename, tempDir, depotId) as ppf:
					product = ppf.packageControlFile.getProduct()
					if forceProductId:
						logger.info("Forcing product id '%s'", forceProductId)
						product.setId(forceProductId)
						ppf.packageControlFile.setProduct(product)

					productId = product.getId()

					logger.info("Creating product in backend")
					dataBackend.product_createObjects(product)

					with lockProduct(dataBackend, product, depotId, force) as productOnDepot:
						logger.info("Checking package dependencies")
						self.checkDependencies(ppf)

						with runPackageScripts(ppf, depotId):
							logger.info("Deleting old client-data dir")
							ppf.deleteProductClientDataDir()

							logger.info("Unpacking package files")
							ppf.extractData()

							logger.info("Updating product dependencies of product %s", product)
							currentProductDependencies = {}
							for productDependency in dataBackend.productDependency_getObjects(
										productId=productId,
										productVersion=product.getProductVersion(),
										packageVersion=product.getPackageVersion()):
								ident = productDependency.getIdent(returnType='unicode')
								currentProductDependencies[ident] = productDependency

							productDependencies = []
							for productDependency in ppf.packageControlFile.getProductDependencies():
								if forceProductId:
									productDependency.productId = productId

								ident = productDependency.getIdent(returnType='unicode')
								try:
									del currentProductDependencies[ident]
								except KeyError:
									pass  # Dependency does currently not exist.
								productDependencies.append(productDependency)

							dataBackend.productDependency_createObjects(productDependencies)
							if currentProductDependencies:
								dataBackend.productDependency_deleteObjects(
									list(currentProductDependencies.values())
								)

							logger.info("Updating product properties of product %s", product)
							currentProductProperties = {}
							productProperties = []
							for productProperty in dataBackend.productProperty_getObjects(
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
							dataBackend.productProperty_createObjects(productProperties)

							for productProperty in productProperties:
								# Adjust property default values
								if productProperty.editable or not productProperty.possibleValues:
									continue

								newValues = [
									value
									for value in propertyDefaultValues.get(productProperty.propertyId, [])
									if value in productProperty.possibleValues
								]
								if not newValues and productProperty.defaultValues:
									newValues = productProperty.defaultValues
								propertyDefaultValues[productProperty.propertyId] = newValues

							if currentProductProperties:
								dataBackend.productProperty_deleteObjects(
									list(currentProductProperties.values())
								)

							logger.info("Deleting product property states of product %s on depot '%s'", productId, depotId)
							dataBackend.productPropertyState_deleteObjects(
								dataBackend.productPropertyState_getObjects(
									productId=productId,
									objectId=depotId
								)
							)

							logger.info("Deleting not needed property states of product %s", productId)
							productPropertyStates = dataBackend.productPropertyState_getObjects(productId=productId)
							baseProperties = dataBackend.productProperty_getObjects(productId=productId)

							productPropertyIds = None
							productPropertyStatesToDelete = None
							productPropertyIds = [productProperty.propertyId for productProperty in baseProperties]
							productPropertyStatesToDelete = [ppState for ppState in productPropertyStates if ppState.propertyId not in productPropertyIds]
							logger.debug("Following productPropertyStates are marked to delete: '%s'", productPropertyStatesToDelete)
							if productPropertyStatesToDelete:
								dataBackend.productPropertyState_deleteObjects(productPropertyStatesToDelete)

							logger.info("Setting product property states in backend")
							productPropertyStates = [
								ProductPropertyState(
									productId=productId,
									propertyId=productProperty.propertyId,
									objectId=depotId,
									values=productProperty.defaultValues
								) for productProperty in productProperties
							]

							for productPropertyState in productPropertyStates:
								if productPropertyState.propertyId in propertyDefaultValues:
									try:
										productPropertyState.setValues(propertyDefaultValues[productPropertyState.propertyId])
									except Exception as installationError:  # pylint: disable=broad-except
										logger.error(
											"Failed to set default values to %s for productPropertyState %s: %s",
											propertyDefaultValues[productPropertyState.propertyId],
											productPropertyState,
											installationError
										)
							dataBackend.productPropertyState_createObjects(productPropertyStates)

						if not suppressPackageContentFileGeneration:
							ppf.createPackageContentFile()
						else:
							logger.debug("Suppressed generation of package content file.")

				cleanUpProducts(dataBackend, productOnDepot.productId)
				cleanUpProductPropertyStates(dataBackend, productProperties, depotId, productOnDepot)
			except Exception as installingPackageError:
				logger.debug("Failed to install the package %s", filename)
				logger.logException(installingPackageError, logLevel=LOG_DEBUG)
				raise installingPackageError
		except Exception as err:
			logger.error(err, exc_info=True)
			raise BackendError(
				f"Failed to install package '{filename}' on depot '{depotId}': {err}"
			) from err

	def uninstallPackage(self, productId, force=False, deleteFiles=True):
		depotId = self._depotBackend._depotId  # pylint: disable=protected-access
		logger.info("=================================================================================================")
		logger.notice("Uninstalling product '%s' on depot '%s'", productId, depotId)
		try:
			productId = forceProductIdFunc(productId)
			force = forceBool(force)
			deleteFiles = forceBool(deleteFiles)

			dataBackend = self._depotBackend._context  # pylint: disable=protected-access
			depot = dataBackend.host_getObjects(type='OpsiDepotserver', id=depotId)[0]
			productOnDepots = dataBackend.productOnDepot_getObjects(depotId=depotId, productId=productId)
			try:
				productOnDepot = productOnDepots[0]
			except IndexError as err:
				raise BackendBadValueError(
					f"Product '{productId}' is not installed on depot '{depotId}'"
				) from err

			if productOnDepot.getLocked():
				logger.notice("Product '%s' currently locked on depot '%s'", productId, depotId)
				if not force:
					raise BackendTemporaryError("Product '%s' currently locked on depot '%s'" % (productId, depotId))
				logger.warning("Uninstallation of locked product forced")

			logger.notice("Locking product '%s' on depot '%s'", productId, depotId)
			productOnDepot.setLocked(True)
			dataBackend.productOnDepot_updateObject(productOnDepot)

			logger.debug("Deleting product '%s'", productId)

			if deleteFiles:
				if not depot.depotLocalUrl.startswith('file:///'):
					raise BackendBadValueError("Value '%s' not allowed for depot local url (has to start with 'file:///')" % depot.depotLocalUrl)

				for element in os.listdir(depot.depotLocalUrl[7:]):
					if element.lower() == productId.lower():
						clientDataDir = os.path.join(depot.depotLocalUrl[7:], element)
						logger.info("Deleting client data dir '%s'", clientDataDir)
						removeDirectory(clientDataDir)

			dataBackend.productOnDepot_deleteObjects(productOnDepot)
		except Exception as err:
			logger.error(err, exc_info=True)
			raise BackendError(
				f"Failed to uninstall product '{productId}' on depot '{depotId}': {err}"
			) from err

	def checkDependencies(self, productPackageFile):
		for dependency in productPackageFile.packageControlFile.getPackageDependencies():
			productOnDepots = self._depotBackend._context.productOnDepot_getObjects(  # pylint: disable=protected-access
				depotId=self._depotBackend._depotId, productId=dependency['package']  # pylint: disable=protected-access
			)
			if not productOnDepots:
				raise BackendUnaccomplishableError("Dependent package '%s' not installed" % dependency['package'])

			if not dependency['version']:
				logger.info("Fulfilled product dependency '%s'", dependency)
				continue

			productOnDepot = productOnDepots[0]
			availableVersion = productOnDepot.getProductVersion() + '-' + productOnDepot.getPackageVersion()

			if compareVersions(availableVersion, dependency['condition'], dependency['version']):
				logger.info("Fulfilled package dependency %s (available version: %s)", dependency, availableVersion)
			else:
				raise BackendUnaccomplishableError("Unfulfilled package dependency %s (available version: %s)" % (dependency, availableVersion))
