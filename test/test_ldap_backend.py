#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.LDAP import LDAPBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)
logger.setLogFile("out.log")


baseDn = u'dc=uib,dc=local'
ldapBackend = LDAPBackend(
	username         = "cn=admin,%s" % baseDn,
	password         = "linux123",
	adress           = "localhost",
	opsiBaseDn       = "cn=opsi-ldap-test,%s" % baseDn,
	hostsContainerDn = u"cn=hosts,cn=opsi-ldap-test,%s" % baseDn
)

'''
print ldapBackend._objectFilterToLDAPFilter( {"type": ['OpsiClient']})
print ldapBackend._objectFilterToLDAPFilter( {"type": 'OpsiDepotserver'})
print ldapBackend._objectFilterToLDAPFilter( {"type": ['OpsiDepotserver', 'OpsiClient']} )
print ldapBackend._objectFilterToLDAPFilter( {"type": None} )
print ldapBackend._objectFilterToLDAPFilter( {"type": [ None ]} )
'''
#print ldapBackend.host_

#sys.exit(0)

'''
ldapBackend.host_getObjects()
ldapBackend.host_getObjects(type = 'OpsiClient')
ldapBackend.host_getObjects(type = 'OpsiDepotserver')
ldapBackend.host_getObjects(type = ['OpsiClient', 'OpsiDepotserver'], description="something", ipAddress = ['192.168.1.1', '192.168.2.1'])
ldapBackend.host_getObjects(type = ['OpsiClient', None])
ldapBackend.host_getObjects(type = None)
sys.exit(0)
'''


bt = BackendTest(ExtendedConfigDataBackend(ldapBackend))
bt.cleanupBackend()
ldapBackend.backend_createBase()
bt.testObjectMethods()
bt.testNonObjectMethods()
bt.testPerformance(clientCount=100, productCount=50)


























