# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2019 uib GmbH <info@uib.de>

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
Products.

:copyright: uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import re
import shutil

from OPSI.Config import (
	FILE_ADMIN_GROUP as DEFAULT_CLIENT_DATA_GROUP,
	OPSICONFD_USER as DEFAULT_CLIENT_DATA_USER)
from OPSI.Logger import Logger, LOG_INFO, LOG_ERROR
from OPSI.Util.File.Opsi import PackageControlFile, PackageContentFile
from OPSI.Util.File.Archive import Archive
from OPSI.Util import randomString, findFiles, removeDirectory
from OPSI.System import execute
from OPSI.Types import (forceBool, forceFilename, forcePackageCustomName,
	forceUnicode)

if os.name == 'posix':
	import pwd
	import grp

DEFAULT_TMP_DIR = u'/tmp'
EXCLUDE_DIRS_ON_PACK_REGEX = re.compile(r'(^\.svn$)|(^\.git$)')
EXCLUDE_FILES_ON_PACK_REGEX = re.compile(r'~$')
PACKAGE_SCRIPT_TIMEOUT = 600

logger = Logger()


def _(string):
	return string


class ProductPackageFile:

	def __init__(self, packageFile, tempDir=None):
		self.packageFile = os.path.abspath(forceFilename(packageFile))
		if not os.path.exists(self.packageFile):
			raise IOError(u"Package file '%s' not found" % self.packageFile)

		tempDir = tempDir or DEFAULT_TMP_DIR
		self.tempDir = os.path.abspath(forceFilename(tempDir))

		if not os.path.isdir(self.tempDir):
			raise IOError(u"Temporary directory '%s' not found" % self.tempDir)

		self.clientDataDir = None
		self.tmpUnpackDir = os.path.join(self.tempDir, u'.opsi.unpack.%s' % randomString(5))
		self.packageControlFile = None
		self.clientDataFiles = []

	def cleanup(self):
		logger.info(u"Cleaning up")
		if os.path.isdir(self.tmpUnpackDir):
			shutil.rmtree(self.tmpUnpackDir)
		logger.debug(u"Finished cleaning up")

	def setClientDataDir(self, clientDataDir):
		self.clientDataDir = os.path.abspath(forceFilename(clientDataDir))
		logger.info(u"Client data dir set to '%s'", self.clientDataDir)

	def getProductClientDataDir(self):
		if not self.packageControlFile:
			raise ValueError(u"Metadata not present")

		if not self.clientDataDir:
			raise ValueError(u"Client data dir not set")

		productId = self.packageControlFile.getProduct().getId()
		return os.path.join(self.clientDataDir, productId)

	def uninstall(self):
		logger.info(u"Uninstalling package")
		self.deleteProductClientDataDir()
		logger.debug(u"Finished uninstalling package")

	def deleteProductClientDataDir(self):
		if not self.packageControlFile:
			raise ValueError(u"Metadata not present")

		if not self.clientDataDir:
			raise ValueError(u"Client data dir not set")

		productId = self.packageControlFile.getProduct().getId()
		for f in os.listdir(self.clientDataDir):
			if f.lower() == productId.lower():
				clientDataDir = os.path.join(self.clientDataDir, f)
				logger.info("Deleting client data dir '%s'", clientDataDir)
				removeDirectory(clientDataDir)

	def install(self, clientDataDir, suppressPackageContentFileGeneration=False):
		"""
		Install a package.

		This runs the preinst-script, extracts the data, creates a
		package content file, sets the rights on extracted files, runs
		the postinst and removes temporary files created during the
		installation.

		Setting `suppressPackageContentFileGeneration` to `True` will
		suppress the creation of the package content file.
		"""
		self.setClientDataDir(clientDataDir)
		self.getMetaData()
		self.runPreinst()
		self.extractData()
		if not suppressPackageContentFileGeneration:
			self.createPackageContentFile()
		self.setAccessRights()
		self.runPostinst()
		self.cleanup()

	def unpackSource(self, destinationDir=u'.', newProductId=None, progressSubject=None):
		logger.info(u"Extracting package source from '%s'", self.packageFile)
		if progressSubject:
			progressSubject.setMessage(_(u"Extracting package source from '%s'") % self.packageFile)

		try:
			destinationDir = forceFilename(destinationDir)
			if newProductId:
				newProductId = forceUnicode(newProductId)

			archive = Archive(filename=self.packageFile, progressSubject=progressSubject)

			logger.debug(u"Extracting source from package '%s' to: '%s'", self.packageFile, destinationDir)

			if progressSubject:
				progressSubject.setMessage(_(u'Extracting archives'))
			archive.extract(targetPath=self.tmpUnpackDir)

			for f in os.listdir(self.tmpUnpackDir):
				logger.info(u"Processing file '%s'", f)
				archiveName = u''
				if f.endswith('.cpio.gz'):
					archiveName = f[:-8]
				elif f.endswith('.cpio'):
					archiveName = f[:-5]
				elif f.endswith('.tar.gz'):
					archiveName = f[:-7]
				elif f.endswith('.tar'):
					archiveName = f[:-4]
				elif f.startswith('OPSI'):
					continue
				else:
					logger.warning(u"Unknown content in archive: %s", f)
					continue
				archive = Archive(filename=os.path.join(self.tmpUnpackDir, f), progressSubject=progressSubject)
				if progressSubject:
					progressSubject.setMessage(_(u'Extracting archive %s') % archiveName)
				archive.extract(targetPath=os.path.join(destinationDir, archiveName))

			if newProductId:
				self.getMetaData()
				product = self.packageControlFile.getProduct()
				for scriptName in (u'setupScript', u'uninstallScript', u'updateScript', u'alwaysScript', u'onceScript', u'customScript'):
					script = getattr(product, scriptName)
					if not script:
						continue
					newScript = script.replace(product.id, newProductId)
					if not os.path.exists(os.path.join(destinationDir, u'CLIENT_DATA', script)):
						logger.warning(u"Script file '%s' not found", os.path.join(destinationDir, u'CLIENT_DATA', script))
						continue
					os.rename(os.path.join(destinationDir, u'CLIENT_DATA', script), os.path.join(destinationDir, u'CLIENT_DATA', newScript))
					setattr(product, scriptName, newScript)
				product.setId(newProductId)
				self.packageControlFile.setProduct(product)
				self.packageControlFile.setFilename(os.path.join(destinationDir, u'OPSI', u'control'))
				self.packageControlFile.generate()
			logger.debug(u"Finished extracting package source")
		except Exception as e:
			logger.logException(e, LOG_INFO)
			self.cleanup()
			raise RuntimeError(u"Failed to extract package source from '%s': %s" % (self.packageFile, e))

	def getMetaData(self, output_dir=None):
		if self.packageControlFile:
			# Already done
			return

		logger.info(u"Getting meta data from package '%s'", self.packageFile)

		try:
			if not os.path.exists(self.tmpUnpackDir):
				os.mkdir(self.tmpUnpackDir)
				os.chmod(self.tmpUnpackDir, 0o700)

			metaDataTmpDir = os.path.join(self.tmpUnpackDir, u'OPSI')
			archive = Archive(self.packageFile)

			logger.debug(u"Extracting meta data from package '%s' to: '%s'", self.packageFile, metaDataTmpDir)
			archive.extract(targetPath=metaDataTmpDir, patterns=[u"OPSI*"])

			metadataArchives = []
			for f in os.listdir(metaDataTmpDir):
				if not f.endswith((u'.cpio.gz', u'.tar.gz', u'.cpio', u'.tar')):
					logger.warning(u"Unknown content in archive: %s", f)
					continue
				logger.debug(u"Metadata archive found: %s", f)
				metadataArchives.append(f)
			if not metadataArchives:
				raise ValueError(u"No metadata archive found")
			if len(metadataArchives) > 2:
				raise ValueError(u"More than two metadata archives found")

			# Sorting to unpack custom version metadata at last
			metadataArchives.sort()

			for metadataArchive in metadataArchives:
				archive = Archive(os.path.join(metaDataTmpDir, metadataArchive))

				if output_dir is None:
					archive.extract(targetPath=metaDataTmpDir)
				else:
					archive.extract(targetPath=output_dir)
			if output_dir is not None:
				return			# to work on the whole extracted metadata directory

			packageControlFile = os.path.join(metaDataTmpDir, u'control')
			if not os.path.exists(packageControlFile):
				raise IOError(u"No control file found in package metadata archives")

			self.packageControlFile = PackageControlFile(packageControlFile)
			self.packageControlFile.parse()

		except Exception as e:
			logger.logException(e)
			self.cleanup()
			raise RuntimeError(u"Failed to get metadata from package '%s': %s" % (self.packageFile, e))
		logger.debug(u"Got meta data from package '%s'", self.packageFile)
		return self.packageControlFile

	def extractData(self):
		logger.info(u"Extracting data from package '%s'", self.packageFile)

		try:
			if not self.packageControlFile:
				raise ValueError(u"Metadata not present")

			if not self.clientDataDir:
				raise ValueError(u"Client data dir not set")

			self.clientDataFiles = []

			archive = Archive(self.packageFile)

			logger.info(u"Extracting data from package '%s' to: '%s'", self.packageFile, self.tmpUnpackDir)
			archive.extract(targetPath=self.tmpUnpackDir, patterns=[u"CLIENT_DATA*", u"SERVER_DATA*"])

			clientDataArchives = []
			serverDataArchives = []
			for f in os.listdir(self.tmpUnpackDir):
				if f.startswith('OPSI'):
					continue

				if not f.endswith((u'.cpio.gz', u'.tar.gz', u'.cpio', u'.tar')):
					logger.warning(u"Unknown content in archive: %s", f)
					continue

				if f.startswith('CLIENT_DATA'):
					logger.debug(u"Client-data archive found: %s", f)
					clientDataArchives.append(f)
				elif f.startswith('SERVER_DATA'):
					logger.debug(u"Server-data archive found: %s", f)
					serverDataArchives.append(f)

			if not clientDataArchives:
				logger.warning(u"No client-data archive found")
			if len(clientDataArchives) > 2:
				raise ValueError(u"More than two client-data archives found")
			if len(serverDataArchives) > 2:
				raise ValueError(u"More than two server-data archives found")

			# Sorting to unpack custom version data at last
			def psort(name):
				return re.sub(r'(\.tar|\.tar\.gz|\.cpio|\.cpio\.gz)$', '', name)

			clientDataArchives = sorted(clientDataArchives, key=psort)
			serverDataArchives = sorted(serverDataArchives, key=psort)

			for serverDataArchive in serverDataArchives:
				archiveFile = os.path.join(self.tmpUnpackDir, serverDataArchive)
				logger.info(u"Extracting server-data archive '%s' to '/'" % archiveFile)
				archive = Archive(archiveFile)
				archive.extract(targetPath=u'/')

			productClientDataDir = self.getProductClientDataDir()
			if not os.path.exists(productClientDataDir):
				os.mkdir(productClientDataDir)
				os.chmod(productClientDataDir, 0o2770)

			for clientDataArchive in clientDataArchives:
				archiveFile = os.path.join(self.tmpUnpackDir, clientDataArchive)
				logger.info(u"Extracting client-data archive '%s' to '%s'", archiveFile, productClientDataDir)
				archive = Archive(archiveFile)
				archive.extract(targetPath=productClientDataDir)

			logger.debug(u"Finished extracting data from package")
		except Exception as e:
			self.cleanup()
			raise RuntimeError(u"Failed to extract data from package '%s': %s" % (self.packageFile, e))

	def getClientDataFiles(self):
		if self.clientDataFiles:
			return self.clientDataFiles

		self.clientDataFiles = findFiles(self.getProductClientDataDir())
		return self.clientDataFiles

	def setAccessRights(self):
		logger.info(u"Setting access rights of client-data files")

		if os.name != 'posix':
			raise NotImplementedError(u"setAccessRights not implemented on windows")

		try:
			if not self.packageControlFile:
				raise ValueError(u"Metadata not present")

			if not self.clientDataDir:
				raise ValueError(u"Client data dir not set")

			productClientDataDir = self.getProductClientDataDir()

			uid = -1
			if os.geteuid() == 0:
				uid = pwd.getpwnam(DEFAULT_CLIENT_DATA_USER)[2]
			gid = grp.getgrnam(DEFAULT_CLIENT_DATA_GROUP)[2]

			os.chown(productClientDataDir, uid, gid)
			os.chmod(productClientDataDir, 0o2770)

			for filename in self.getClientDataFiles():
				path = os.path.join(productClientDataDir, filename)

				try:
					if os.path.islink(path):
						continue
					logger.debug(u"Setting owner of '%s' to '%s:%s'", path, uid, gid)
					os.chown(path, uid, gid)
				except Exception as e:
					raise RuntimeError(u"Failed to change owner of '%s' to '%s:%s': %s" % (path, uid, gid, e))

				mode = None
				try:
					if os.path.islink(path):
						continue
					elif os.path.isdir(path):
						logger.debug(u"Setting rights on directory '%s'", path)
						mode = 0o2770
					elif os.path.isfile(path):
						logger.debug(u"Setting rights on file '%s'", path)
						mode = (os.stat(path)[0] | 0o660) & 0o770

					if mode is not None:
						os.chmod(path, mode)
				except Exception as error:
					if mode is None:
						raise RuntimeError(u"Failed to set access rights of '%s': %s" % (path, error))
					else:
						raise RuntimeError(u"Failed to set access rights of '%s' to '%o': %s" % (path, mode, error))
			logger.debug(u"Finished setting access rights of client-data files")
		except Exception as e:
			self.cleanup()
			raise RuntimeError(u"Failed to set access rights of client-data files of package '%s': %s" % (self.packageFile, e))

	def createPackageContentFile(self):
		logger.info(u"Creating package content file")

		try:
			if not self.packageControlFile:
				raise ValueError(u"Metadata not present")

			if not self.clientDataDir:
				raise ValueError(u"Client data dir not set")

			productId = self.packageControlFile.getProduct().getId()
			productClientDataDir = self.getProductClientDataDir()
			packageContentFilename = productId + u'.files'
			packageContentFile = os.path.join(productClientDataDir, packageContentFilename)

			packageContentFile = PackageContentFile(packageContentFile)
			packageContentFile.setProductClientDataDir(productClientDataDir)
			cdf = self.getClientDataFiles()
			try:
				# The package content file will be re-written and
				# then the hash will be different so we need to remove
				# this before the generation.
				cdf.remove(packageContentFilename)
			except ValueError:
				pass  # not in list
			packageContentFile.setClientDataFiles(cdf)
			packageContentFile.generate()

			cdf.append(packageContentFilename)
			self.clientDataFiles = cdf
			logger.debug(u"Finished creating package content file")
		except Exception as e:
			logger.logException(e)
			self.cleanup()
			raise RuntimeError(u"Failed to create package content file of package '%s': %s" % (self.packageFile, e))
	
	"""
	def _replacePythonShebang(self, script):
		with open(script, "rb") as f:
			data = f.read()
		idx = data.index(b"\n")
		if idx == -1:
			return
		shebang = data[:idx]
		if not shebang.strip().rstrip(b"3").endswith(b"python"):
			return
		logger.info("Replacing interpreter %s with /usr/bin/opsi-python", shebang[2:].strip())
		data = b"#!/usr/bin/opsi-python" + data[idx:]
		with open(script, "wb") as f:
			f.write(data)
	"""

	def _runPackageScript(self, scriptName, env={}):
		logger.info(u"Attempt to run package script %s", scriptName)
		try:
			if not self.packageControlFile:
				raise ValueError(u"Metadata not present")

			if not self.clientDataDir:
				raise ValueError(u"Client data dir not set")
			
			clientDataDir = self.getProductClientDataDir()
			script = os.path.join(self.tmpUnpackDir, u'OPSI', scriptName)
			if not os.path.exists(script):
				logger.info(u"Package script '%s' not found", scriptName)
				return []
			
			with open(script, "rb") as f:
				data = f.read()
			if data.startswith(b"#!"):
				new_data = re.sub(b"(^|\s|/)python3?(\s+)", b'\g<1>opsi-python\g<2>', data)
				if b"\r\n" in data:
					logger.info(u"Replacing dos line breaks in %s", script)
					new_data = new_data.replace(b"\r\n", b"\n")
				if data != new_data:
					with open(script, "wb") as f:
						f.write(new_data)
			
			"""
			self._replacePythonShebang(script)
			for match in re.finditer(b"\${?CLIENT_DATA_DIR}?/(\S+\.py)", data):
				pyScript = os.path.join(clientDataDir, match.group(1).decode("utf8"))
				logger.info("Found python script %s in package script %s", pyScript, scriptName)
				if os.path.exists(pyScript):
					self._replacePythonShebang(pyScript)
			"""

			logger.notice(u"Running package script '%s'", scriptName)
			os.chmod(script, 0o700)

			sp_env = {
				'PRODUCT_ID': self.packageControlFile.getProduct().getId(),
				'PRODUCT_TYPE': self.packageControlFile.getProduct().getType(),
				'PRODUCT_VERSION': self.packageControlFile.getProduct().getProductVersion(),
				'PACKAGE_VERSION': self.packageControlFile.getProduct().getPackageVersion(),
				'CLIENT_DATA_DIR': clientDataDir
			}
			sp_env.update(env)
			logger.debug("Package script env: %s", sp_env)
			return execute(script, timeout=PACKAGE_SCRIPT_TIMEOUT, env=sp_env)
		except Exception as error:
			logger.logException(error, LOG_ERROR)
			self.cleanup()
			raise RuntimeError(u"Failed to execute package script '%s' of package '%s': %s" % (scriptName, self.packageFile, error))
		finally:
			logger.debug(u"Finished running package script %s", scriptName)

	def runPreinst(self, env={}):
		return self._runPackageScript(u'preinst', env=env)

	def runPostinst(self, env={}):
		return self._runPackageScript(u'postinst', env=env)


class ProductPackageSource:

	def __init__(self, packageSourceDir, tempDir=None, customName=None, customOnly=False, packageFileDestDir=None, format='cpio', compression='gzip', dereference=False):
		self.packageSourceDir = os.path.abspath(forceFilename(packageSourceDir))
		if not os.path.isdir(self.packageSourceDir):
			raise IOError(u"Package source directory '%s' not found" % self.packageSourceDir)

		tempDir = tempDir or DEFAULT_TMP_DIR
		self.tempDir = os.path.abspath(forceFilename(tempDir))
		if not os.path.isdir(self.tempDir):
			raise IOError(u"Temporary directory '%s' not found" % self.tempDir)

		self.customName = None
		if customName:
			self.customName = forcePackageCustomName(customName)

		self.customOnly = forceBool(customOnly)

		if format:
			if format not in (u'cpio', u'tar'):
				raise ValueError(u"Format '%s' not supported" % format)
			self.format = format
		else:
			self.format = u'cpio'

		if not compression:
			self.compression = None
		else:
			if compression not in (u'gzip', u'bzip2'):
				raise ValueError(u"Compression '%s' not supported" % compression)
			self.compression = compression

		self.dereference = forceBool(dereference)

		if not packageFileDestDir:
			packageFileDestDir = self.packageSourceDir
		packageFileDestDir = os.path.abspath(forceFilename(packageFileDestDir))
		if not os.path.isdir(packageFileDestDir):
			raise IOError(u"Package destination directory '%s' not found" % packageFileDestDir)

		packageControlFile = os.path.join(self.packageSourceDir, u'OPSI', u'control')
		if customName and os.path.exists(os.path.join(self.packageSourceDir, u'OPSI.%s' % customName, u'control')):
			packageControlFile = os.path.join(self.packageSourceDir, u'OPSI.%s' % customName, u'control')
		self.packageControlFile = PackageControlFile(packageControlFile)
		self.packageControlFile.parse()

		customName = u''
		if self.customName:
			customName = u'~%s' % self.customName
		self.packageFile = os.path.join(packageFileDestDir, u"%s_%s-%s%s.opsi" % (
				self.packageControlFile.getProduct().id,
				self.packageControlFile.getProduct().productVersion,
				self.packageControlFile.getProduct().packageVersion,
				customName))

		self.tmpPackDir = os.path.join(self.tempDir, u'.opsi.pack.%s' % randomString(5))

	def getPackageFile(self):
		return self.packageFile

	def cleanup(self):
		logger.info(u"Cleaning up")
		if os.path.isdir(self.tmpPackDir):
			shutil.rmtree(self.tmpPackDir)
		logger.debug(u"Finished cleaning up")

	def pack(self, progressSubject=None):
		# Create temporary directory
		if os.path.exists(self.tmpPackDir):
			shutil.rmtree(self.tmpPackDir)
		os.mkdir(self.tmpPackDir)

		archives = []
		diskusage = 0
		dirs = [u'CLIENT_DATA', u'SERVER_DATA', u'OPSI']

		try:
			if self.customName:
				found = False
				for i, currentDir in enumerate(dirs):
					customDir = u"%s.%s" % (currentDir, self.customName)
					if os.path.exists(os.path.join(self.packageSourceDir, customDir)):
						found = True
						if self.customOnly:
							dirs[i] = customDir
						else:
							dirs.append(customDir)
				if not found:
					raise RuntimeError(u"No custom dirs found for '%s'" % self.customName)

			# Try to define diskusage from Sourcedirectory to prevent a override from cpio sizelimit.
			for d in dirs:
				if not os.path.exists(os.path.join(self.packageSourceDir, d)) and d != u'OPSI':
					logger.info(u"Directory '%s' does not exist", os.path.join(self.packageSourceDir, d))
					continue
				fileList = findFiles(
					os.path.join(self.packageSourceDir, d),
					excludeDir=EXCLUDE_DIRS_ON_PACK_REGEX,
					excludeFile=EXCLUDE_FILES_ON_PACK_REGEX,
					followLinks=self.dereference)
				if fileList:
					for f in fileList:
						diskusage = diskusage + os.path.getsize(os.path.join(self.packageSourceDir, d, f))

			if diskusage >= 2147483648:
				logger.info(u"Switching to tar format, because sourcefiles overrides cpio sizelimit.")
				self.format = u'tar'

			for d in dirs:
				if not os.path.exists(os.path.join(self.packageSourceDir, d)) and d != u'OPSI':
					logger.info(u"Directory '%s' does not exist", os.path.join(self.packageSourceDir, d))
					continue

				fileList = findFiles(
					os.path.join(self.packageSourceDir, d),
					excludeDir=EXCLUDE_DIRS_ON_PACK_REGEX,
					excludeFile=EXCLUDE_FILES_ON_PACK_REGEX,
					followLinks=self.dereference)

				if d.startswith(u'SERVER_DATA'):
					# Never change permissions of existing directories in /
					tmp = []
					for f in fileList:
						if f.find(os.sep) == -1:
							logger.info(u"Skipping dir '%s'", f)
							continue
						tmp.append(f)

					fileList = tmp

				if not fileList:
					logger.notice(u"Skipping empty dir '%s'", os.path.join(self.packageSourceDir, d))
					continue

				filename = os.path.join(self.tmpPackDir, u'%s.%s' % (d, self.format))
				if self.compression == 'gzip':
					filename += u'.gz'
				elif self.compression == 'bzip2':
					filename += u'.bz2'
				archive = Archive(filename, format=self.format, compression=self.compression, progressSubject=progressSubject)
				if progressSubject:
					progressSubject.reset()
					progressSubject.setMessage(u'Creating archive %s' % os.path.basename(archive.getFilename()))
				archive.create(fileList=fileList, baseDir=os.path.join(self.packageSourceDir, d), dereference=self.dereference)
				archives.append(filename)

			archive = Archive(self.packageFile, format=self.format, compression=None, progressSubject=progressSubject)
			if progressSubject:
				progressSubject.reset()
				progressSubject.setMessage(u'Creating archive %s' % os.path.basename(archive.getFilename()))
			archive.create(fileList=archives, baseDir=self.tmpPackDir)
		except Exception as error:
			self.cleanup()
			raise RuntimeError(u"Failed to create package '%s': %s" % (self.packageFile, error))
