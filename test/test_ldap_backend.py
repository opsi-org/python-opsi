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

baseDn = u'dc=uib,dc=local'
ldapBackend = LDAPBackend(
	username         = "cn=admin,%s" % baseDn,
	password         = "linux123",
	adress           = "localhost",
	opsiBaseDn       = "cn=opsi,%s" % baseDn,
	hostsContainerDn = u"cn=hosts,cn=opsi,%s" % baseDn
)

bt = BackendTest(ExtendedConfigDataBackend(ldapBackend))
bt.cleanupBackend()
ldapBackend.backend_createBase()
bt.testObjectMethods()
bt.testNonObjectMethods()
bt.testPerformance(clientCount=100, productCount=50)























