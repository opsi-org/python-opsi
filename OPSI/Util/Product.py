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
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '3.4.99'

# Globals
DEFAULT_TMP_DIR = u'/tmp'

# Imports
import os, shutil

# OPSI imports
from OPSI.Logger import *
from OPSI.Util.File.Opsi import PackageControlFile
from OPSI.Util.File.Archive import *
from OPSI.Util import randomString

logger = Logger()

class ProductPackageFile(ProductPackage):
	
	def __init__(self, packageFile, tempDir = None):
		self.packageFile = forceFilename(packageFile)
		if not tempDir:
			tempDir = DEFAULT_TMP_DIR
		tempDir = forceFilename(tempDir)
		if not os.path.isdir(tempDir):
			raise Exception(u"Temporary directory '%s' not found" % tempDir)
		
		self.tempDir        = os.path.abspath(tempDir)
		self.clientDataDir  = None
		self.installedFiles = []
		self.tmpUnpackDir   = os.path.join( self.tempDir, u'.opsi.unpack.%s' % randomString(5) )
		
		self.getMetaData()
		
		self.clientDataDir = os.path.join('/tmp', self.productId)
	
	def cleanup(self):
		if os.path.isdir(self.tmpUnpackDir):
			shutil.rmtree(self.tmpUnpackDir)
	
	def getMetaData(self):
		archive = Archive(self.packageFile)
		try:
			logger.notice(u"Extracting meta data from archive content to: '%s'" % self.tmpUnpackDir)
			archive.extract(targetPath = self.tmpUnpackDir, patterns=[u"OPSI*"])
			
			metadataArchives = []
			basenames = []
			for f in os.listdir(self.tmpUnpackDir):
				if not f.endswith(u'.cpio.gz') and not f.endswith(u'.tar.gz') and not f.endswith(u'.cpio') and not f.endswith(u'.tar'):
					logger.warning(u"Unknown content in archive: %s" % f)
					continue
				logger.debug(u"Metadata archive found: %s" % f)
				metadataArchives.append(metadataArchives)
			if not metadataArchives:
				raise Exception(u"No metadata archive found")
			if (len(metadataArchives) > 2):
				raise Exception(u"More than two metadata archives found")
			
			# Sorting to unpack custom version metadata at last
			metadataArchives.sort()
			metadataArchives.reverse()
			
			for metadataArchive in metadataArchives:
				archive = Archive( os.path.join(self.tmpUnpackDir, metadataArchive) )
				archive.extract(targetPath = self.tmpUnpackDir)
			
			packageControlFile = os.path.join(self.tmpUnpackDir, u'control')
			if not os.path.exists(packageControlFile):
				raise Exception(u"No control file found in package metadata archives")
		except Exception, e:
			self.cleanup()
			raise
		
	def unpack(self, dataArchives=True):
		archive = Archive(self.packageFile)
		
		prevUmask = os.umask(0077)
		# Create temporary directory
		if os.path.exists(self.tmpUnpackDir):
			shutil.rmtree(self.tmpUnpackDir)
		os.umask(prevUmask)
		os.mkdir(self.tmpUnpackDir)
		try:
			if dataArchives:
				logger.notice(u"Extracting archive content to: '%s'" % self.tmpUnpackDir)
				archive.extract(targetPath = self.tmpUnpackDir)
			else:
				
			
			
		except Exception, e:
			self.cleanup()
			raise
		
		names = [u'OPSI']
		if dataArchives:
			os.mkdir( self.clientDataDir )
			self.installedFiles.append( self.clientDataDir )
			names.extend( [u'SERVER_DATA', u'CLIENT_DATA'] )
		
		
		for name in names:
			archives = []
			if os.path.exists( os.path.join(self.tmpUnpackDir, name + '.tar.gz') ):
				archives.append( os.path.join(self.tmpUnpackDir, name + '.tar.gz') )
			elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.tar') ):
				archives.append( os.path.join(self.tmpUnpackDir, name + '.tar') )
			elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.cpio.gz') ):
				archives.append( os.path.join(self.tmpUnpackDir, name + '.cpio.gz') )
			elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.cpio') ):
				archives.append( os.path.join(self.tmpUnpackDir, name + '.cpio') )
			
			if self.customName:
				if os.path.exists( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.tar.gz') ):
					archives.append( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.tar.gz') )
				elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.tar') ):
					archives.append( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.tar') )
				elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.cpio.gz') ):
					archives.append( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.cpio.gz') )
				elif os.path.exists( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.cpio') ):
					archives.append( os.path.join(self.tmpUnpackDir, name + '.' + self.customName + '.cpio') )
			
			if not archives:
				if (name == 'OPSI'):
					raise Exception("Bad package: OPSI.{cpio|tar}[.gz] not found.")
				else:
					logger.warning("No %s archive found." % name)
			
			dstDir = self.tmpUnpackDir
			if (name == 'SERVER_DATA'):
				dstDir = '/'
			elif (name == 'CLIENT_DATA'):
				dstDir = self.clientDataDir
			
			for archive in archives:
				try:
					if (name != 'OPSI'):
						for filename in Tools.getArchiveContent(archive):
							fn = os.path.join(dstDir, filename).strip()
							if not fn:
								continue
							self.installedFiles.append(fn)
					Tools.extractArchive(archive, chdir=dstDir)
				except Exception, e:
					self.cleanup()
					raise Exception("Failed to extract '%s': %s" % (self.packageFile, e))
					
				#os.unlink(archive)
			
			if (name == 'OPSI'):
				self.controlFile = os.path.join(self.tmpUnpackDir, 'control')
				self.readControlFile()
				
				if self.clientDataDir:
					# Copy control file into client data dir
					cfName = '%s_%s-%s' % (self.product.productId, self.product.productVersion, self.product.packageVersion)
					if self.customName:
						cfName = '%s_%s' % (cfName, self.customName)
					cfName = '%s.control' % cfName
					
					ci = open(self.controlFile, 'r')
					co = open(os.path.join(self.clientDataDir, cfName), 'w')
					co.write(ci.read())
					co.close()
					ci.close()
					self.installedFiles.append( os.path.join(self.clientDataDir, cfName) )
					
		if self.installedFiles:
			self.installedFiles.sort()
			for filename in self.installedFiles:
				logger.debug("Installed file: %s" % filename)






