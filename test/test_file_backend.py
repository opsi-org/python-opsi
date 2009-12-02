#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.File31 import File31Backend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.Object import *
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)

file31Backend = File31Backend()

#for host in file31Backend.host_getObjects():
#	print "all hosts: '%s'" % host.toHash()
#for host in file31Backend.host_getObjects(attributes = [], id = '*local'):
#	print "all local hosts: '%s'" % host.toHash()



#file31Backend.host_deleteObjects(client)

#


bt = BackendTest(ExtendedConfigDataBackend(file31Backend))
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()
#bt.testPerformance()
























