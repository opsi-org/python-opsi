import os, pwd, grp



from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import SQLiteBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase

from OPSI.Backend.BackendManager import BackendAccessControl
from OPSI.Object import *



class ACLTestCase(BackendTestCase):
	
	def setUp(self):
		super(ACLTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		self.fb = self.useFixture(SQLiteBackendFixture())
		self.backend = self.fb.backend
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, True))
		self.inventoryHistory = True
	
	def test_get_access_full(self):
		backend = BackendAccessControl(
				backend  = self.backend,
				username = self.expected.configserver1.id,
				password = self.expected.configserver1.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
						]
					]
				]
		)
		hosts = backend.host_getObjects()
		self.assertEqual(len(self.expected.hosts), len(hosts), u"Expected %s hosts, but got '%s' from backend" % (len(self.expected.hosts), len(hosts)))
		for host in hosts:
			for h in self.expected.hosts:
				if (h.id != host.id):
					continue
				self.assertEqual(h.opsiHostKey, host.opsiHostKey, u"Expected opsi host key %s, but got '%s' from backend" % (h.opsiHostKey, host.opsiHostKey))
	
	def test_get_access_self(self):
		backend = BackendAccessControl(
				backend  = self.backend,
				username = self.expected.configserver1.id,
				password = self.expected.configserver1.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
						]
					]
				]
		)
		hosts = backend.host_getObjects()
		self.assertEqual(1, len(hosts), u"Expected %s hosts, but found '%s' on backend" % (1, len(hosts)))
	
	def test_get_access_deny_attributes(self):
		denyAttributes = ['opsiHostKey', 'description']
		backend = BackendAccessControl(
				backend  = self.backend,
				username = self.expected.configserver1.id,
				password = self.expected.configserver1.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': denyAttributes, 'allowAttributes': []}
						]
					]
				]
		)
		hosts = backend.host_getObjects()
		self.assertEqual(len(self.expected.hosts), len(hosts), u"Expected %s hosts, but got '%s' from backend" % (len(self.expected.hosts), len(hosts)))
		for host in hosts:
			for (attribute, value) in host.toHash().items():
				if attribute in denyAttributes:
					self.assertEqual(value, None, u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value))
		
	def test_get_access_allow_attributes(self):
		allowAttributes = ['type', 'id', 'description', 'notes']
		backend = BackendAccessControl(
				backend  = self.backend,
				username = self.expected.configserver1.id,
				password = self.expected.configserver1.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': [], 'allowAttributes': allowAttributes}
						]
					]
				]
		)
		hosts = backend.host_getObjects()
		self.assertEqual(len(self.expected.hosts), len(hosts), u"Expected %s hosts, but got '%s' from backend" % (len(self.expected.hosts), len(hosts)))
		for host in hosts:
			for (attribute, value) in host.toHash().items():
				if attribute not in allowAttributes:
					self.assertEqual(value, None, u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value))
	
	def test_get_access_deny_attributes_and_self(self):
		denyAttributes = ['opsiHostKey', 'description']
		backend = BackendAccessControl(
				backend  = self.backend,
				username = self.expected.configserver1.id,
				password = self.expected.configserver1.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'opsi_depotserver', 'ids': [], 'denyAttributes': denyAttributes, 'allowAttributes': []},
							{'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
						]
					]
				]
		)
		hosts = backend.host_getObjects()
		self.assertEqual(len(self.expected.hosts), len(hosts), u"Expected %s hosts, but got '%s' from backend" % (len(self.expected.hosts), len(hosts)))
		for host in hosts:
			if (host.id == self.expected.configserver1.id):
				self.assertEqual(self.expected.configserver1.opsiHostKey, host.opsiHostKey, u"Expected opsi host key %s, but got '%s' from backend" % (self.expected.configserver1.opsiHostKey, host.opsiHostKey))
			else:
				for (attribute, value) in host.toHash().items():
					if attribute in denyAttributes:
						self.assertEqual(value, None, u"Expected attribute '%s' to be None, but got '%s' from backend" % (attribute, value))
		
	
	def test_access_self_productOnClients(self):
		return
		for client in self.clients:
			if (client.id == self.productOnClients[0].clientId):
				break
		backend = BackendAccessControl(
				backend  = self.backend,
				username = client.id,
				password = client.opsiHostKey,
				acl      = [
					['.*', [
							{'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []}
						]
					]
				]
		)
		productOnClients = backend.productOnClient_getObjects()
		for productOnClient in productOnClients:
			self.assertEqual(client.id, productOnClient.clientId, u"Expected client id %s in productOnClient, but got client id '%s'" % (client.id, productOnClient.clientId))
		
		otherClientId = None 
		for c in self.clients:
			if (client.id != c.id):
				otherClientId = c.id
				break
		
		productOnClient = productOnClients[0].clone()
		productOnClient.clientId = otherClientId
		try:
			backend.productOnClient_updateObjects(productOnClient)
		except Exception, e:
			pass
		else:
			self.fail("Successfuly inserted productOnClient %s as user %s into backend. Access should have been denied." % (productOnClient, client.id))


def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)		
		
		
		
		
		
		
		