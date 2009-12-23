#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.File31 import File31Backend
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Backend.Object import *
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_CONFIDENTIAL)
logger.setConsoleColor(True)
#logger.setConsoleFormat('%D [%L] %M (%F|%N)')

file31Backend = File31Backend()



#pp0 = BoolProductProperty(
#	productId      = 'product1',
#	productVersion = 'pp0prodVe',
#	packageVersion = 'pp0packVe',
#	propertyId     = 'pp0propId',
#	description    = 'pp0desc',
#	defaultValues  = True
#)

#file31Backend.productProperty_deleteObjects([pp0])
#exit()



bt = BackendTest(ExtendedConfigDataBackend(file31Backend))
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()
#bt.testPerformance()












