#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)



mysqlBackend = MySQLBackend(username = 'opsi', password = 'opsi', database='opsi')

bt = BackendTest(ExtendedConfigDataBackend(mysqlBackend))
bt.cleanupBackend()
bt.testObjectMethods()
bt.testNonObjectMethods()
#bt.testPerformance()

























