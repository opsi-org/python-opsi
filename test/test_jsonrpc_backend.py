#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

from OPSI.Logger import *
from OPSI.Backend.JSONRPC import JSONRPCBackend
from backend import *

logger = Logger()
#logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleLevel(LOG_NOTICE)
logger.setConsoleColor(True)

jsonrpcBackend = JSONRPCBackend(username = 'username', password = 'password', adress = 'localhost')

bt = BackendTest(jsonrpcBackend)
bt.cleanupBackend()
jsonrpcBackend.base_create()
bt.testObjectMethods()
bt.testNonObjectMethods()
bt.testMultithreading()

jsonrpcBackend.exit()






















