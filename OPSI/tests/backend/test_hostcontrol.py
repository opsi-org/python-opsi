
import os, pwd, grp

from ConnectionHelper import *

from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import FileBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from OPSI.Backend import HostControl
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.File import FileBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend



	
class HostControlTestCase(BackendTestCase):
	
	def setUp(self):
		super(HostControlTestCase, self).setUp()
		
		self.inventoryHistory = False
		
		self.useFixture(FQDNFixture())
		self.fb = self.useFixture(FileBackendFixture())
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, False))
		
		self.patch(HostControl.socket, "socket", DummySocket)
		self.patch(HostControl, "non_blocking_connect_https", dummy_connect_http)
		self.patch(HostControl, "HTTPSConnection", DummyHttpConnection)
		
		self.backend = HostControlBackend(ExtendedConfigDataBackend(self.fb.backend))
		self.backend.backend_createBase()
		
	def test_HostControlBackend(self):
		#try:
			self.backend.hostControl_start([u'client1.uib.local'])
			self.backend.hostControl_shutdown([u'client1.uib.local'])
		#except Exception, e:
		#	self.fail("HostControlBackend test failed with: %s;"% (e))

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)