#!/usr/bin/python
# -*- coding utf-8 -*-

import sys, types

from OPSI.Logger import *
from OPSI.Backend.MySQL import MySQLBackend
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


#init and reset
fileBackend = ExtendedConfigDataBackend(File31Backend())
btfileBackend = BackendTest(fileBackend)
btfileBackend.cleanupBackend()

mysqlBackend = ExtendedConfigDataBackend(MySQLBackend(username = 'opsi', password = 'opsi', database='opsi'))
btmysqlBackend = BackendTest(mysqlBackend)
btmysqlBackend.cleanupBackend()


#create data
btfileBackend.testObjectMethods()
mysqlBackend.backend_createBase()

def check(one, two):
	for objectType in (
	'host',
	'config',
	'configState',
	'product',
	'productProperty',
	'productDependency',
	'productOnDepot',
	'productOnClient',
	'productPropertyState',
	'group',
	'objectToGroup'):
		idents = []
		objects = eval('%s.%s_getObjects()' % (one, objectType))
		for obj in objects:
			idents.append(obj.getIdent(returnType = 'unicode'))
		
		objects = eval('%s.%s_getObjects()' % (two, objectType))
		assert len(objects) == len(idents)
		for obj in objects:
			assert obj.getIdent(returnType = 'unicode') in idents










#convert fileBackend -> mysqlBackend
mysqlBackend.host_createObjects(                  fileBackend.host_getObjects()                 )
mysqlBackend.config_createObjects(                fileBackend.config_getObjects()               )
mysqlBackend.configState_createObjects(           fileBackend.configState_getObjects()          )
mysqlBackend.product_createObjects(               fileBackend.product_getObjects()              )
mysqlBackend.productProperty_createObjects(       fileBackend.productProperty_getObjects()      )
mysqlBackend.productDependency_createObjects(     fileBackend.productDependency_getObjects()    )
mysqlBackend.productOnDepot_createObjects(        fileBackend.productOnDepot_getObjects()       )
mysqlBackend.productOnClient_createObjects(       fileBackend.productOnClient_getObjects()      )
mysqlBackend.productPropertyState_createObjects(  fileBackend.productPropertyState_getObjects() )
mysqlBackend.group_createObjects(                 fileBackend.group_getObjects()                )
mysqlBackend.objectToGroup_createObjects(         fileBackend.objectToGroup_getObjects()        )

check('fileBackend', 'mysqlBackend')



#btfileBackend.cleanupBackend()

#convert mysqlBackend -> btfileBackend
fileBackend.host_createObjects(                  mysqlBackend.host_getObjects()                 )
fileBackend.config_createObjects(                mysqlBackend.config_getObjects()               )
fileBackend.configState_createObjects(           mysqlBackend.configState_getObjects()          )
fileBackend.product_createObjects(               mysqlBackend.product_getObjects()              )
fileBackend.productProperty_createObjects(       mysqlBackend.productProperty_getObjects()      )
fileBackend.productDependency_createObjects(     mysqlBackend.productDependency_getObjects()    )
fileBackend.productOnDepot_createObjects(        mysqlBackend.productOnDepot_getObjects()       )
fileBackend.productOnClient_createObjects(       mysqlBackend.productOnClient_getObjects()      )
fileBackend.productPropertyState_createObjects(  mysqlBackend.productPropertyState_getObjects() )
fileBackend.group_createObjects(                 mysqlBackend.group_getObjects()                )
fileBackend.objectToGroup_createObjects(         mysqlBackend.objectToGroup_getObjects()        )

check('mysqlBackend', 'fileBackend')

