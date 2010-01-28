#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Product   =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH
   
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
   
   @copyright: uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.4.99'

# Globals
DEFAULT_TMP_DIR               = u'/tmp'
DEFAULT_CLIENT_DATA_GROUP     = 'pcpatch'
DEFAULT_CLIENT_DATA_FILE_MODE = 0660
DEFAULT_CLIENT_DATA_DIR_MODE  = 0770

# Imports
import os, pwd, grp, shutil

# OPSI imports
from OPSI.Logger import *
from OPSI.Util.File.Opsi import PackageControlFile, PackageContentFile
from OPSI.Util.File.Archive import *
from OPSI.Util import randomString
from OPSI.System import execute

logger = Logger()

def _(string):
	return string

class ProductPackageFile(object):
	
	def __init__(self, packageFile, tempDir = None):
		self.packageFile = forceFilename(packageFile)
		if not tempDir:
			tempDir = DEFAULT_TMP_DIR
		tempDir = forceFilename(tempDir)
		if not os.path.isdir(tempDir):
			raise Exception(u"Temporary directory '%s' not found" % tempDir)
		
		self.tempDir                  = os.path.abspath(tempDir)
		self.clientDataDir            = None
		self.installedFiles           = []
		self.tmpUnpackDir             = os.path.join( self.tempDir, u'.opsi.unpack.%s' % randomString(5) )
		self.packageControlFile       = None
		self.installedClientDataFiles = []
		self.installedServerDataFiles = []
		
	def cleanup(self):
		logger.info(u"Cleaning up")
		if os.path.isdir(self.tmpUnpackDir):
			shutil.rmtree(self.tmpUnpackDir)
	
	def setClientDataDir(self, clientDataDir):
		self.clientDataDir = os.path.abspath(forceFilename(clientDataDir))
		logger.info(u"Client data dir set to '%s'" % self.clientDataDir)
	
	def getProductClientDataDir(self):
		if not self.packageControlFile:
			raise Exception(u"Metadata not present")
		
		if not self.clientDataDir:
			raise Exception(u"Client data dir not set")
		
		productId = self.packageControlFile.getProduct().getId()
		return os.path.join(self.clientDataDir, productId)
	
	def uninstall(self):
		logger.notice(u"Uninstalling package")
		self.deleteProductClientDataDir()
	
	def deleteProductClientDataDir(self):
		if not self.packageControlFile:
			raise Exception(u"Metadata not present")
		
		if not self.clientDataDir:
			raise Exception(u"Client data dir not set")
		
		productId = self.packageControlFile.getProduct().getId()
		for f in os.listdir(self.clientDataDir):
			if (f.lower() == productId.lower()):
				clientDataDir = os.path.join(self.clientDataDir, f)
				logger.info("Deleting client data dir '%s'" % clientDataDir)
				shutil.rmtree(clientDataDir)
		
	def install(self, clientDataDir):
		self.setClientDataDir(clientDataDir)
		self.getMetaData()
		self.runPreinst()
		self.extractData()
		self.createPackageContentFile()
		self.setAccessRights()
		self.runPostinst()
		self.cleanup()
	
	def unpackSource(self, destinationDir=u'', newProductId=u'', progressSubject=None):
		logger.notice(u"Extracting package source from '%s'" % self.packageFile)
		if progressSubject: progressSubject.setMessage(_(u"Extracting package source from '%s'") % self.packageFile)
		try:
			destinationDir = forceFilename(destinationDir)
			newProductId   = forceUnicode(newProductId)
			
			archive = Archive(filename = self.packageFile, progressSubject = progressSubject)
			
			logger.debug(u"Extracting source from package '%s' to: '%s'" % (self.packageFile, destinationDir))
			
			if progressSubject: progressSubject.setMessage(_(u'Extracting archives'))
			archive.extract(targetPath = self.tmpUnpackDir)
			
			for f in os.listdir(self.tmpUnpackDir):
				archiveName = u''
				if   f.endswith('.cpio.gz'):
					archiveName = f[:-8]
				elif f.endswith('.cpio'):
					archiveName = f[:-5]
				elif f.endswith('.tar.gz'):
					archiveName = f[:-7]
				elif f.endswith('tar'):
					archiveName = f[:-4]
				else:
					logger.warning(u"Unknown content in archive: %s" % f)
					continue
				archive = Archive(filename = os.path.join(self.tmpUnpackDir, f), progressSubject = progressSubject)
				if progressSubject: progressSubject.setMessage(_(u'Extracting archive %s') % archiveName)
				archive.extract(targetPath = os.path.join(destinationDir, archiveName))
			
			if newProductId:
				self.getMetaData()
				product = self.packageControlFile.getProduct()
				for scriptName in (u'setupScript', u'uninstallScript', u'updateScript', u'alwaysScript', u'onceScript', u'customScript'):
					script = getattr(product, scriptName)
					if not script:
						continue
					newScript = script.replace(product.id, newProductId)
					os.rename(os.path.join(destinationDir, u'CLIENT_DATA', script), os.path.join(destinationDir, u'CLIENT_DATA', newScript))
					setattr(product, scriptName, newScript)
				product.setId(newProductId)
				self.packageControlFile.setProduct(product)
				self.packageControlFile.setFilename(os.path.join(destinationDir, u'OPSI', u'control'))
				self.packageControlFile.generate()
				
		except Exception, e:
			self.cleanup()
			raise Exception(u"Failed to extract package source from '%s': %s" % (self.packageFile, e))
		
	def getMetaData(self):
		if self.packageControlFile:
			# Already done
			return
		logger.notice(u"Getting meta data from package '%s'" % self.packageFile)
		try:
			if not os.path.exists(self.tmpUnpackDir):
				os.mkdir(self.tmpUnpackDir)
				os.chmod(self.tmpUnpackDir, 0700)
			
			metaDataTmpDir = os.path.join(self.tmpUnpackDir, u'OPSI')
			archive = Archive(self.packageFile)
			
			logger.debug(u"Extracting meta data from package '%s' to: '%s'" % (self.packageFile, metaDataTmpDir))
			archive.extract(targetPath = metaDataTmpDir, patterns=[u"OPSI*"])
			
			metadataArchives = []
			for f in os.listdir(metaDataTmpDir):
				if not f.endswith(u'.cpio.gz') and not f.endswith(u'.tar.gz') and not f.endswith(u'.cpio') and not f.endswith(u'.tar'):
					logger.warning(u"Unknown content in archive: %s" % f)
					continue
				logger.debug(u"Metadata archive found: %s" % f)
				metadataArchives.append(f)
			if not metadataArchives:
				raise Exception(u"No metadata archive found")
			if (len(metadataArchives) > 2):
				raise Exception(u"More than two metadata archives found")
			
			# Sorting to unpack custom version metadata at last
			metadataArchives.sort()
			metadataArchives.reverse()
			
			for metadataArchive in metadataArchives:
				archive = Archive( os.path.join(metaDataTmpDir, metadataArchive) )
				archive.extract(targetPath = metaDataTmpDir)
			
			packageControlFile = os.path.join(metaDataTmpDir, u'control')
			if not os.path.exists(packageControlFile):
				raise Exception(u"No control file found in package metadata archives")
			
			self.packageControlFile = PackageControlFile(packageControlFile)
			self.packageControlFile.parse()
			
		except Exception, e:
			logger.logException(e)
			self.cleanup()
			raise Exception(u"Failed to get metadata from package '%s': %s" % (self.packageFile, e))
		logger.debug(u"Got meta data from package '%s'" % self.packageFile)
		return self.packageControlFile
		
	def extractData(self):
		logger.notice(u"Extracting data from package '%s'" % self.packageFile)
		try:
			if not self.packageControlFile:
				raise Exception(u"Metadata not present")
			
			if not self.clientDataDir:
				raise Exception(u"Client data dir not set")
			
			archive = Archive(self.packageFile)
			
			logger.debug(u"Extracting data from package '%s' to: '%s'" % (self.packageFile, self.tmpUnpackDir))
			archive.extract(targetPath = self.tmpUnpackDir, patterns=[u"CLIENT_DATA*", u"SERVER_DATA*"])
			
			clientDataArchives = []
			serverDataArchives = []
			for f in os.listdir(self.tmpUnpackDir):
				if f.startswith('OPSI'):
					continue
				if not f.endswith(u'.cpio.gz') and not f.endswith(u'.tar.gz') and not f.endswith(u'.cpio') and not f.endswith(u'.tar'):
					logger.warning(u"Unknown content in archive: %s" % f)
					continue
				if   f.startswith('CLIENT_DATA'):
					logger.debug(u"Client-data archive found: %s" % f)
					clientDataArchives.append(f)
				elif f.startswith('SERVER_DATA'):
					logger.debug(u"Server-data archive found: %s" % f)
					serverDataArchives.append(f)
				
			if not clientDataArchives:
				logger.warning(u"No client-data archive found")
			if (len(clientDataArchives) > 2):
				raise Exception(u"More than two client-data archives found")
			if (len(serverDataArchives) > 2):
				raise Exception(u"More than two server-data archives found")
			
			# Sorting to unpack custom version data at last
			clientDataArchives.sort()
			clientDataArchives.reverse()
			serverDataArchives.sort()
			serverDataArchives.reverse()
			
			self.installedServerDataFiles = []
			for serverDataArchive in serverDataArchives:
				archiveFile = os.path.join(self.tmpUnpackDir, serverDataArchive)
				logger.info(u"Extracting server-data archive '%s' to '/'" % archiveFile)
				archive = Archive(archiveFile)
				for filename in archive.content():
					self.installedServerDataFiles.append(filename)
				archive.extract(targetPath = u'/')
			self.installedServerDataFiles.sort()
			
			productClientDataDir = self.getProductClientDataDir()
			if not os.path.exists(productClientDataDir):
				os.mkdir(productClientDataDir)
			
			self.installedClientDataFiles = []
			for clientDataArchive in clientDataArchives:
				archiveFile = os.path.join(self.tmpUnpackDir, clientDataArchive)
				logger.info(u"Extracting client-data archive '%s' to '%s'" % (archiveFile, productClientDataDir))
				archive = Archive(archiveFile)
				for filename in archive.content():
					self.installedClientDataFiles.append(filename)
				archive.extract(targetPath = productClientDataDir)
			self.installedClientDataFiles.sort()
			
		except Exception, e:
			self.cleanup()
			raise Exception(u"Failed to extract data from package '%s': %s" % (self.packageFile, e))
	
	def setAccessRights(self):
		logger.notice(u"Setting access rights of client-data files")
		try:
			if not self.packageControlFile:
				raise Exception(u"Metadata not present")
			
			if not self.clientDataDir:
				raise Exception(u"Client data dir not set")
			
			user = pwd.getpwuid(os.getuid())[0]
			productClientDataDir = self.getProductClientDataDir()
			
			for filename in self.installedClientDataFiles:
				path = os.path.join(productClientDataDir, filename)
				
				(mode, group) = (DEFAULT_CLIENT_DATA_FILE_MODE, DEFAULT_CLIENT_DATA_GROUP)
				
				if os.path.isdir(path):
					mode = DEFAULT_CLIENT_DATA_DIR_MODE
				
				logger.info(u"Setting owner of '%s' to '%s:%s'" % (path, user, group))
				try:
					os.chown(path, pwd.getpwnam(user)[2], grp.getgrnam(group)[2])
				except Exception, e:
					raise Exception(u"Failed to change owner of '%s' to '%s:%s': %s" % (path, user, group, e))
				
				logger.info(u"Setting access rights of '%s' to '%o'" % (path, mode))
				try:
					os.chmod(path, mode)
				except Exception, e:
					raise Exception(u"Failed to set access rights of '%s' to '%o': %s" % (path, mode, e))
		except Exception, e:
			self.cleanup()
			raise Exception(u"Failed to set access rights of client-data files of package '%s': %s" % (self.packageFile, e))
		
	def createPackageContentFile(self):
		logger.notice(u"Creating package content file")
		try:
			if not self.packageControlFile:
				raise Exception(u"Metadata not present")
			
			if not self.clientDataDir:
				raise Exception(u"Client data dir not set")
			
			productId = self.packageControlFile.getProduct().getId()
			productClientDataDir = self.getProductClientDataDir()
			packageContentFile = os.path.join(productClientDataDir, productId + u'.files')
			
			packageContentFile = PackageContentFile(packageContentFile)
			packageContentFile.setProductClientDataDir(productClientDataDir)
			packageContentFile.setClientDataFiles(self.installedClientDataFiles)
			packageContentFile.generate()
			
			self.installedClientDataFiles.append(productId + u'.files')
			
		except Exception, e:
			self.cleanup()
			raise Exception(u"Failed to create package content file of package '%s': %s" % (self.packageFile, e))
		
	def _runPackageScript(self, scriptName):
		logger.notice(u"Running package script '%s'" % scriptName)
		try:
			if not self.packageControlFile:
				raise Exception(u"Metadata not present")
			
			if not self.clientDataDir:
				raise Exception(u"Client data dir not set")
			
			script = os.path.join(self.tmpUnpackDir, u'OPSI', scriptName)
			if not os.path.exists(script):
				logger.warning(u"Package script '%s' not found" % scriptName)
				return []
			
			os.chmod(script, 0700)
			
			productId = self.packageControlFile.getProduct().getId()
			productClientDataDir = self.getProductClientDataDir()
			
			os.putenv('PRODUCT_ID',      productId)
			os.putenv('CLIENT_DATA_DIR', productClientDataDir)
			
			return execute(script)
		except Exception, e:
			self.cleanup()
			raise Exception(u"Failed to execute package script '%s' of package '%s': %s" % (scriptName, self.packageFile, e))
		
	def runPreinst(self):
		return self._runPackageScript(u'preinst')
	
	def runPostinst(self):
		return self._runPackageScript(u'postinst')
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
