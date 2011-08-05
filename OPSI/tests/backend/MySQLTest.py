from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import MySQLBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
#from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin
from BackendMixins.ExtendedBackendMixin import ExtendedBackendMixin

class MySQLTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    InventoryObjectMethodMixin,
		    LicenseManagementObjectsMixin,
		    ExtendedBackendMixin,
#		    MultithreadingMixin
		):
	
	def setUp(self):
		super(MySQLTestCase, self).setUp()
		
		self.licenseManagement = True
		self.inventoryHistory = True
		
		self.useFixture(FQDNFixture())
		self.backendFixture = self.useFixture(MySQLBackendFixture(username="root", password="linux123", database="test"))
		self.backend = self.backendFixture.backend
		
		self.expected = self.useFixture(BackendContentFixture(self.backendFixture.backend, self.backendFixture.licenseManagement))
