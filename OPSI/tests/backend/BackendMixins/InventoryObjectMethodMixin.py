from OPSI.Object import *

class InventoryObjectMethodMixin(object):
	
	def test_getAuditSoftwareFromBackend(self):
		
		auditSoftwares = self.backend.auditSoftware_getObjects()
		self.assertEqual(len(auditSoftwares), len(self.expected.auditSoftwares), u"Expected %s audit software objects, but found %s on backend." % (len(self.expected.auditSoftwares), len(auditSoftwares)))
	
	def test_updateAuditSoftware(self):
		auditSoftware3update = AuditSoftware(
			name=self.expected.auditSoftware3.name,
			version=self.expected.auditSoftware3.version,
			subVersion=self.expected.auditSoftware3.subVersion,
			language=self.expected.auditSoftware3.language,
			architecture=self.expected.auditSoftware3.architecture,
			windowsSoftwareId=self.expected.auditSoftware3.windowsSoftwareId,
			windowsDisplayName='updatedDN',
			windowsDisplayVersion=self.expected.auditSoftware3.windowsDisplayVersion,
			installSize=self.expected.auditSoftware3.installSize
		)
		
		self.backend.auditSoftware_updateObject(auditSoftware3update)
		auditSoftwares = self.backend.auditSoftware_getObjects(windowsDisplayName='updatedDN')
		self.assertEqual(len(auditSoftwares), 1, u"Expected one audit software object, but found %s on backend." % (len(auditSoftwares)))
	
	def test_deleteAuditSoftware(self):
		self.backend.auditSoftware_deleteObjects(self.expected.auditSoftware3)
		auditSoftwares = self.backend.auditSoftware_getObjects()
		self.assertEqual(len(auditSoftwares), len(self.expected.auditSoftwares) - 1, u"Expected %s audit software objects, but found %s on backend." % (len(self.expected.auditSoftwares) - 1, len(auditSoftwares)))
			
	def test_insertAuditSoftware(self):
		self.backend.auditSoftware_deleteObjects(self.expected.auditSoftware3)
		self.backend.auditSoftware_insertObject(self.expected.auditSoftware3)
		auditSoftwares = self.backend.auditSoftware_getObjects()
		self.assertEqual(len(auditSoftwares), len(self.expected.auditSoftwares), u"Expected %s audit software objects, but found %s on backend." % (len(self.expected.auditSoftwares), len(auditSoftwares)))
		
		
	def test_getAuditSoftewareLicensePoolFromBackend(self):
		if not self.expected.licenseManagement:
			self.skipTest("LicenseManagement is not enabled on %s." % self.__class__.__name__)
			# AuditSoftwareToLicensePools
			
		self.backend.auditSoftwareToLicensePool_createObjects(self.expected.auditSoftwareToLicensePools)
		
		auditSoftwareToLicensePools = self.backend.auditSoftwareToLicensePool_getObjects()
		self.assertEqual(len(auditSoftwareToLicensePools), len(self.expected.auditSoftwareToLicensePools), u"Expected %s audit license objects in pool, but found %s on backend." % (len(self.expected.auditSoftwareToLicensePools), len(auditSoftwareToLicensePools)))
			
			
	def test_getAuditSoftwareOnClients(self):
		auditSoftwareOnClients = self.backend.auditSoftwareOnClient_getObjects()
		self.assertEqual(len(auditSoftwareOnClients), len(self.expected.auditSoftwareOnClients), "Expected %s software objects in pool, but found %s on backend." % (len(self.expected.auditSoftwareOnClients), len(auditSoftwareOnClients)))
		

	def test_updateAuditSoftwareOnClient(self):
		auditSoftwareOnClient1update = AuditSoftwareOnClient(
			name=self.expected.auditSoftware1.getName(),
			version=self.expected.auditSoftware1.getVersion(),
			subVersion=self.expected.auditSoftware1.getSubVersion(),
			language=self.expected.auditSoftware1.getLanguage(),
			architecture=self.expected.auditSoftware1.getArchitecture(),
			clientId=self.expected.client1.getId(),
			uninstallString=None,
			binaryName='updatedBN',
			firstseen=None,
			lastseen=None,
			state=None,
			usageFrequency=2,
			lastUsed='2009-02-12 09:48:22'
		)
		
		self.backend.auditSoftwareOnClient_updateObject(auditSoftwareOnClient1update)
		auditSoftwareOnClients = self.backend.auditSoftwareOnClient_getObjects(binaryName='updatedBN')
		self.assertEqual(len(auditSoftwareOnClients), 1, "Expected one software object in pool, but found %s on backend." % (len(auditSoftwareOnClients)))
			
	def test_deleteAuditSoftwareOnClient(self):
		self.backend.auditSoftwareOnClient_deleteObjects(self.expected.auditSoftwareOnClient1)
		auditSoftwareOnClients = self.backend.auditSoftwareOnClient_getObjects()
		self.assertEqual(len(auditSoftwareOnClients), len(self.expected.auditSoftwareOnClients) - 1, u"Expected %s audit software objects, but found %s on backend." % (len(self.expected.auditSoftwareOnClients) - 1, len(auditSoftwareOnClients)))
		
	def test_insertAuditSoftwareOnClient(self):
		self.backend.auditSoftwareOnClient_deleteObjects(self.expected.auditSoftwareOnClient1)
		self.backend.auditSoftwareOnClient_insertObject(self.expected.auditSoftwareOnClient1)
		auditSoftwareOnClients = self.backend.auditSoftwareOnClient_getObjects()
		self.assertEqual(len(auditSoftwareOnClients), len(self.expected.auditSoftwareOnClients), u"Expected %s audit software objects, but found %s on backend." % (len(self.expected.auditSoftwareOnClients), len(auditSoftwareOnClients)))
		
		
	def test_getAuditHardwareFromBackend(self):
		auditHardwares = self.backend.auditHardware_getObjects()
		self.assertEqual(len(auditHardwares), len(self.expected.auditHardwares), u"Expected %s audit hardware objects, but found %s on backend." % (len(self.expected.auditHardwares), len(auditHardwares)))
		
	
	def test_selectAuditHardwareClasses(self):
		auditHardwareClasses = map((lambda x: x.getHardwareClass()),self.backend.auditHardware_getObjects(hardwareClass=['CHASSIS', 'COMPUTER_SYSTEM']))
		for auditHardwareClass in auditHardwareClasses:
			self.assertIn(auditHardwareClass, ['CHASSIS', 'COMPUTER_SYSTEM'], u"Hardware class '%s' not in '%s'." % (auditHardwareClass, ['CHASSIS', 'COMPUTER_SYSTEM']))
		
		auditHardwareClasses = map((lambda x: x.getHardwareClass()), self.backend.auditHardware_getObjects(hardwareClass=['CHA*IS', '*UTER_SYS*']))
		for auditHardwareClass in auditHardwareClasses:
			self.assertIn(auditHardwareClass, ['CHASSIS', 'COMPUTER_SYSTEM'], u"Hardware class '%s' not in '%s'." % (auditHardwareClass, ['CHASSIS', 'COMPUTER_SYSTEM']))
	
	def test_deleteAuditHardware(self):
		self.backend.auditHardware_deleteObjects([ self.expected.auditHardware1, self.expected.auditHardware2 ])
		auditHardwares = self.backend.auditHardware_getObjects()
		self.assertEqual(len(auditHardwares), len(self.expected.auditHardwares) - 2, u"Expected %s audit hardware objects, but found %s on backend." % (len(self.expected.auditHardwares)-2, len(auditHardwares)))
	
	def test_deleteAllAuditHardware(self):
		self.backend.auditHardware_deleteObjects(self.backend.auditHardware_getObjects())
		auditHardwares = self.backend.auditHardware_getObjects()
		self.assertEqual(len(auditHardwares), 0, u"Expected 0 audit hardware objects, but found %s on backend." % (len(auditHardwares)))
		
	def test_createAuditHardware(self):
		self.backend.auditHardware_deleteObjects([ self.expected.auditHardware1, self.expected.auditHardware2 ])
		self.backend.auditHardware_createObjects([ self.expected.auditHardware1, self.expected.auditHardware2 ])
		auditHardwares = self.backend.auditHardware_getObjects()
		self.assertEqual(len(auditHardwares), len(self.expected.auditHardwares), u"Expected %s audit hardware objects, but found %s on backend." % (len(self.expected.auditHardwares), len(auditHardwares)))
		
		self.backend.auditHardware_deleteObjects(self.backend.auditHardware_getObjects())
		self.backend.auditHardware_createObjects(self.expected.auditHardwares)
		auditHardwares = self.backend.auditHardware_getObjects()
		self.assertEqual(len(auditHardwares), len(self.expected.auditHardwares), u"Expected %s audit hardware objects, but found %s on backend." % (len(self.expected.auditHardwares), len(auditHardwares)))
		
	def test_getAuditHardwareOnHost(self):
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts), u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts), auditHardwareOnHosts))
		
	
	def test_insertAuditHardwareOnHost(self):
		auditHardwareOnHost4update = self.expected.auditHardwareOnHost4.clone()
		auditHardwareOnHost4update.setLastseen('2000-01-01 01:01:01')
		self.backend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		if self.inventoryHistory:
			self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts) + 1, u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts)+1, len(auditHardwareOnHosts)))
		else:
			self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts), u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts), len(auditHardwareOnHosts)))
				
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects(lastseen='2000-01-01 01:01:01')
		self.assertEqual(len(auditHardwareOnHosts), 1, u"Expected one audit hardware object on host, but found %s on backend." % (len(auditHardwareOnHosts)))
		
		auditHardwareOnHost4update.setState(0)
		self.backend.auditHardwareOnHost_insertObject(auditHardwareOnHost4update)
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		if self.inventoryHistory:
			self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts) + 2, u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts)+2, len(auditHardwareOnHosts)))
		else:
			self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts), u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts), len(auditHardwareOnHosts)))
			
	
	def test_deleteAllAuditHardwareOnHost(self):
		self.backend.auditHardwareOnHost_delete(hostId=[], hardwareClass=[], firstseen=[], lastseen=[], state=[])
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		self.assertEqual(len(auditHardwareOnHosts), 0, u"Expected no audit hardware objects on host, but found %s on backend." % (len(auditHardwareOnHosts)))
		
	def test_createAuditHardwareOnHost(self):
		self.backend.auditHardwareOnHost_delete(hostId=[], hardwareClass=[], firstseen=[], lastseen=[], state=[])
		self.backend.auditHardwareOnHost_createObjects(self.expected.auditHardwareOnHosts)
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts), u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts), len(auditHardwareOnHosts)))
		
	def test_createDuplicateAuditHardwareOnHost(self):
		numBefore = len(self.backend.auditHardwareOnHost_getObjects())
		auditHardwareOnHost4update = self.expected.auditHardwareOnHost4.clone()
		self.backend.auditHardwareOnHost_updateObject(auditHardwareOnHost4update)
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		numAfter = len(self.backend.auditHardwareOnHost_getObjects())
		self.assertEqual(numBefore, numAfter, u"Expected %s audit hardware objects on host, but found %s on backend." % (numBefore, numAfter))

	def test_deleteAuditHardwareOnHost(self):
		self.backend.auditHardwareOnHost_deleteObjects([self.expected.auditHardwareOnHost4, self.expected.auditHardwareOnHost3])
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects()
		self.assertEqual(len(auditHardwareOnHosts), len(self.expected.auditHardwareOnHosts) - 2, u"Expected %s audit hardware objects on host, but found %s on backend." % (len(self.expected.auditHardwareOnHosts)-2, len(auditHardwareOnHosts)))
	
	def test_setObsoleteAuditHardwareOnHost(self):
		self.backend.auditHardwareOnHost_setObsolete(self.expected.client3.id)
		auditHardwareOnHosts = self.backend.auditHardwareOnHost_getObjects(hostId = self.expected.client3.id)
		for auditHardwareOnHost in auditHardwareOnHosts:
			self.assertEqual(auditHardwareOnHost.getState(), 0, u"Expected state 0 in audit hardware on host %s, but found state %s on backend." % (auditHardwareOnHost, auditHardwareOnHost.getState()))
	







