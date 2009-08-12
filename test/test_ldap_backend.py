#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.LDAP import LDAPBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)



ldapBackend = LDAPBackend(username = 'opsi', password = 'opsi')
bt = BackendTest(ldapBackend)
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()


























