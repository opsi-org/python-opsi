import os, pwd, grp

from tests.helper.backend import FileBackendFixture, BackendContentFixture
from tests.helper.testcase import TestCase
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
		fb = self.useFixture(FileBackendFixture())
		self.useFixture(BackendContentFixture(fb.backend, False))
		