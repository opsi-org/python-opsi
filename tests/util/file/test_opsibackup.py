
import os, shutil, tempfile, tarfile, hashlib, time

import MySQLdb

from testtools import TestCase
from fixtures import Fixture
from OPSI.Util.File.Opsi import OpsiBackupArchive
from OPSI.Util import randomString, md5sum
from OPSI.Types import *


class BackendArchiveFixture(Fixture):
	
	def __init__(self, name=None, mode=None, tempdir=tempfile.gettempdir(), *args, **kwargs):
		Fixture.__init__(self)
		self._archiveName = name
		self._archiveMode = mode
		self._archiveTempDir = tempdir
	
	def setUp(self):
		Fixture.setUp(self)
		self.archive = OpsiBackupArchive(name=self._archiveName, mode=self._archiveMode, tempdir=self._archiveTempDir)
		self.addCleanup(self.cleanUp)

	def cleanUp(self):
		if os.path.exists(self.archive.name):
			os.remove(self.archive.name)

	@property
	def path(self):
		return self.archive.name
	
	def __getattr__(self, name):
		return getattr(self.archive, name)


class BackupArchiveTest(TestCase):

	def test_createBackupArchive(self):
		archive = self.useFixture(BackendArchiveFixture())
		
		self.assertTrue(os.path.exists(archive.path))

	def test_createNamedArchive(self):
		name = "/tmp/%s.tar" % randomString(10)
		archive = self.useFixture(BackendArchiveFixture(name=name, mode="w"))
		self.assertTrue(os.path.exists(name))
		
	def test_immutableArchive(self):
		name = "/tmp/%s.tar" % randomString(10)
		archive = self.useFixture(BackendArchiveFixture(name=name, mode="w"))
		
		self.assertRaises(OpsiBackupFileError, self.useFixture, BackendArchiveFixture(name=name, mode="w"))

	def test_addFile(self):
		archive = self.useFixture(BackendArchiveFixture())
		
		archive._addContent(".")
		archive.close()
	
	def test_backupConfiguration(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupConfiguration()
		archive.close()

		old = []

		for root, ds, files in os.walk(archive.CONF_DIR):
			for d in ds:
				old.append(os.path.join(root, d))
			for file in files:

				old.append(file)
		
		shutil.rmtree(archive.CONF_DIR, ignore_errors="True")
		
		backup = self.useFixture(BackendArchiveFixture(name=archive.name, mode="r"))
		backup.restoreConfiguration()
		backup.close()
		
		new = []
		
		for root, ds, files in os.walk(archive.CONF_DIR):
			for d in ds:
				new.append(os.path.join(root, d))
			for file in files:
				new.append(file)
				
		self.assertEquals(old, new)
	
	def test_hasConfiguration(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupConfiguration()
		archive.close()
		
		backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
		self.assertTrue(backup.hasConfiguration())
		backup.close()

	def test_backupFileBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		
		for backend in archive._getBackends("file"):
			baseDir = backend["config"]["baseDir"]
			old = []
			
			for root, ds, files in os.walk(baseDir):
				for d in ds:
					old.append(os.path.join(root, d))
				for file in files:
					old.append(file)
			
			
			archive.backupFileBackend()
			archive.close()
			
			shutil.rmtree(baseDir, ignore_errors=True)
			os.mkdir(baseDir)
			
			backup = self.useFixture(BackendArchiveFixture(name=archive.name, mode="r"))
			backup.restoreFileBackend()
	
			new = []
			
			for root, ds, files in os.walk(baseDir):
				for d in ds:
					new.append(os.path.join(root, d))
				for file in files:
					new.append(file)
					
			self.assertEquals(old, new)
	
	def test_hasFileBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupFileBackend()
		archive.close()
		
		backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
		self.assertTrue(backup.hasFileBackend())
		backup.close()
	
	def test_backupDHCPBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		
		for backend in archive._getBackends("dhcpd"):
			file = backend['config']['dhcpdConfigFile']
			
			orig = md5sum(file)
			
			
			archive.backupDHCPBackend()
			archive.close()
			
			os.remove(file)
			
			backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
			backup.restoreDHCPBackend()
			
			new = md5sum(file)
			
			self.assertEqual(orig, new)

	def test_hasDHCPBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupDHCPBackend()
		archive.close()
		
		backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
		self.assertTrue(backup.hasDHCPBackend())
		backup.close()
		
	def test_backupMySQLBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupMySQLBackend()
		archive.close()

		orig = {}
		for backend in archive._getBackends("mysql"):
			con = MySQLdb.connect (	host = backend["config"]["address"],
						user = backend["config"]["username"],
						passwd = backend["config"]["password"],
						db = backend["config"]["database"])
		
		
			cursor = con.cursor ()
			cursor.execute ("SHOW TABLES;")
			orig[backend["name"]] = dict.fromkeys([r[0] for r in cursor.fetchall ()])
			for entry in orig[backend["name"]].keys():
				cursor.execute("SELECT COUNT(*) FROM `%s`"% entry)
				count = cursor.fetchone()
				orig[backend["name"]][entry] = count[0]
				cursor.execute("DROP TABLE `%s`" % entry)
			
		backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
		backup.restoreMySQLBackend()
			
		new = {}
		for backend in archive._getBackends("mysql"):
			con = MySQLdb.connect (	host = backend["config"]["address"],
						user = backend["config"]["username"],
						passwd = backend["config"]["password"],
						db = backend["config"]["database"])
			cursor = con.cursor ()
			cursor.execute ("SHOW TABLES;")
			new[backend["name"]] = dict.fromkeys([r[0] for r in cursor.fetchall ()])
			for entry in new[backend["name"]].keys():
				cursor.execute("SELECT COUNT(*) FROM `%s`"% entry)
				count = cursor.fetchone()
				new[backend["name"]][entry] = count[0]
				
		self.assertEqual(orig, new)
	
	def test_hasMySQLBackend(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupMySQLBackend()
		archive.close()

		backup = self.useFixture(BackendArchiveFixture(archive.name, "r"))
		self.assertTrue(backup.hasMySQLBackend())
		backup.close()
		
	def test_backupVerify(self):
		archive = self.useFixture(BackendArchiveFixture())
		archive.backupFileBackend()
		archive.close()

		backup = self.useFixture(BackendArchiveFixture(name=archive.name, mode="r"))
		self.assertTrue(backup.verify())
		backup.close()

#	def test_backupVerifyCorrupted(self):
#		self.skip("TODO: test corrupted Image")
	
	
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)