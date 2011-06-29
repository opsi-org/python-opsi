import os, pwd, grp, time


from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import FileBackendFixture, BackendContentFixture
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *

from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin

class FileBackendTestCase(TestCase,
		   ObjectMethodsMixin,
		   NonObjectMethodsMixin,
		   InventoryObjectMethodMixin
		   ):
	
	def setUp(self):
		super(FileBackendTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		self.fb = self.useFixture(FileBackendFixture())
		self.useFixture(BackendContentFixture(self.fb.backend, False))
		
		self.backend = self.fb.backend