#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.File import FileBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()

loglevel = LOG_NONE
loglevel = LOG_COMMENT
loglevel = LOG_CRITICAL
loglevel = LOG_ERROR
loglevel = LOG_WARNING
loglevel = LOG_NOTICE
loglevel = LOG_INFO
loglevel = LOG_DEBUG
loglevel = LOG_DEBUG2
#loglevel = LOG_CONFIDENTIAL


logger.setConsoleLevel(loglevel)
logger.setConsoleColor(True)
#logger.setConsoleFormat('%D [%L] %M (%F|%N)')

fileBackend = FileBackend(baseDir = u'/tmp/opsi-file-backend-test', hostKeyFile = u'/tmp/opsi-file-backend-test/pckeys')
#fileBackend = FileBackend(baseDir = u'/var/lib/opsi/config', hostKeyFile = u'/etc/opsi/pckeys')

# standardtests
bt = BackendTest(ExtendedConfigDataBackend(fileBackend))
bt.cleanupBackend()
#bt.testObjectMethods()
#bt.testInventoryObjectMethods()
#bt.testNonObjectMethods()
bt.testMultithreading()
#bt.testPerformance()









