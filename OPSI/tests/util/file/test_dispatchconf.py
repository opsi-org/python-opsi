

from OPSI.tests.helper.testcase import TestCase
from OPSI.tests.helper.fixture import DispatchConfigFixture

class DispatchConfigTests(TestCase):
	
	def test_parseFile(self):
		f = self.useFixture(DispatchConfigFixture())
		f.setupFile()
		data = f.config.parse()
		
		for entry in data:
			self.assertIn("file", entry[1])
	
	def test_parseMySQL(self):
		f = self.useFixture(DispatchConfigFixture())
		f.setupMySQL()
		data = f.config.parse()
		
		for entry in data:
			self.assertIn("mysql", entry[1])
	
	def test_parseLDAP(self):
		f = self.useFixture(DispatchConfigFixture())
		f.setupLDAP()
		data = f.config.parse()
		
		for entry in data:
			self.assertIn("ldap", entry[1])
			
	
	def test_parseDHCP(self):
		f = self.useFixture(DispatchConfigFixture())
		f.setupDHCP()
		data = f.config.parse()
		
		for entry in data[:1]:
			self.assertIn("dhcpd", entry[1])
	
	def test_parseFileAndDHCP(self):
		f = self.useFixture(DispatchConfigFixture())
		f.setupFile()
		f.setupDHCP()
		data = f.config.parse()
	
		for entry in data:
			self.assertIn("file", entry[1])
	
		for entry in data[:1]:
			self.assertIn("dhcpd", entry[1])
	
	
def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)