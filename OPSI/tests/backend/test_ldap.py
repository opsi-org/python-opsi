import os, pwd, grp

from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import LDAPBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin

class LdapTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    #MultithreadingMixin
		):
	
	def setUp(self):
		super(LdapTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		self.backendFixture = self.useFixture(LDAPBackendFixture())
		self.backend = self.backendFixture.backend
	
		self.expected = self.useFixture(BackendContentFixture(self.backend, self.backendFixture.licenseManagement))
		

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)