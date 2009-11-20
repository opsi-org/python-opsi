#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.LDAP import LDAPBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)



ldapBackend = LDAPBackend(username = 'cn=admin,dc=uib,dc=local', password = 'linux123', adress = 'localhost')


bt = BackendTest(ldapBackend)
bt.cleanupBackend()
#ldapBackend.base_create()
bt.testObjectMethods()
#bt.testNonObjectMethods()


























