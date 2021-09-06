# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Component for handling package updates.
"""
# pylint: disable=too-many-lines

from contextlib import contextmanager
import os
import os.path
import re
import time
import json
import datetime
from urllib.parse import quote
import requests
from requests.packages import urllib3

from opsicommon.logging import logger
from opsicommon.client.jsonrpc import JSONRPCBackend

from OPSI import System
from OPSI.Backend.BackendManager import BackendManager
from OPSI.Logger import Logger
from OPSI.Object import NetbootProduct, ProductOnClient
from OPSI.Types import forceHostId, forceProductId
from OPSI.Util import compareVersions, formatFileSize, getfqdn, md5sum
from OPSI.Util.File import ZsyncFile
from OPSI.Util.File.Opsi import parseFilename
from OPSI.Util.Path import cd
from OPSI.Util.Product import ProductPackageFile
from OPSI.Util.Task.Rights import setRights

from .Config import DEFAULT_USER_AGENT, ConfigurationParser
from .Notifier import DummyNotifier, EmailNotifier
from .Repository import LinksExtractor

urllib3.disable_warnings()

__all__ = ('OpsiPackageUpdater', )

logger = Logger()

class HashsumMissmatchError(ValueError):
	pass


class OpsiPackageUpdater:  # pylint: disable=too-many-public-methods
	def __init__(self, config):
		self.config = config
		self.httpHeaders = {"User-Agent": self.config.get("userAgent", DEFAULT_USER_AGENT)}
		self.configBackend = None
		self.depotConnections = {}
		self.depotId = forceHostId(getfqdn(conf="/etc/opsi/global.conf").lower())
		self.errors = []

		depots = self.getConfigBackend().host_getObjects(type='OpsiDepotserver', id=self.depotId)  # pylint: disable=no-member
		try:
			self.depotKey = depots[0].opsiHostKey
		except IndexError as err:
			raise ValueError(f"Depot '{self.depotId}' not found in backend") from err

		if not self.depotKey:
			raise ValueError(f"Opsi host key for depot '{self.depotId}' not found in backend")
		logger.addConfidentialString(self.depotKey)

		self.readConfigFile()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		for con in self.depotConnections.values():
			try:
				con.backend_exit()
			except Exception:  # pylint: disable=broad-except
				pass

		try:
			self.configBackend.backend_exit()
		except Exception:  # pylint: disable=broad-except
			pass

	def getActiveRepositories(self):
		"""
		Iterates over the found repositories and yields the active ones
		one by one.
		If a repository name filter is given only repositories matching
		the name will be returned.

		:rtype: ProductRepositoryInfo
		"""
		for repo in self.getRepositories():
			if not repo.active:
				continue

			yield repo

	def getRepositories(self):
		"""
		Iterates over all found repositories and yields them.
		If a repository name filter is given only repositories matching
		the name will be returned.

		:rtype: ProductRepositoryInfo
		"""
		name = self.config.get("repositoryName", None)

		for repo in self.config.get('repositories', []):
			if name and repo.name.strip().lower() != name.strip().lower():
				continue

			yield repo

	def readConfigFile(self):
		parser = ConfigurationParser(self.config["configFile"], backend=self.getConfigBackend(), depotId=self.depotId, depotKey=self.depotKey)
		self.config = parser.parse(self.config)

	def getConfigBackend(self):
		if not self.configBackend:
			self.configBackend = BackendManager(
				dispatchConfigFile='/etc/opsi/backendManager/dispatch.conf',
				backendConfigDir='/etc/opsi/backends',
				extensionConfigDir='/etc/opsi/backendManager/extend.d',
				depotbackend=True,
				hostControlBackend=True
			)
		return self.configBackend

	def getDepotConnection(self, depotId, username, password):
		if depotId not in self.depotConnections:
			self.depotConnections[depotId] = JSONRPCBackend(
				address=depotId,
				username=username,
				password=password,
				application=self.httpHeaders['User-Agent'] + ' (depot connection)',
			)
		return self.depotConnections[depotId]

	def get_new_packages_per_repository(self):
		downloadablePackages = self.getDownloadablePackages()
		downloadablePackages = self.onlyNewestPackages(downloadablePackages)
		downloadablePackages = self._filterProducts(downloadablePackages)
		result = {}
		for package in downloadablePackages:
			if result.get(package["repository"]):
				result[package["repository"]].append(package)
			else:
				result[package["repository"]] = [package]
		return result

	def processUpdates(self):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		if not any(self.getActiveRepositories()):
			logger.warning("No repositories configured, nothing to do")
			return

		notifier = self._getNotifier()

		try:  # pylint: disable=too-many-nested-blocks
			installedProducts = self.getInstalledProducts()
			localPackages = self.getLocalPackages()
			packages_per_repository = self.get_new_packages_per_repository()
			if not any(packages_per_repository.values()):
				logger.warning("No downloadable packages found")
				return

			newPackages = []
			for repository, downloadablePackages in packages_per_repository.items():
				logger.debug("Processing downloadable packages on repository %s", repository)
				with self.makeSession(repository) as session:
					for availablePackage in downloadablePackages:
						logger.debug("Processing available package %s", availablePackage)
						try:
							product = self.get_installed_package(availablePackage, installedProducts)

							if not self.is_install_needed(availablePackage, product):
								continue

							localPackageFound = self.get_local_package(availablePackage, localPackages)

							zsync = True
							if availablePackage['repository'].baseUrl.split(':', 1)[0].lower().endswith('s'):
								logger.warning("Cannot use zsync, because zsync does not support https")
								zsync = False

							if self.is_download_needed(localPackageFound, availablePackage, notifier=None):
								self.get_package(availablePackage, localPackageFound, session,  zsync=zsync, notifier=None)
							packageFile = os.path.join(self.config["packageDir"], availablePackage["filename"])
							self._verifyDownloadedPackage(packageFile, availablePackage, session, zsync, notifier)
							newPackages.append(availablePackage)
						except Exception as exc: # pylint: disable=broad-except
							if self.config.get("ignoreErrors"):
								logger.error("Ignoring Error for package %s: %s", availablePackage["productId"], exc, exc_info=True)
								notifier.appendLine(f"Ignoring Error for package {availablePackage['productId']}: {exc}")
							else:
								raise exc
			if not newPackages:
				logger.notice("No new packages available")
				return

			logger.info("New packages available: %s", ", ".join([sorted(np["productId"]) for np in newPackages]))

			def in_installation_window(start_str, end_str):
				now = datetime.datetime.now().time()
				start = datetime.time(int(start_str.split(":")[0]), int(start_str.split(":")[1]))
				end = datetime.time(int(end_str.split(":")[0]), int(end_str.split(":")[1]))

				logger.debug("Installation window configuration: start=%s, end=%s, now=%s", start, end, now)

				in_window = False
				if start <= end:
					in_window = start <= now <= end
				else:
					# Crosses midnight
					in_window = now >= start or now <= end

				if in_window:
					logger.info("Current time %s is within the configured installation window (%s-%s)", now, start, end)
					return True

				logger.info("Current time %s is outside the configured installation window (%s-%s)", now, start, end)
				return False

			insideInstallWindow = True
			# Times have to be specified in the form HH:MM, i.e. 06:30
			if not self.config['installationWindowStartTime'] or not self.config['installationWindowEndTime']:
				logger.info("Installation time window is not defined, installing products and setting actions")
			elif in_installation_window(self.config['installationWindowStartTime'], self.config['installationWindowEndTime']):
				logger.notice("Running inside installation time window, installing products and setting actions")
			else:
				logger.notice(
					"Running outside installation time window, not installing products except product ids %s",
					self.config['installationWindowExceptions']
				)
				insideInstallWindow = False

			sequence = []
			for package in newPackages:
				if not insideInstallWindow and package['productId'] not in self.config['installationWindowExceptions']:
					continue
				sequence.append(package['productId'])

			for package in newPackages:
				if package['productId'] not in sequence:
					continue
				packageFile = os.path.join(self.config["packageDir"], package["filename"])
				productId = package['productId']
				ppf = ProductPackageFile(packageFile, tempDir=self.config.get('tempdir', '/tmp'))
				ppf.getMetaData()
				dependencies = ppf.packageControlFile.getPackageDependencies()
				ppf.cleanup()
				for dependency in dependencies:
					try:
						ppos = sequence.index(productId)
						dpos = sequence.index(dependency['package'])
						if ppos < dpos:
							sequence.remove(dependency['package'])
							sequence.insert(ppos, dependency['package'])
					except Exception as err:  # pylint: disable=broad-except
						logger.debug("While processing package '%s', dependency '%s': %s", packageFile, dependency['package'], err)

			sortedPackages = []
			for productId in sequence:
				for package in newPackages:
					if productId == package['productId']:
						sortedPackages.append(package)
						break
			newPackages = sortedPackages

			backend = self.getConfigBackend()
			installedPackages = []
			for package in newPackages:
				packageFile = os.path.join(self.config["packageDir"], package["filename"])

				if package['repository'].onlyDownload:
					logger.debug("Download only is set for repository, not installing package '%s'", packageFile)
					continue

				try:
					propertyDefaultValues = {}
					try:
						if package['repository'].inheritProductProperties and package['repository'].opsiDepotId:
							logger.info("Trying to get product property defaults from repository")
							productPropertyStates = backend.productPropertyState_getObjects(  # pylint: disable=no-member
								productId=package['productId'],
								objectId=package['repository'].opsiDepotId
							)
						else:
							productPropertyStates = backend.productPropertyState_getObjects(  # pylint: disable=no-member
								productId=package['productId'],
								objectId=self.depotId
							)
						if productPropertyStates:
							for pps in productPropertyStates:
								propertyDefaultValues[pps.propertyId] = pps.values
						logger.notice("Using product property defaults: %s", propertyDefaultValues)
					except Exception as err:  # pylint: disable=broad-except
						logger.warning("Failed to get product property defaults: %s", err)

					logger.info("Installing package '%s'", packageFile)
					backend.depot_installPackage(  # pylint: disable=no-member
						filename=packageFile,
						propertyDefaultValues=propertyDefaultValues,
						tempDir=self.config.get('tempdir', '/tmp')
					)
					productOnDepots = backend.productOnDepot_getObjects(  # pylint: disable=no-member
						depotId=self.depotId,
						productId=package['productId']
					)
					if not productOnDepots:
						raise ValueError(
							f"Product '{package['productId']}' not found on depot '{self.depotId}' after installation"
						)
					package['product'] = backend.product_getObjects(  # pylint: disable=no-member
						id=productOnDepots[0].productId,
						productVersion=productOnDepots[0].productVersion,
						packageVersion=productOnDepots[0].packageVersion
					)[0]

					message = f"Package '{packageFile}' successfully installed"
					notifier.appendLine(message, pre='\n')
					logger.notice(message)
					installedPackages.append(package)

				except Exception as err: # pylint: disable=broad-except
					if not self.config.get("ignoreErrors"):
						raise
					logger.error("Ignoring error for package %s: %s", package["productId"], err, exc_info=True)
					notifier.appendLine(f"Ignoring error for package {package['productId']}: {err}")

			if not installedPackages:
				logger.notice("No new packages installed")
				return

			logger.debug("Mark redis product cache as dirty for depot: %s", self.depotId)
			config_id = f"opsiconfd.{self.depotId}.product.cache.outdated"
			backend.config_createBool(id=config_id, description="", defaultValues=[True])  # pylint: disable=no-member

			shutdownProduct = None
			if self.config['wolAction'] and self.config["wolShutdownWanted"]:
				try:
					shutdownProduct = backend.productOnDepot_getObjects(  # pylint: disable=no-member
						depotId=self.depotId, productId='shutdownwanted'
					)[0]
					logger.info("Found 'shutdownwanted' product on depot '%s': %s", self.depotId, shutdownProduct)
				except IndexError:
					logger.error("Product 'shutdownwanted' not avaliable on depot '%s'", self.depotId)

			wakeOnLanClients = set()
			for package in installedPackages:
				if not package['product'].setupScript:
					continue
				if package['repository'].autoSetup:
					if isinstance(package['product'], NetbootProduct):
						logger.info(
							"Not setting action 'setup' for product '%s' where installation status 'installed' "
							"because auto setup is not allowed for netboot products",
							package['productId']
						)
						continue
					if package['productId'].startswith((
						'opsi-local-image-', 'opsi-uefi-', 'opsi-vhd-', 'opsi-wim-', 'windows10-upgrade', 'opsi-auto-update', 'windomain'
					)):
						logger.info(
							"Not setting action 'setup' for product '%s' where installation status 'installed' "
							"because auto setup is not allowed for opsi module products",
							package['productId']
						)
						continue

					if any(exclude.search(package['productId']) for exclude in package['repository'].autoSetupExcludes):
						logger.info(
							"Not setting action 'setup' for product '%s' because it's excluded by regular expression",
							package['productId']
						)
						continue

					logger.notice(
						"Setting action 'setup' for product '%s' where installation status 'installed' "
						"because auto setup is set for repository '%s'",
						package['productId'], package['repository'].name
					)
				else:
					logger.info(
						"Not setting action 'setup' for product '%s' where installation status 'installed' "
						"because auto setup is not set for repository '%s'",
						package['productId'], package['repository'].name
					)
					continue

				clientToDepotserver = backend.configState_getClientToDepotserver(depotIds=[self.depotId])  # pylint: disable=no-member
				clientIds = set(
					ctd['clientId']
					for ctd in clientToDepotserver
					if ctd['clientId']
				)

				if clientIds:
					productOnClients = backend.productOnClient_getObjects(  # pylint: disable=no-member
						attributes=['installationStatus'],
						productId=package['productId'],
						productType='LocalbootProduct',
						clientId=clientIds,
						installationStatus=['installed'],
					)
					if productOnClients:
						wolEnabled = self.config['wolAction']
						excludedWolProducts = set(self.config['wolActionExcludeProductIds'])

						for poc in productOnClients:
							poc.setActionRequest('setup')
							if wolEnabled and package['productId'] not in excludedWolProducts:
								wakeOnLanClients.add(poc.clientId)

						backend.productOnClient_updateObjects(productOnClients)  # pylint: disable=no-member
						notifier.appendLine((
							f"Product {package['productId']} set to 'setup' on clients: "
							', '.join(sorted(poc.clientId for poc in productOnClients))
						))

			if wakeOnLanClients:
				logger.notice("Powering on clients %s", wakeOnLanClients)
				notifier.appendLine(f"Powering on clients: {', '.join(sorted(wakeOnLanClients))}")

				for clientId in wakeOnLanClients:
					try:
						logger.info("Powering on client '%s'", clientId)
						if self.config["wolShutdownWanted"] and shutdownProduct:
							logger.info("Setting shutdownwanted to 'setup' for client '%s'", clientId)

							backend.productOnClient_updateObjects(  # pylint: disable=no-member
								ProductOnClient(
									productId=shutdownProduct.productId,
									productType=shutdownProduct.productType,
									productVersion=shutdownProduct.productVersion,
									packageVersion=shutdownProduct.packageVersion,
									clientId=clientId,
									actionRequest='setup'
								)
							)
						backend.hostControl_start(hostIds=[clientId])  # pylint: disable=no-member
						time.sleep(self.config["wolStartGap"])
					except Exception as err:  # pylint: disable=broad-except
						logger.error("Failed to power on client '%s': %s", clientId, err)
		except Exception as err:  # pylint: disable=broad-except
			notifier.appendLine(f"Error occurred: {err}")
			notifier.setSubject(f"ERROR {self.config['subject']}")
			raise
		finally:
			if notifier and notifier.hasMessage():
				notifier.notify()

	def _getNotifier(self):
		if not self.config["notification"]:
			return DummyNotifier()

		logger.info("E-Mail notification is activated")
		notifier = EmailNotifier(
			smtphost=self.config["smtphost"],
			smtpport=self.config["smtpport"],
			sender=self.config["sender"],
			receivers=self.config["receivers"],
			subject=self.config["subject"],
		)

		if self.config["use_starttls"]:
			notifier.useStarttls = self.config["use_starttls"]

		if self.config["smtpuser"] and self.config["smtppassword"] is not None:
			notifier.username = self.config["smtpuser"]
			notifier.password = self.config["smtppassword"]

		return notifier

	def _filterProducts(self, products):
		if self.config["processProductIds"]:
			# Checking if given productIds are available and
			# process only these products
			newProductList = []
			for product in self.config["processProductIds"]:
				for pac in products:
					if product == pac["productId"]:
						newProductList.append(pac)
						break
				else:
					logger.error("Product '%s' not found in repository!", product)
					possibleProductIDs = sorted(set(pac["productId"] for pac in products))
					logger.notice("Possible products are: %s", ', '.join(possibleProductIDs))
					raise ValueError(f"You have searched for a product, which was not found in configured repository: '{product}'")

			if newProductList:
				return newProductList

		return products

	def _verifyDownloadedPackage(self, packageFile, availablePackage, session, zsync, notifier):  # pylint: disable=too-many-arguments
		"""
		Verify the downloaded package.

		This checks the hashsums of the downloaded package.
		If the download was done with zsync and the hashes are different
		we download the package in whole.

		:param packageFile: The path to the package that is checked.
		:type packageFile: str
		:param availablePackage: Information about the package.
		:type availablePackage: dict
		:param notifier: The notifier to use
		:raise HashsumMissmatchError: In case the hashsums mismatch
		"""
		if availablePackage['md5sum']:
			logger.info("Verifying download of package '%s'", packageFile)
			md5 = md5sum(packageFile)
			if md5 != availablePackage["md5sum"]:
				if zsync:
					logger.warning(
						"%s: zsync Download has failed, trying once to load full package",
						availablePackage['productId']
					)
					self.downloadPackage(availablePackage, session, notifier=notifier)
					self.cleanupPackages(availablePackage)

					md5 = md5sum(packageFile)

				# Check again in case we re-downloaded the file
				if md5 != availablePackage["md5sum"]:
					raise HashsumMissmatchError(
						f"{availablePackage['productId']}: md5sum mismatch"
					)

			logger.info(
				"%s: md5sum match, package download verified",
				availablePackage['productId']
			)
		else:
			logger.warning("%s: Cannot verify download of package: missing md5sum file",
				availablePackage['productId']
			)

	def get_installed_package(self, availablePackage, installedProducts):  # pylint: disable=no-self-use
		logger.info("Testing if download/installation of package '%s' is needed", availablePackage["filename"])
		for product in installedProducts:
			if product['productId'] == availablePackage['productId']:
				logger.debug("Product '%s' is installed", availablePackage['productId'])
				logger.debug(
					"Available product version is '%s', installed product version is '%s-%s'",
						availablePackage['version'],
						product['productVersion'],
						product['packageVersion']
				)
				return product
		return None

	def get_local_package(self, availablePackage, localPackages):  # pylint: disable=no-self-use
		for localPackage in localPackages:
			if localPackage['productId'] == availablePackage['productId']:
				logger.debug("Found local package file '%s'", localPackage['filename'])
				return localPackage
		return None

	def is_download_needed(self, localPackageFound, availablePackage, notifier=None):
		if (
				localPackageFound and
				localPackageFound['filename'] == availablePackage['filename'] and
				localPackageFound['md5sum'] == availablePackage['md5sum']
		):
			logger.info(
				"%s - download of package is not required: found local package %s with matching md5sum",
					availablePackage["filename"],
					localPackageFound["filename"]
			)
			# No notifier message as nothing to do
			return False

		if self.config["forceDownload"]:
			message = f"{availablePackage['filename']} - download of package is forced."
		elif localPackageFound:
			message = (
				f"{availablePackage['filename']} - download of package is required: "
				f"found local package {localPackageFound['filename']} which differs from available"
			)
		else:
			message = (
				f"{availablePackage['filename']} - download of package is required: "
				" local package not found"
			)

		logger.notice(message)
		if notifier is not None:
			notifier.appendLine(message)
		return True

	def is_install_needed(self, availablePackage, product):  # pylint: disable=no-self-use
		if not product:
			if availablePackage['repository'].autoInstall:
				logger.notice(
					"%s - installation required: product '%s' is not installed and auto install is set for repository '%s'",
					availablePackage["filename"], availablePackage['productId'], availablePackage['repository'].name
				)
				return True
			logger.info(
				"%s - installation not required: product '%s' is not installed but auto install is not set for repository '%s'",
				availablePackage["filename"], availablePackage['productId'], availablePackage['repository'].name
			)
			return False

		if compareVersions(availablePackage['version'], '>', f"{product['productVersion']}-{product['packageVersion']}"):
			if availablePackage['repository'].autoUpdate:
				logger.notice(
					"%s - installation required: a more recent version of product '%s' was found"
					" (installed: %s-%s, available: %s) and auto update is set for repository '%s'",
					availablePackage["filename"], availablePackage['productId'], product['productVersion'],
					product['packageVersion'], availablePackage['version'], availablePackage['repository'].name
				)
				return True
			logger.info(
				"%s - installation not required: a more recent version of product '%s' was found"
				" (installed: %s-%s, available: %s) but auto update is not set for repository '%s'",
				availablePackage["filename"], availablePackage['productId'], product['productVersion'],
				product['packageVersion'], availablePackage['version'], availablePackage['repository'].name
			)
			return False
		logger.info(
			"%s - installation not required: installed version '%s-%s' of product '%s' is up to date",
			availablePackage["filename"], product['productVersion'], product['packageVersion'], availablePackage['productId']
		)
		return False

	def get_package(self, availablePackage, localPackageFound, session, notifier=None, zsync=True):  # pylint: disable=too-many-arguments
		packageFile = os.path.join(self.config["packageDir"], availablePackage["filename"])
		if self.config["zsyncCommand"] and availablePackage['zsyncFile'] and localPackageFound:
			if not zsync:
				self.downloadPackage(availablePackage, session, notifier=notifier)
			else:
				if localPackageFound['filename'] != availablePackage['filename']:
					os.rename(os.path.join(self.config["packageDir"], localPackageFound["filename"]), packageFile)
					localPackageFound["filename"] = availablePackage['filename']
				self.zsyncPackage(availablePackage, notifier=notifier)
		else:
			self.downloadPackage(availablePackage, session, notifier=notifier)
		self.cleanupPackages(availablePackage)

	def downloadPackages(self):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		if not any(self.getActiveRepositories()):
			logger.warning("No repositories configured, nothing to do")
			return

		notifier = self._getNotifier()

		try:  # pylint: disable=too-many-nested-blocks
			installedProducts = self.getInstalledProducts()
			localPackages = self.getLocalPackages()
			packages_per_repository = self.get_new_packages_per_repository()
			if not any(packages_per_repository.values()):
				logger.warning("No downloadable packages found")
				return

			newPackages = []
			for repository, downloadablePackages in packages_per_repository.items():
				with self.makeSession(repository) as session:
					for availablePackage in downloadablePackages:
						try:
							#This ís called to keep the logs consistent
							_ = self.get_installed_package(availablePackage, installedProducts)
							localPackageFound = self.get_local_package(availablePackage, localPackages)
							zsync = availablePackage['repository'].baseUrl.split(':')[0].lower().endswith('s')
							if self.is_download_needed(localPackageFound, availablePackage, notifier=notifier):
								self.get_package(availablePackage, localPackageFound, session, zsync=zsync, notifier=notifier)
							packageFile = os.path.join(self.config["packageDir"], availablePackage["filename"])
							self._verifyDownloadedPackage(packageFile, availablePackage, session, zsync, notifier)
							newPackages.append(availablePackage)
						except Exception as exc: # pylint: disable=broad-except
							if self.config.get("ignoreErrors"):
								logger.error("Ignoring Error for package %s: %s", availablePackage["productId"], exc, exc_info=True)
								notifier.appendLine(f"Ignoring Error for package {availablePackage['productId']}: {exc}")
							else:
								raise exc

			if not newPackages:
				logger.notice("No new packages downloaded")
				return
		except Exception as err:  # pylint: disable=broad-except
			notifier.appendLine(f"Error occurred: {err}")
			notifier.setSubject(f"ERROR {self.config['subject']}")
			raise
		finally:
			if notifier and notifier.hasMessage():
				notifier.notify()

	def zsyncPackage(self, availablePackage, notifier=None):
		outFile = os.path.join(self.config["packageDir"], availablePackage["filename"])

		repository = availablePackage['repository']
		with cd(os.path.dirname(outFile)):
			logger.info("Zsyncing %s to %s", availablePackage["packageFile"], outFile)

			cmd = "%s -A %s='%s:%s' -o '%s' %s 2>&1" % (
				self.config["zsyncCommand"],
				repository.baseUrl.split('/')[2].split(':')[0],
				repository.username,
				repository.password,
				outFile,
				availablePackage["zsyncFile"]
			)

			env = {}
			if repository.proxy:
				if repository.proxy != "system":
					env = {
						"http_proxy": repository.proxy,
						"https_proxy": repository.proxy
					}
			else:
				env['no_proxy'] = '*'

			stateRegex = re.compile(r'\s([\d.]+)%\s+([\d.]+)\skBps(.*)$')
			data = b''
			percent = 0.0
			speed = 0
			handle = System.execute(cmd, env=env, getHandle=True)
			while True:
				inp = handle.read(16)
				if not inp:
					handle.close()
					break
				data += inp
				match = stateRegex.search(data.decode())
				if not match:
					continue
				data = match.group(3).encode()
				if (percent == 0) and (float(match.group(1)) == 100):
					continue
				percent = float(match.group(1))
				speed = float(match.group(2)) * 8
				logger.debug('Zsyncing %s: %d%% (%d kbit/s)', availablePackage["packageFile"], percent, speed)

			message = f"Zsync of '{availablePackage['packageFile']}' completed"
			logger.info(message)
			if notifier:
				notifier.appendLine(message)

	def downloadPackage(self, availablePackage, session, notifier=None):  # pylint: disable=too-many-locals
		url = availablePackage["packageFile"]
		outFile = os.path.join(self.config["packageDir"], availablePackage["filename"])

		response = session.get(url, headers=self.httpHeaders, stream=True, timeout=3600*8) # 8h timeout
		if response.status_code < 200 or response.status_code > 299:
			logger.error("Unable to download Package from %s", url)
			raise ConnectionError(f"Unable to download Package from {url}")
		size = int(response.headers.get("Content-length", 0))
		if size:
			logger.info("Downloading %s (%s MB) to %s", url, round(size / (1024.0 * 1024.0), 2), outFile)
		else:
			logger.info("Downloading %s to %s", url, outFile)

		completed = 0.0
		percent = 0.0
		lastTime = time.time()
		lastCompleted = 0
		lastPercent = 0
		speed = 0

		with open(outFile, 'wb') as out:
			for chunk in response.iter_content(chunk_size=32768):
				completed += len(chunk)
				out.write(chunk)

				if size > 0:
					try:
						percent = round(100 * completed / size, 1)
						if lastPercent != percent:
							lastPercent = percent
							now = time.time()
							if not speed or (now - lastTime) > 2:
								speed = 8 * int(((completed - lastCompleted) / (now - lastTime)) / 1024)
								lastTime = now
								lastCompleted = completed
							logger.debug("Downloading %s: %0.1f%% (%0.2f kbit/s)", url, percent, speed)
					except Exception: # pylint: disable=broad-except
						pass

		if size:
			message = f"Download of '{url}' completed (~{formatFileSize(size)})"
		else:
			message = f"Download of '{url}' completed"

		logger.info(message)
		if notifier:
			notifier.appendLine(message)

	def cleanupPackages(self, newPackage):
		logger.info("Cleaning up in %s", self.config["packageDir"])

		try:
			setRights(self.config["packageDir"])
		except Exception as err:  # pylint: disable=broad-except
			logger.warning("Failed to set rights on directory '%s': %s", self.config["packageDir"], err)

		for filename in os.listdir(self.config["packageDir"]):
			path = os.path.join(self.config["packageDir"], filename)
			if not os.path.isfile(path):
				continue
			if path.endswith('.zs-old'):
				os.unlink(path)
				continue

			try:
				productId, version = parseFilename(filename)
			except Exception as err:  # pylint: disable=broad-except
				logger.debug("Parsing '%s' failed: '%s'", filename, err)
				continue

			if productId == newPackage["productId"] and version != newPackage["version"]:
				logger.info("Deleting obsolete package file '%s'", path)
				os.unlink(path)

		packageFile = os.path.join(self.config["packageDir"], newPackage["filename"])

		md5sumFile = f'{packageFile}.md5'
		logger.info("Creating md5sum file '%s'", md5sumFile)

		with open(md5sumFile, 'w') as hashFile:
			hashFile.write(md5sum(packageFile))

		setRights(md5sumFile)

		zsyncFile = f'{packageFile}.zsync'
		logger.info("Creating zsync file '%s'", zsyncFile)
		try:
			zsyncFile = ZsyncFile(zsyncFile)
			zsyncFile.generate(packageFile)
		except Exception as err:  # pylint: disable=broad-except
			logger.error("Failed to create zsync file '%s': %s", zsyncFile, err)

	def onlyNewestPackages(self, packages):  # pylint: disable=no-self-use
		newestPackages = []
		for package in packages:
			found = None
			for i, newPackage in enumerate(newestPackages):
				if newPackage['productId'] == package['productId']:
					found = i
					if compareVersions(package['version'], '>', newestPackages[i]['version']):
						logger.debug(
							"Package version '%s' is newer than version '%s'",
							package['version'], newestPackages[i]['version']
						)
						newestPackages[i] = package
					break

			if found is None:
				newestPackages.append(package)

		return newestPackages

	def getLocalPackages(self):
		return getLocalPackages(
			self.config["packageDir"],
			forceChecksumCalculation=self.config['forceChecksumCalculation']
		)

	def getInstalledProducts(self):
		logger.info("Getting installed products")
		products = []
		configBackend = self.getConfigBackend()
		for product in configBackend.productOnDepot_getHashes(depotId=self.depotId):  # pylint: disable=no-member
			logger.info("Found installed product '%s_%s-%s'", product['productId'], product['productVersion'], product['packageVersion'])
			products.append(product)
		return products

	def getDownloadablePackages(self):
		downloadablePackages = []
		for repository in self.getActiveRepositories():
			logger.info("Getting package infos from repository '%s'", repository.name)
			for package in self.getDownloadablePackagesFromRepository(repository):
				downloadablePackages.append(package)
		return downloadablePackages

	def getDownloadablePackagesFromRepository(self, repository):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		depotConnection = None
		depotRepositoryPath = None
		if repository.opsiDepotId:
			depotConnection = self.getDepotConnection(repository.opsiDepotId, repository.username, repository.password)
			repositoryLocalUrl = depotConnection.getDepot_hash(repository.opsiDepotId).get("repositoryLocalUrl")
			logger.info("Got repository local url '%s' for depot '%s'", repositoryLocalUrl, repository.opsiDepotId)
			if not repositoryLocalUrl or not repositoryLocalUrl.startswith('file://'):
				raise ValueError(f"Invalid repository local url for depot '{repository.opsiDepotId}'")
			depotRepositoryPath = repositoryLocalUrl[7:]

		with self.makeSession(repository) as session:
			packages = []
			errors = set()

			for url in repository.getDownloadUrls():  # pylint: disable=too-many-nested-blocks
				try:
					url = quote(url.encode('utf-8'), safe="/#%[]=:;$&()+,!?*@'~")
					if str(os.environ.get("USE_REPOFILE")).lower() == "true":
						logger.debug("Trying to retrieve packages.json from %s", url)
						try:
							repo_data = None
							if url.startswith("http"):
								repo_data = session.get(f"{url}/packages.json").content
							elif url.startswith("file://"):
								with open(f"{url[7:]}/packages.json", "rb") as file:
									repo_data = file.read()
							else:
								raise ValueError(f"invalid repository url: {url}")

							repo_packages = json.loads(repo_data.decode("utf-8"))["packages"]
							for key, pdict in repo_packages.items():
								link = ".".join([key, "opsi"])
								pdict["repository"] = repository
								pdict["productId"] = pdict.pop("product_id")
								pdict["version"] = f"{pdict.pop('product_version')}-{pdict.pop('package_version')}"
								pdict["packageFile"] = f"{url}/{link}"
								pdict["filename"] = link
								pdict["md5sum"] = pdict.pop("md5sum", None)
								pdict["zsyncFile"] = pdict.pop("zsync_file", None)
								packages.append(pdict)
								logger.info("Found opsi package: %s/%s", url, link)
							continue
						except Exception as err:  # pylint: disable=broad-except
							logger.warning("No repofile found, falling back to scanning the repository")

					response = session.get(url, headers=self.httpHeaders)
					content = response.content.decode("utf-8")
					logger.debug("content: '%s'", content)

					htmlParser = LinksExtractor()
					htmlParser.feed(content)
					htmlParser.close()
					for link in htmlParser.getLinks():
						if not link.endswith('.opsi'):
							continue

						if link.startswith("/"):
							# absolute link to relative link
							path = "/" + url.split("/", 3)[-1]
							rlink = link[len(path):].lstrip("/")
							logger.info("Absolute link: '%s', relative link: '%s'", link, rlink)
							link = rlink

						if repository.includes:
							if not any(include.search(link) for include in repository.includes):
								logger.info("Package '%s' is not included. Please check your includeProductIds-entry in configurationfile.", link)
								continue

						if any(exclude.search(link) for exclude in repository.excludes):
							logger.info("Package '%s' excluded by regular expression", link)
							continue

						try:
							productId, version = parseFilename(link)
							packageFile = url + '/' + link
							logger.info("Found opsi package: %s", packageFile)
							packageInfo = {
								"repository": repository,
								"productId": forceProductId(productId),
								"version": version,
								"packageFile": packageFile,
								"filename": link,
								"md5sum": None,
								"zsyncFile": None
							}
							if depotConnection:
								packageInfo["md5sum"] = depotConnection.getMD5Sum(f"{depotRepositoryPath}/{link}")
							logger.debug("Repository package info: %s", packageInfo)
							packages.append(packageInfo)
						except Exception as err:  # pylint: disable=broad-except
							logger.error("Failed to process link '%s': %s", link, err)

					if not depotConnection:
						# if checking for md5sum only retrieve first 64 bytes of file
						md5getHeader = self.httpHeaders.copy().update({"Range": "bytes=0-64"})
						for link in htmlParser.getLinks():
							isMd5 = link.endswith('.opsi.md5')
							isZsync = link.endswith('.opsi.zsync')

							# stripping directory part from link
							link = link.split("/")[-1]

							filename = None
							if isMd5:
								filename = link[:-4]
							elif isZsync:
								filename = link[:-6]
							else:
								continue

							try:
								for i, package in enumerate(packages):
									if package.get('filename') == filename:
										if isMd5:
											response = session.get(f"{url}/{link}", headers=md5getHeader)
											match = re.search(r'([a-z\d]{32})', response.content.decode("utf-8"))
											if match:
												foundMd5sum = match.group(1)
												packages[i]["md5sum"] = foundMd5sum
												logger.debug("Got md5sum for package %s: %s", filename, foundMd5sum)
										elif isZsync:
											zsyncFile = url + '/' + link
											packages[i]["zsyncFile"] = zsyncFile
											logger.debug("Found zsync file for package '%s': %s", filename, zsyncFile)

										break
							except Exception as err:  # pylint: disable=broad-except
								logger.error("Failed to process link '%s': %s", link, err)
				except Exception as err:  # pylint: disable=broad-except
					logger.debug(err, exc_info=True)
					self.errors.append(err)
					errors.add(str(err))

			if errors:
				logger.warning("Problems processing repository %s: %s", repository.name, '; '.join(str(e) for e in errors))

			return packages

	@contextmanager
	def makeSession(self, repository):  # pylint: disable=no-self-use
		logger.info("opening session for repository %s", repository)
		try:
			session = requests.session()
			if repository.proxy:
				# Use a proxy
				if repository.proxy.lower() != "system":
					session.proxies.update({
						"http": repository.proxy,
						"https": repository.proxy,
					})
					for key in ("http_proxy", "https_proxy"):
						if key in os.environ:
							del os.environ[key]
				os.environ["no_proxy"] = "localhost,127.0.0.1,ip6-localhost,::1"
			else:
				# Do not use a proxy
				os.environ['no_proxy'] = '*'

			if os.path.exists(repository.authcertfile) and os.path.exists(repository.authkeyfile):
				logger.debug("setting session.cert to %s %s", repository.authcertfile, repository.authkeyfile)
				session.cert = (repository.authcertfile, repository.authkeyfile)
			session.verify = repository.verifyCert
			session.auth = (repository.username, repository.password)
			logger.debug("Initiating session with verify=%s", repository.verifyCert)
			yield session
		finally:
			session.close()

def getLocalPackages(packageDirectory, forceChecksumCalculation=False):
	"""
	Show what packages are available in the given `packageDirectory`.

	This function will not traverse into any subdirectories.

	:param packageDirectory: The directory whose packages should be listed.
	:type packageDirectory: str
	:param forceChecksumCalculation: If this is `False` an existing \
`.md5` of a package will be used. If this is `True` then the checksum \
will be calculated for each package independent of the possible \
existance of a corresponding `.md5` file.
	:returns: Information about the found opsi packages. For each \
package there will be the following information: _productId_, \
_version_, _packageFile_ (complete path), _filename_ and _md5sum_.
	:rtype: [{}]
	"""
	logger.info("Getting info for local packages in '%s'", packageDirectory)

	packages = []
	for filename in os.listdir(packageDirectory):
		if not filename.endswith('.opsi'):
			continue

		packageFile = os.path.join(packageDirectory, filename)
		logger.info("Found local package '%s'", packageFile)
		try:
			productId, version = parseFilename(filename)
			checkSumFile = packageFile + '.md5'
			if not forceChecksumCalculation and os.path.exists(checkSumFile):
				logger.debug("Reading existing checksum from %s", checkSumFile)
				with open(checkSumFile) as hashFile:
					packageMd5 = hashFile.read().strip()
			else:
				logger.debug("Calculating checksum for %s", packageFile)
				packageMd5 = md5sum(packageFile)

			packageInfo = {
				"productId": forceProductId(productId),
				"version": version,
				"packageFile": packageFile,
				"filename": filename,
				"md5sum": packageMd5
			}
			logger.debug("Local package info: %s", packageInfo)
			packages.append(packageInfo)
		except Exception as err:  # pylint: disable=broad-except
			logger.error("Failed to process file '%s': %s", filename, err)

	return packages
