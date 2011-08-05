

class LicenseManagementObjectsMixin(object):
	
	def test_getLicenseContractsFromBackend(self):
		licenseContracts = self.backend.licenseContract_getObjects()
		self.assertEqual(len(self.expected.licenseContracts), len(licenseContracts), u"Expected %s license contracts, but found %s on backend." % (len(self.expected.licenseContracts), len(licenseContracts)))

	def test_getSoftwareLicensesFromBackend(self):
		softwareLicenses = self.backend.softwareLicense_getObjects()
		self.assertEqual(len(self.expected.softwareLicenses), len(softwareLicenses), u"Expected %s software licenses, but found %s on backend." % (len(self.expected.softwareLicenses), len(softwareLicenses)))
		
	

	def test_licensePools(self):
		licensePools = self.backend.licensePool_getObjects()
		self.assertEqual(len(self.expected.licensePools), len(licensePools), u"Expected %s license pools, but found %s on backend." % (len(self.expected.licensePools), len(licensePools)))
		for licensePool in licensePools:
			if (licensePool.getId() == self.expected.licensePool1.getId()):
				for productId in licensePool.getProductIds():
					self.assertIn(productId, self.expected.licensePool1.getProductIds(), u"Expected product %s to be in license pool %s, but could not find it." % (productId, self.expected.licensePool1.getProductIds()))
	
	def test_selectLicensePoolsByProducts(self):
		licensePools = self.backend.licensePool_getObjects(productIds = self.expected.licensePool1.productIds)
		self.assertEqual(len(licensePools), 1, u"Expected one license pool, but found %s on backend." % len(licensePools))
		self.assertEqual(licensePools[0].getId(), self.expected.licensePool1.getId(), u"Expected license pool %s but got %s." % (self.expected.licensePool1.getId(), licensePools[0].getId()))
	
	
	def test_selectInvalidLicensePoolById(self):		
		licensePools = self.backend.licensePool_getObjects(id = self.expected.licensePool2.id, productIds = self.expected.licensePool1.productIds)
		self.assertEqual(len(licensePools), 0, u"Got %s license pools from backend but did not expect any." % len(licensePools))
		

	def test_selectLicensePoolWithoutProducts(self):
		licensePools = self.backend.licensePool_getObjects(productIds = None)
		self.assertEqual(len(self.expected.licensePools), len(licensePools), u"Expected %s license pools, but found %s on backend." % (len(self.expected.licensePools), len(licensePools)))
		
	def test_selectLicensePoolByInvalidProduct(self):
		licensePools = self.backend.licensePool_getObjects(productIds = ['xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'])
		self.assertEqual(len(licensePools), 0, u"Did not expect any license pools, but found %s on backend." % len(licensePools))

	def test_softwareLicenseToLicensePool(self):
		softwareLicenseToLicensePools = self.backend.softwareLicenseToLicensePool_getObjects()
		self.assertEqual(len(self.expected.softwareLicenseToLicensePools), len(softwareLicenseToLicensePools), u"Expected %s software license to license pool objects, but got %s" % (len(self.expected.softwareLicenseToLicensePools),len(softwareLicenseToLicensePools)))

	def test_getLicenseOnClientFromBackend(self):
		licenseOnClients = self.backend.licenseOnClient_getObjects()
		self.assertEqual(len(self.expected.licenseOnClients), len(licenseOnClients), u"Expected %s licenses on clients, but found %s on backend." % (len(self.expected.licenseOnClients), len(licenseOnClients)))