import os, pwd, grp

from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import SQLiteBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from OPSI.Backend.SQLite import SQLiteBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Object import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin
from BackendMixins.ExtendedBackendMixin import ExtendedBackendMixin

class SQLiteTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    InventoryObjectMethodMixin,
		    LicenseManagementObjectsMixin,
		    ExtendedBackendMixin,
		    #MultithreadingMixin
		):
	
	def setUp(self):
		super(SQLiteTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		self.fb = self.useFixture(SQLiteBackendFixture())
		self.backend = self.fb.backend
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, True))
		self.inventoryHistory = True
		
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)