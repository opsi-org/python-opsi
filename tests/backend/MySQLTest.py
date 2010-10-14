import os, pwd, grp

from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Object import *

from BackendTest import *
from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin
from BackendMixins.ExtendedBackendMixin import ExtendedBackendMixin

class MySQLTestCase(ExtendedBackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    InventoryObjectMethodMixin,
		    LicenseManagementObjectsMixin,
		    ExtendedBackendMixin,
		#    MultithreadingMixin
		):
	
	@classmethod
	def setUpClass(cls):
		cls.mysqlBackend = MySQLBackend(username = 'root', password = 'linux123', database='test')
	
	def createBackend(self):
		env = os.environ.copy()
		uid = gid = env["USER"]
		
		self.licenseManagement = True
		self.inventoryHistory = True

		self.backend = ExtendedConfigDataBackend(self.mysqlBackend)
		self.backend.backend_createBase()