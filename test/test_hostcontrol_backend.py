#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.HostControl import HostControlBackend

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)



hostControlBackend = HostControlBackend()
hostControlBackend.hostControl_start([u'client1.uib.local'])
hostControlBackend.hostControl_shutdown([u'client1.uib.local'])












