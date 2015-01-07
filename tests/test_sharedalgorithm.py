#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing OPSI.SharedAlgorithm

:author: Rupert Röder <r.roeder@uib.de>
:license: GNU Affero General Public License version 3
"""
# for testing install python-pip, and then pip install nose
#nosetests -s tests/test_sharedalgorithm.py 


from __future__ import absolute_import

import unittest


from OPSI.Logger import *
from OPSI.Object import *
from OPSI.Types import OpsiProductOrderingError, BackendUnaccomplishableError
from OPSI.Types import forceInt, forceBool
from OPSI import SharedAlgorithm


class TestFrame(unittest.TestCase):
	opsiAgent = LocalbootProduct(
		id                 = 'opsi-agent',
		name               = u'opsi client agent',
		productVersion     = '4.0',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 95,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)

	ultravnc = LocalbootProduct(
		id                 = 'ultravnc',
		name               = u'Ult@VNC',
		productVersion     = '1.0.8.2',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)

	firefox = LocalbootProduct(
		id                 = 'firefox',
		name               = u'Mozilla Firefox',
		productVersion     = '3.6',
		packageVersion     = '1',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = "update.ins",
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)

	flashplayer = LocalbootProduct(
		id                 = 'flashplayer',
		name               = u'Adobe Flashplayer',
		productVersion     = '10.0.45.2',
		packageVersion     = '2',
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	
	sysessential = LocalbootProduct(
		id                 = 'sysessential',
		name               = u'Sys Essential',
		productVersion     = '1.10.0',
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 55,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)

	javavm = LocalbootProduct(
		id                 = 'javavm',
		name               = u'Sun Java',
		productVersion     = '1.6.20',
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)
	
	jedit = LocalbootProduct(
		id                 = 'jedit',
		name               = u'jEdit',
		productVersion     = '5.1.0',
		packageVersion     = 2,
		licenseRequired    = False,
		setupScript        = "setup.ins",
		uninstallScript    = u"uninstall.ins",
		updateScript       = None,
		alwaysScript       = None,
		onceScript         = None,
		priority           = 0,
		description        = None,
		advice             = "",
		windowsSoftwareIds = []
	)




	flashplayerDependency1 = ProductDependency(
		productId                  = flashplayer.id,
		productVersion             = flashplayer.productVersion,
		packageVersion             = flashplayer.packageVersion,
		productAction              = 'setup',
		requiredProductId          = firefox.id,
		requiredProductVersion     = firefox.productVersion,
		requiredPackageVersion     = firefox.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)

	javavmDependency1 = ProductDependency(
		productId                  = javavm.id,
		productVersion             = javavm.productVersion,
		packageVersion             = javavm.packageVersion,
		productAction              = 'setup',
		requiredProductId          = firefox.id,
		requiredProductVersion     = firefox.productVersion,
		requiredPackageVersion     = firefox.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	jeditDependency1 = ProductDependency(
		productId                  = jedit.id,
		productVersion             = jedit.productVersion,
		packageVersion             = jedit.packageVersion,
		productAction              = 'setup',
		requiredProductId          = javavm.id,
		requiredProductVersion     = javavm.productVersion,
		requiredPackageVersion     = javavm.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	
	ultravncDependency1 = ProductDependency(
		productId                  = ultravnc.id,
		productVersion             = ultravnc.productVersion,
		packageVersion             = ultravnc.packageVersion,
		productAction              = 'setup',
		requiredProductId          = javavm.id,
		requiredProductVersion     = javavm.productVersion,
		requiredPackageVersion     = javavm.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	sysessentialDependency1 = ProductDependency(
		productId                  = sysessential.id,
		productVersion             =sysessential.productVersion,
		packageVersion             = sysessential.packageVersion,
		productAction              = 'setup',
		requiredProductId          = ultravnc.id,
		requiredProductVersion     = ultravnc.productVersion,
		requiredPackageVersion     = ultravnc.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	firefoxDependency1 = ProductDependency(
		productId                  = firefox.id,
		productVersion             =firefox.productVersion,
		packageVersion             = firefox.packageVersion,
		productAction              = 'setup',
		requiredProductId          = ultravnc.id,
		requiredProductVersion     = ultravnc.productVersion,
		requiredPackageVersion     = ultravnc.packageVersion,
		requiredAction             = None,
		requiredInstallationStatus = 'installed',
		requirementType            = 'before'
	)
	
	


	productOnClient1 = ProductOnClient(
		productId          = flashplayer.getId(),
		productType        = flashplayer.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = flashplayer.getProductVersion(),
		packageVersion     = flashplayer.getPackageVersion(),
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient2 = ProductOnClient(
		productId          = opsiAgent.getId(),
		productType        = opsiAgent.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient3 = ProductOnClient(
		productId          = jedit.getId(),
		productType        = jedit.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	productOnClient4 = ProductOnClient(
		productId          = ultravnc.getId(),
		productType        = ultravnc.getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	
	productOnClient5 = ProductOnClient(
		productId          = sysessential.getId(),
		productType        =sysessential .getType(),
		clientId           = 'client1.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	
	productOnClient6 = ProductOnClient(
		productId          = jedit.getId(),
		productType        = javavm .getType(),
		clientId           = 'client2.uib.local',
		installationStatus = 'not_installed',
		actionRequest      = 'setup',
		actionProgress     = '',
		productVersion     = None,
		packageVersion     = None,
		modificationTime   = '2009-07-01 12:00:00'
	)
	
	
	availProducts = [ opsiAgent, ultravnc, flashplayer, javavm, jedit, firefox,sysessential ]
	deps = [ flashplayerDependency1, javavmDependency1, jeditDependency1, ultravncDependency1 ]
	
	productOnClients = [ productOnClient1, productOnClient2, productOnClient3, productOnClient4,productOnClient5,productOnClient6 ]
	
	def show(self):
		print 
		print ("testing %s " % self)
	
	def weHave(self):	
		print
		
	def weHaveWithMoreContent(self):
		print( u"data is ")
		print ( u"availProducts")
		for prod in self.availProducts :
			print prod
		print
		print ( u"dependencies :")
		for dep in self.deps:
			print dep
		print
		print ( u"productOnClients")
		for prod in self.productOnClients:
			print prod
		print	
		print ( u"productOnClients with dependent products")
		self.productOnClients = SharedAlgorithm.addDependentProductOnClients(
			self.productOnClients,
			self.availProducts,
			self.deps)
		print ( u"productOnClients")
		for prod in self.productOnClients:
			print prod
		print "**********************************************************"
		print "**********************************************************"
	
	
		

class DependenciesOnlyInsideAPriorityclassTestCase(TestFrame):
	"""
	CASE: priority levels and dependency do not interfer
	"""
	availProducts =  TestFrame.availProducts
	productOnClients = TestFrame.productOnClients
	deps = TestFrame.deps
	sortedProductList = [u'opsi-agent', u'sysessential', u'firefox', u'javavm', u'ultravnc', u'flashplayer', u'jedit'] 
	sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(availProducts, deps)
	sortedProductList2 =SharedAlgorithm.generateProductSequence_algorithm2(availProducts, deps)
	
	def setUp(self):
		self.weHave()
		
	def tearDown(self):
		pass
	
	def testAlgo1(self):
		#print("++++++++++")
		print("availProducts %s "  % self.availProducts)
		print("dependencies %s "  % self.deps)
		print(u"compare to sortedProductList %s " % self.sortedProductList)
		#sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		print(u"produced sorted list  with 1: %s " % self.sortedProductList1)
		self.assertEqual( self.sortedProductList1, self.sortedProductList, "not the expected ordering")
		
	
	def testAlgo2(self):
		#print(u"availProducts %s " % self.availProducts)
		print(u"compare to sortedProductList %s " % self.sortedProductList)
		#sortedProductList =SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)
		print(u"produced sorted list : %s " % self.sortedProductList2)
		self.assertEqual( self.sortedProductList2, self.sortedProductList, "not the expected ordering")
		pass
	
	def testCompAlgo1_3(self):
		#self.assertTrue( False, "not the expected ordering")
		pass
	
	
class DependenciesCrossingPriorityclassesTestCase(TestFrame):
	"""
	CASE: the sysessential dependency tries to move the product ultravnc to front in contradiction to priority
	"""
	availProducts =  TestFrame.availProducts
	productOnClients = TestFrame.productOnClients
	deps = TestFrame.deps
	deps.append(TestFrame.sysessentialDependency1)
	
	sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(availProducts, deps)
	sortedProductList2 = SharedAlgorithm.generateProductSequence_algorithm2(availProducts, deps)

	
	def setUp(self):
		self.weHave()
		pass
	
	def tearDown(self):
		pass
	
	def testAlgo1(self):
		sortedProductListTarget = ['opsi-agent', u'firefox', u'javavm', u'ultravnc', u'flashplayer', u'jedit', u'sysessential']
		#sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		print(u"produced sorted list : %s " % self.sortedProductList1)
		self.assertEqual( self.sortedProductList1, sortedProductListTarget, "not the expected ordering")
	
	def testAlgo2(self):
		sortedProductListTarget=[u'opsi-agent', u'sysessential', u'firefox', u'javavm', u'ultravnc', u'flashplayer', u'jedit'] 
		#sortedProductList = SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)
		print(u"produced sorted list : %s " % self.sortedProductList2)
		self.assertEqual( self.sortedProductList2, sortedProductListTarget, "not the expected ordering")
	
	#def testCompAlgo1_3 (self):
		#sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		#productOnClients0 = self.productOnClients
		#productOnClients1 = SharedAlgorithm.generateProductOnClientSequence(productOnClients0, self.sortedProductList1)
		
		#productOnClients3=SharedAlgorithm. generateProductOnClientSequence_algorithm3(productOnClients0, self.availProducts, self.deps)
		
		#print(u'productOnClients1 %s ' % productOnClients1)
		#print
		#print(u'productOnClients3 %s ' % productOnClients3)
		#self.assertEquals(productOnClients0, productOnClients3, u'different results from 1 vs. 3')
	
	
class CircularDependenciesTestCase(TestFrame):
	"""
	CASE: ultravnc depends on javavm, javavm on firefox and, now added, firefox on ultravnc 
	"""
	
	availProducts =  TestFrame.availProducts
	productOnClients = TestFrame.productOnClients
	deps = TestFrame.deps
	deps.append(TestFrame.firefoxDependency1)
	
	
	def setUp(self):
		self.weHave()
		pass
	
	def tearDown(self):
		pass
	
	def testAlgo1(self):
		sortedProductListTarget = []
		
		print ( u"availProducts %s " %self.availProducts)
		print ( u"dependencies %s " %self.deps)
		
		sortedProductList = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		print(u"produced sorted list : %s " % sortedProductList)
		self.assertEqual( sortedProductList, sortedProductListTarget, "not the expected ordering")
	
	def testAlgo2(self):
		sortedProductListTarget = []
		sortedProductList = SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)
		print(u"produced sorted list : %s " % sortedProductList)
		self.assertEqual( sortedProductList, sortedProductListTarget, "not the expected ordering")
	
	def testCompAlgo1_3 (self):
		print ( u"availProducts ")
		for p in self.availProducts:
			print p
		print
		print ( u"dependencies ")
		for dep in self.deps:
			print dep
		print
		sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		print(u'sortedList 1 %s ' % sortedProductList1)
		print
		productOnClients0 = self.productOnClients
		print(u'productOnClients0 %s ' % productOnClients0)
		print
		productOnClients1 = SharedAlgorithm.generateProductOnClientSequence(productOnClients0, sortedProductList1)
		print(u'productOnClients1 %s ' % productOnClients1)
		print
		productOnClients3=SharedAlgorithm. generateProductOnClientSequence_algorithm3(productOnClients0, self.availProducts, self.deps)
		print(u'productOnClients3 %s ' % productOnClients3)
		self.assertNotEquals(productOnClients0, productOnClients3, u'different results from 1 vs. 3')
	
	
	
	
if __name__ == '__main__':
    unittest.main()

	
    
