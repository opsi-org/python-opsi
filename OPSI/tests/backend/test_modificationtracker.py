import time

from OPSI.Backend.SQLite import SQLiteBackend, SQLiteObjectBackendModificationTracker
from OPSI.Backend.Backend import ExtendedConfigDataBackend, ModificationTrackingBackend

from OPSI.tests.helper.fixture import FQDNFixture
from OPSI.tests.helper.backend import SQLiteBackendFixture, SQLiteModificationTrackerFixture, BackendContentFixture, BackendTestCase
from OPSI.tests.helper.testcase import TestCase
from OPSI.Object import *


	
class ModificationTrackerTestCase(BackendTestCase):
	
	def setUp(self):
		super(ModificationTrackerTestCase, self).setUp()
		
		self.useFixture(FQDNFixture())
		
		self.fb = self.useFixture(SQLiteBackendFixture())
		self.backend = ModificationTrackingBackend(self.fb.backend)
		
		self.tb = self.useFixture(SQLiteModificationTrackerFixture())
		self.tracker = self.tb.tracker
		self.backend.addBackendChangeListener(self.tracker)
		
		self.expected = self.useFixture(BackendContentFixture(self.fb.backend, True))
		self.inventoryHistory = True

	def test_insert(self):
		self.tracker.clearModifications()
		host = self.expected.clients[0]
		self.backend.host_insertObject(host)
		time.sleep(0.1)
		modifications = self.tracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'insert', u"Expected command %s, but got '%s'" % ('insert', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
		
	def test_update(self):
		host = self.expected.clients[0]
		self.backend.host_insertObject(host)
		self.tracker.clearModifications()
		self.backend.host_updateObject(host)
		time.sleep(0.1)
		modifications = self.tracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'update', u"Expected command %s, but got '%s'" % ('update', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
		
	def test_delete(self):
		host = self.expected.clients[0]
		self.backend.host_insertObject(host)
		self.tracker.clearModifications()
		self.backend.host_deleteObjects(host)
		time.sleep(0.1)
		modifications = self.tracker.getModifications()
		self.assertEqual(len(modifications), 1, u"Expected %s modifications, but got '%s'" % (1, len(modifications)))
		self.assertEqual(modifications[0]['objectClass'], host.__class__.__name__, u"Expected objectClass %s, but got '%s'" % (host.__class__.__name__, modifications[0]['objectClass']))
		self.assertEqual(modifications[0]['command'], 'delete', u"Expected command %s, but got '%s'" % ('delete', modifications[0]['command']))
		self.assertEqual(modifications[0]['ident'], host.getIdent(), u"Expected ident %s, but got '%s'" % (host.getIdent(), modifications[0]['ident']))
	
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)























