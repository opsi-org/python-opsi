#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.File31 import File31Backend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)

file31Backend = File31Backend()

client = OpsiClient(
	id = 'schwarz.uib.local',
	opsiHostKey = None,
	description=None,
	notes=None,
	hardwareAddress=None,
	ipAddress=None,
	inventoryNumber=None,
	created=None,
	lastSeen=None)

#file31Backend.host_insertObject(client)

#file31Backend.host_deleteObjects(client)

#
bt = BackendTest(ExtendedConfigDataBackend(file31Backend))
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()
#bt.testPerformance()
























