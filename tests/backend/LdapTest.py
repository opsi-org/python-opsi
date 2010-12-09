import os, pwd, grp

from OPSI.Backend.LDAP import LDAPBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Object import *
from opsidevtools.unittest.lib import unittest2 as unittest

from BackendTest import *
from BackendMixins.ObjectMethodsMixin import ObjectMethodsMixin
from BackendMixins.NonObjectMethodsMixin import NonObjectMethodsMixin
from BackendMixins.InventoryObjectMethodMixin import InventoryObjectMethodMixin
from BackendMixins.MultithreadingMixin import MultithreadingMixin
from BackendMixins.LicenseManagementObjectsMixin import LicenseManagementObjectsMixin

class LdapTestCase(BackendTestCase,
		    ObjectMethodsMixin,
		    NonObjectMethodsMixin,
		    #MultithreadingMixin
		):
	
	def createBackend(self):
		baseDn = u'dc=uib,dc=local'
		ldapBackend = LDAPBackend(
					username         = "cn=admin,%s" % baseDn,
					password         = "linux123",
					address           = "vmax19100",
					opsiBaseDn       = "cn=opsi-test,%s" % baseDn,
					hostsContainerDn = u"cn=hosts,cn=opsi-test,%s" % baseDn
					)
		
		self.backend = ExtendedConfigDataBackend(ldapBackend)
		
	@unittest.expectedFailure
	def test_Multithreading(self):
		MultithreadingMixin(LdapTestCase, self).test_Multithreading()
