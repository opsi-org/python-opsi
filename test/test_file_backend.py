#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.File31 import File31Backend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)

file31Backend = File31Backend()

bt = BackendTest(ExtendedConfigDataBackend(file31Backend))
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()
#bt.testPerformance()

























