#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.File31 import File31Backend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.Object import *
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

file31Backend = File31Backend()

bt = BackendTest(ExtendedConfigDataBackend(file31Backend))
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()
#bt.testPerformance()












