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
import os

# OPSI imports
from OPSI.Logger import *
from OPSI.Util.File.Opsi import PackageControlFile

logger = Logger()



class ProductPackageFile(ProductPackage):
	
	def __init__(self, packageFile, tempDir = None):
		self.packageFile = forceFilename(packageFile)
		if not tempDir:
			tempDir = DEFAULT_TMP_DIR
		tempDir = forceFilename(tempDir)
		self.tempDir = os.path.abspath(tempDir)
		if not os.path.isdir(self.tempDir):
			raise Exception(u"Temporary directory '%s' not found" % self.tempDir)
		
		self.productId      = 'unknown'
		self.productVersion = 'unknown'
		self.packageVersion = 'unknown'
		self.customName     = None
		
		if self.packageFile.endswith('.opsi'):
			infoFromFileName = os.path.basename(self.packageFile)[:-1*len('.opsi')].split('_')
			self.productId = infoFromFileName[0]
			if (len(infoFromFileName) > 1):
				i = infoFromFileName[1].find('-')
				if (i != -1):
					self.productVersion = infoFromFileName[1][:i]
					self.packageVersion = infoFromFileName[1][i+1:]
			if (len(infoFromFileName) > 2):
				self.customName = infoFromFileName[2]
		
		self.tmpUnpackDir = os.path.join( self.tempDir, 'unpack.%s.%s' % (self.productId, Tools.randomString(5)) )
	
		return
		##################################
		self.product = Product()
		self.packageFile = os.path.abspath(packageFile)
		self.tempDir = os.path.abspath(tempDir)
		self.installedFiles = []
		
		ProductPackage.__init__(self, self.product)
		self.clientDataDir = None
		
		
		
		# Unpack and read control file
		#self.lock()
		self.unpack(dataArchives = False)
		#self.unlock()
				
		self.clientDataDir = os.path.join('/tmp', self.product.productId)







