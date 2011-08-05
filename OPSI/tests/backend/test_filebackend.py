
from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import FileBackendFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin

class FileBackendTestCase(BackendTestCase,
		   ObjectMethodsMixin,
		   NonObjectMethodsMixin,
		   InventoryObjectMethodMixin
		   ):
	
	def setUp(self):
		super(FileBackendTestCase, self).setUp()
		self.inventoryHistory = False
		
		self.useFixture(FQDNFixture())
		self.fb = self.useFixture(FileBackendFixture())
		self.backend = self.fb.backend
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, False))

def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)