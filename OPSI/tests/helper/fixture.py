
import os

from testtools.monkey import patch
from fixtures import Fixture
import fixtures

from OPSI.Util.File.Opsi import BackendDispatchConfigFile

class FQDNFixture(Fixture):
	
	def __init__(self, fqdn="opsi.uib.local", address="172.16.0.1"):
		
		self.hostname = fqdn.split(".")[0]
		self.fqdn = fqdn
		self.address = address
		
	def setUp(self):
		super(FQDNFixture, self).setUp()
		
		def getfqdn(_ignore):
			return self.fqdn
		
		def gethostbyaddr(_ignore):
			return (self.fqdn, [self.hostname], [self.address])
		
		self.useFixture(fixtures.MonkeyPatch('socket.getfqdn', getfqdn))
		self.useFixture(fixtures.MonkeyPatch('socket.gethostbyaddr', gethostbyaddr))

class GlobalConfFixture(Fixture):
	
	template = """[global]
hostname = #hostname#
"""
	
	def __init__(self, fqdn="opsi.uib.local"):
		self.fqdn = fqdn
		
	def setUp(self):
		super(GlobalConfFixture, self).setUp()
		self.dir = self.useFixture(fixtures.TempDir())
		self.path = os.path.join(self.dir.path, "global.conf")
		
		s = self.template.replace("#hostname#", self.fqdn)
		try:
			f = open(self.path, "w")
			f.write(s)

		except Exception, e:
			self.addDetail("conferror", e)
			self.test.fail("Could not generate global.conf.")
		finally:
			f.close()

class DispatchConfigFixture(Fixture):
	
	template = """
	backend_.*         : #backend#, opsipxeconfd, #dhcp#
	host_.*            : #backend#, opsipxeconfd, #dhcp#
	productOnClient_.* : #backend#, opsipxeconfd
	configState_.*     : #backend#, opsipxeconfd
	.*                 : #backend#
	"""
	
	def __init__(self, prefix=None, dir=None):
		
		super(DispatchConfigFixture, self).__init__()
		self.prefix = prefix
		self.dir = dir
		self.data = None
		
	def setUp(self):
		super(DispatchConfigFixture, self).setUp()
		
		if self.dir is None:
			self.dir = self.useFixture(fixtures.TempDir()).path
		if self.prefix is not None:
			self.dir = os.path.join(self.dir, self.prefix)
		self.path = self.dir
	
	def _generateDispatchConf(self, data):
		self.data = data
		path = os.path.join(self.path, "dispatch.conf")
		f = file(path, "w")
		f.write(data)
		f.close()
		
		self.config = BackendDispatchConfigFile(path)

	def setupFile(self):
		conf = self.template.replace("#backend#", "file")
		self._generateDispatchConf(conf)
		
	def setupMySQL(self):
		conf = self.template.replace("#backend#", "mysql")
		self._generateDispatchConf(conf)
		
	def setupLDAP(self):
		conf = self.template.replace("#backend#", "ldap")
		self._generateDispatchConf(conf)
		
	def setupDHCP(self):
		if self.data is not None:
			conf = self.data.replace("#dhcp#", "dhcpd")
		else:
			conf = self.template.replace("#dhcp#", "dhcpd")
		self._generateDispatchConf(conf)
		
		
		
