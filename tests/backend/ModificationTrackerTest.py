import time

from OPSI.Backend.SQLite import SQLiteBackend, SQLiteObjectBackendModificationTracker
from OPSI.Backend.Backend import ExtendedConfigDataBackend, ModificationTrackingBackend
from OPSI.Object import *
from BackendTest import *

#from OPSI.Logger import *
#logger = Logger()
#logger.setConsoleLevel(6)
#logger.setConsoleColor(True)


	
class ModificationTrackerTestCase(ExtendedBackendTestCase):
	
	@classmethod
	def setUpClass(cls):
		cls.sqliteBackend  = SQLiteBackend(database = ":memory:")
		cls.backendTracker = SQLiteObjectBackendModificationTracker(database = ":memory:")
		
	def createBackend(self):
		self.backend = ExtendedConfigDataBackend(ModificationTrackingBackend(self.sqliteBackend))
		self.backend.addBackendChangeListener(self.backendTracker)
		self.backend.backend_createBase()
		
	def test_insert(self):
		self.backendTracker.clearModifications()
		host = self.clients[0]
		self.backend.host_insertObject(host)
		time.sleep(0.1)
		modifications = self.backendTracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'insert', u"Expected command %s, but got '%s'" % ('insert', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
		
	def test_update(self):
		host = self.clients[0]
		self.backend.host_insertObject(host)
		self.backendTracker.clearModifications()
		self.backend.host_updateObject(host)
		time.sleep(0.1)
		modifications = self.backendTracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'update', u"Expected command %s, but got '%s'" % ('update', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
		
	def test_delete(self):
		host = self.clients[0]
		self.backend.host_insertObject(host)
		self.backendTracker.clearModifications()
		self.backend.host_deleteObjects(host)
		time.sleep(0.1)
		modifications = self.backendTracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'delete', u"Expected command %s, but got '%s'" % ('delete', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
	
























