from OPSI.tests.helper.testcase import TestCase
from OPSI.tests.helper.fixture import GlobalConfFixture, FQDNFixture

from fixtures import EnvironmentVariableFixture

from OPSI.Util import getfqdn, randomString


class UtilTestCase(TestCase):
	def test_getfqdn(self):
		fqdn = "opsi.uib.local"
		self.useFixture(FQDNFixture(fqdn=fqdn))

		self.assertEqual(fqdn, getfqdn())

	def test_getfqdnFromConf(self):
		self.useFixture(FQDNFixture(fqdn="nomatch.uib.local"))

		fqdn = "opsi.uib.local"
		f = self.useFixture(GlobalConfFixture(fqdn=fqdn))

		self.assertEqual(fqdn, getfqdn(conf=f.path))

	def test_getfqdn_noConf(self):
		fqdn = "opsi.uib.local"
		self.useFixture(FQDNFixture(fqdn=fqdn))

		self.assertEqual(fqdn, getfqdn(conf=randomString(32)))

	def test_getfqdn_emptyConf(self):
		fqdn = "opsi.uib.local"
		self.useFixture(FQDNFixture(fqdn=fqdn))

		f = self.useFixture(GlobalConfFixture())
		fp = open(f.path,"w")
		fp.write("")
		fp.close()

		self.assertEqual(fqdn, getfqdn(conf=f.path))

	def test_getfqdn_environment(self):
		fqdn = "opsi.uib.local"
		self.useFixture(FQDNFixture(fqdn="nomatch.uib.local"))
		self.useFixture(GlobalConfFixture(fqdn="nomatch.uib.local"))
		self.useFixture(EnvironmentVariableFixture('OPSI_HOSTNAME', fqdn))

		self.assertEqual(fqdn, getfqdn())

	def test_getfqdn_byname(self):
		fqdn = "opsi.uib.local"
		address = '127.0.0.1'
		self.useFixture(FQDNFixture(fqdn=fqdn, address=address))

		self.assertEqual(fqdn, getfqdn(name=address))


def test_suite():
	from unittest import TestLoader
	return TestLoader().loadTestsFromName(__name__)
