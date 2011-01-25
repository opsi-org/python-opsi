import os, pwd, grp

from OPSI.Backend.SQLite import SQLiteBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Object import *

from BackendTest import *
from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin
from BackendMixins.ExtendedBackendMixin import ExtendedBackendMixin

class SQLiteTestCase(ExtendedBackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    InventoryObjectMethodMixin,
		    LicenseManagementObjectsMixin,
		    ExtendedBackendMixin,
		    #MultithreadingMixin
		):
	
	@classmethod
	def setUpClass(cls):
		cls.sqliteBackend = SQLiteBackend(database = ":memory:")
	
	def createBackend(self):
		env = os.environ.copy()
		uid = gid = env["USER"]
		
		self.licenseManagement = True
		self.inventoryHistory = True

		self.backend = ExtendedConfigDataBackend(self.sqliteBackend)
		self.backend.backend_createBase()