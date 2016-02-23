#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import, print_function

from .helpers import unittest

from OPSI.Object import LocalbootProduct, ProductDependency, ProductOnClient
from OPSI import SharedAlgorithm
from OPSI.Types import OpsiProductOrderingError
from OPSI.Types import forceUnicode


class TestFrame(unittest.TestCase):
	opsiAgent = LocalbootProduct(
		id='opsi-agent',
		name=u'opsi client agent',
		productVersion='4.0',
		packageVersion='1',
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=95,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	ultravnc = LocalbootProduct(
		id='ultravnc',
		name=u'Ult@VNC',
		productVersion='1.0.8.2',
		packageVersion='1',
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=0,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	firefox = LocalbootProduct(
		id='firefox',
		name=u'Mozilla Firefox',
		productVersion='3.6',
		packageVersion='1',
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript="update.ins",
		alwaysScript=None,
		onceScript=None,
		priority=0,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	flashplayer = LocalbootProduct(
		id='flashplayer',
		name=u'Adobe Flashplayer',
		productVersion='10.0.45.2',
		packageVersion='2',
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=0,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	sysessential = LocalbootProduct(
		id='sysessential',
		name=u'Sys Essential',
		productVersion='1.10.0',
		packageVersion=2,
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=55,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	javavm = LocalbootProduct(
		id='javavm',
		name=u'Sun Java',
		productVersion='1.6.20',
		packageVersion=2,
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=0,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)

	jedit = LocalbootProduct(
		id='jedit',
		name=u'jEdit',
		productVersion='5.1.0',
		packageVersion=2,
		licenseRequired=False,
		setupScript="setup.ins",
		uninstallScript=u"uninstall.ins",
		updateScript=None,
		alwaysScript=None,
		onceScript=None,
		priority=0,
		description=None,
		advice="",
		windowsSoftwareIds=[]
	)


	flashplayerDependency1 = ProductDependency(
		productId=flashplayer.id,
		productVersion=flashplayer.productVersion,
		packageVersion=flashplayer.packageVersion,
		productAction='setup',
		requiredProductId=firefox.id,
		requiredProductVersion=firefox.productVersion,
		requiredPackageVersion=firefox.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)

	javavmDependency1 = ProductDependency(
		productId=javavm.id,
		productVersion=javavm.productVersion,
		packageVersion=javavm.packageVersion,
		productAction='setup',
		requiredProductId=firefox.id,
		requiredProductVersion=firefox.productVersion,
		requiredPackageVersion=firefox.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)

	jeditDependency1 = ProductDependency(
		productId=jedit.id,
		productVersion=jedit.productVersion,
		packageVersion=jedit.packageVersion,
		productAction='setup',
		requiredProductId=javavm.id,
		requiredProductVersion=javavm.productVersion,
		requiredPackageVersion=javavm.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)


	ultravncDependency1 = ProductDependency(
		productId=ultravnc.id,
		productVersion=ultravnc.productVersion,
		packageVersion=ultravnc.packageVersion,
		productAction='setup',
		requiredProductId=javavm.id,
		requiredProductVersion=javavm.productVersion,
		requiredPackageVersion=javavm.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)

	sysessentialDependency1 = ProductDependency(
		productId=sysessential.id,
		productVersion=sysessential.productVersion,
		packageVersion=sysessential.packageVersion,
		productAction='setup',
		requiredProductId=ultravnc.id,
		requiredProductVersion=ultravnc.productVersion,
		requiredPackageVersion=ultravnc.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)
	firefoxDependency1 = ProductDependency(
		productId=firefox.id,
		productVersion=firefox.productVersion,
		packageVersion=firefox.packageVersion,
		productAction='setup',
		requiredProductId=ultravnc.id,
		requiredProductVersion=ultravnc.productVersion,
		requiredPackageVersion=ultravnc.packageVersion,
		requiredAction=None,
		requiredInstallationStatus='installed',
		requirementType='before'
	)


	productOnClient1 = ProductOnClient(
		productId=flashplayer.getId(),
		productType=flashplayer.getType(),
		clientId='client1.test.invalid',
		installationStatus='installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=flashplayer.getProductVersion(),
		packageVersion=flashplayer.getPackageVersion(),
		modificationTime='2009-07-01 12:00:00'
	)
	productOnClient2 = ProductOnClient(
		productId=opsiAgent.getId(),
		productType=opsiAgent.getType(),
		clientId='client1.test.invalid',
		installationStatus='not_installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=None,
		packageVersion=None,
		modificationTime='2009-07-01 12:00:00'
	)
	productOnClient3 = ProductOnClient(
		productId=jedit.getId(),
		productType=jedit.getType(),
		clientId='client1.test.invalid',
		installationStatus='not_installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=None,
		packageVersion=None,
		modificationTime='2009-07-01 12:00:00'
	)
	productOnClient4 = ProductOnClient(
		productId=ultravnc.getId(),
		productType=ultravnc.getType(),
		clientId='client1.test.invalid',
		installationStatus='not_installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=None,
		packageVersion=None,
		modificationTime='2009-07-01 12:00:00'
	)

	productOnClient5 = ProductOnClient(
		productId=sysessential.getId(),
		productType=sysessential .getType(),
		clientId='client1.test.invalid',
		installationStatus='not_installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=None,
		packageVersion=None,
		modificationTime='2009-07-01 12:00:00'
	)

	productOnClient6 = ProductOnClient(
		productId=jedit.getId(),
		productType=javavm .getType(),
		clientId='client2.test.invalid',
		installationStatus='not_installed',
		actionRequest='setup',
		actionProgress='',
		productVersion=None,
		packageVersion=None,
		modificationTime='2009-07-01 12:00:00'
	)

	availProducts = [
		opsiAgent, ultravnc, flashplayer, javavm, jedit, firefox, sysessential
	]
	deps = [
		flashplayerDependency1, javavmDependency1, jeditDependency1,
		ultravncDependency1
	]

	productOnClients = [
		productOnClient1, productOnClient2, productOnClient3,
		productOnClient4, productOnClient5,productOnClient6
	]


class DependenciesOnlyInsideAPriorityclassTestCase(TestFrame):
	"""
	CASE: priority levels and dependency do not interfer
	"""

	def setUp(self):
		self.sortedProductList = [
			u'opsi-agent', u'sysessential', u'firefox', u'javavm',
			u'ultravnc', u'flashplayer', u'jedit'
		]
		self.sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		self.sortedProductList2 = SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)

	def tearDown(self):
		del self.sortedProductList
		del self.sortedProductList1
		del self.sortedProductList2

	def testAlgo1(self):
		print("availProducts %s " % self.availProducts)
		print("dependencies %s " % self.deps)
		print(u"compare to sortedProductList %s " % self.sortedProductList)
		print(u"produced sorted list  with 1: %s " % self.sortedProductList1)
		self.assertEqual(self.sortedProductList1, self.sortedProductList)

	def testAlgo2(self):
		print(u"compare to sortedProductList %s " % self.sortedProductList)
		print(u"produced sorted list : %s " % self.sortedProductList2)
		self.assertEqual(self.sortedProductList2, self.sortedProductList)


class DependenciesCrossingPriorityclassesTestCase(TestFrame):
	"""
	CASE: the sysessential dependency tries to move the product ultravnc to front in contradiction to priority
	"""

	def setUp(self):
		self.deps = TestFrame.deps[:]
		self.deps.append(TestFrame.sysessentialDependency1)

		self.sortedProductList1 = SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		self.sortedProductList2 = SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)

	def tearDown(self):
		del self.sortedProductList1
		del self.sortedProductList2

	def testAlgo1(self):
		sortedProductListTarget = [
			'opsi-agent', u'firefox', u'javavm', u'ultravnc', u'flashplayer',
			u'jedit', u'sysessential'
		]
		print(u"produced sorted list : %s " % self.sortedProductList1)
		self.assertEqual(self.sortedProductList1, sortedProductListTarget)

	def testAlgo2(self):
		sortedProductListTarget = [
			u'opsi-agent', u'sysessential', u'firefox', u'javavm',
			u'ultravnc', u'flashplayer', u'jedit'
		]
		print(u"produced sorted list : %s " % self.sortedProductList2)
		self.assertEqual(self.sortedProductList2, sortedProductListTarget)


class CircularDependenciesTestCase(TestFrame):
	"""
	This testcase shows how Circular Dependencies raise an exception.

	The testcase is that ultravnc depends on javavm, javavm on firefox
	and, now added, firefox on ultravnc.
	"""

	def setUp(self):
		self.deps = TestFrame.deps[:]
		self.deps.append(TestFrame.firefoxDependency1)

	def testAlgo1RaisesAnException(self):
		self.assertRaises(OpsiProductOrderingError, SharedAlgorithm.generateProductSequence_algorithm1, self.availProducts, self.deps)

	def testExceptionIsHelpfulForAlgo1(self):
		try:
			SharedAlgorithm.generateProductSequence_algorithm1(self.availProducts, self.deps)
		except OpsiProductOrderingError as error:
			self.assertIn('firefox', forceUnicode(error))
			self.assertIn('javavm', forceUnicode(error))
			self.assertIn('ultravnc', forceUnicode(error))

	def testAlgo2RaisesAnException(self):
		self.assertRaises(OpsiProductOrderingError, SharedAlgorithm.generateProductSequence_algorithm2, self.availProducts, self.deps)

	def testExceptionIsHelpfulForAlgo2(self):
		try:
			SharedAlgorithm.generateProductSequence_algorithm2(self.availProducts, self.deps)
		except OpsiProductOrderingError as error:
			self.assertIn('firefox', forceUnicode(error))
			self.assertIn('javavm', forceUnicode(error))
			self.assertIn('ultravnc', forceUnicode(error))


if __name__ == '__main__':
	unittest.main()
