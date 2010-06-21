
import os, pwd, grp

from ConnectionHelper import *

from OPSI.Backend import HostControl
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Backend.File import FileBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from BackendTest import BackendTestCase

	
class HostControlTestCase(BackendTestCase):
	
	@classmethod
	def setUpClass(cls):
		HostControl.socket.socket = DummySocket
		HostControl.non_blocking_connect_https = dummy_connect_http
		HostControl.httplib.HTTPSConnection = DummyHttpConnection
		
	def createBackend(self):
		
		env = os.environ.copy()
		uid = gid = env["USER"]
		fileBackend = FileBackend(baseDir = u'/tmp/opsi-file-backend-test', hostKeyFile = u'/tmp/opsi-file-backend-test/pckeys')
		fileBackend.__fileUid = pwd.getpwnam(uid)[2]
		fileBackend.__fileGid = grp.getgrnam(gid)[2]
		fileBackend.__dirUid  = pwd.getpwnam(uid)[2]
		fileBackend.__dirGid  = grp.getgrnam(gid)[2]
		
		self.backend = HostControlBackend(ExtendedConfigDataBackend(fileBackend))
		self.backend.backend_createBase()
		
		
	def test_HostControlBackend(self):
		#try:
			self.backend.hostControl_start([u'client1.uib.local'])
			self.backend.hostControl_shutdown([u'client1.uib.local'])
		#except Exception, e:
		#	self.fail("HostControlBackend test failed with: %s;"% (e))