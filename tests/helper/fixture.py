
import os

from testtools.monkey import patch
from fixtures import Fixture as _Fixture
import fixtures

from OPSI.Util.File.Opsi import BackendDispatchConfigFile

class Fixture(_Fixture):
	
	def patch(self, obj, attribute, value):
		self.addCleanup(patch(obj, attribute, value))



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
		
		
		
