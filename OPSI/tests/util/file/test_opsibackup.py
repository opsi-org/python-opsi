
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


def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)