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
	for objectType in ('host', 'config', 'configState', 'product', 'productProperty', 'productDependency', 'productOnDepot', 'productOnClient', 'productPropertyState', 'group', 'objectToGroup'):
		oneIdents = []
		twoIdents = []
		
		oneObjects = eval('%s.%s_getObjects()' % (one, objectType))
		twoObjects = eval('%s.%s_getObjects()' % (two, objectType))
		
		for oneObject in oneObjects:
			oneIdents.append(oneObject.getIdent(returnType = 'unicode'))
		for twoObject in twoObjects:
			twoIdents.append(twoObject.getIdent(returnType = 'unicode'))
		
		logger.warning(u"assert length %s\noneIdents: '%s'\ntwoIdents: '%s'" \
			% (objectType, oneIdents, twoIdents))
		assert len(oneIdents) == len(twoIdents)
		
		for oneIdent in oneIdents:
			isSameIdent = False
			for twoIdent in twoIdents:
				if oneIdent == twoIdent:
					isSameIdent = True
					break
			logger.warning(u"assert oneIdent '%s' is in twoIdents: '%s'" % (oneIdent, isSameIdent))
			assert isSameIdent
		










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

fileBackend.host_deleteObjects(                  fileBackend.host_getObjects()                 )
fileBackend.config_deleteObjects(                fileBackend.config_getObjects()               )
fileBackend.configState_deleteObjects(           fileBackend.configState_getObjects()          )
fileBackend.product_deleteObjects(               fileBackend.product_getObjects()              )
fileBackend.productProperty_deleteObjects(       fileBackend.productProperty_getObjects()      )
fileBackend.productDependency_deleteObjects(     fileBackend.productDependency_getObjects()    )
fileBackend.productOnDepot_deleteObjects(        fileBackend.productOnDepot_getObjects()       )
fileBackend.productOnClient_deleteObjects(       fileBackend.productOnClient_getObjects()      )
fileBackend.productPropertyState_deleteObjects(  fileBackend.productPropertyState_getObjects() )
fileBackend.group_deleteObjects(                 fileBackend.group_getObjects()                )
fileBackend.objectToGroup_deleteObjects(         fileBackend.objectToGroup_getObjects()        )



for objectType in ('host', 'config', 'configState', 'product', 'productProperty', 'productDependency', 'productOnDepot', 'productOnClient', 'productPropertyState', 'group', 'objectToGroup'):
	idents = []
	
	objects = eval('fileBackend.%s_getObjects()' % objectType)
	
	for obj in objects:
		idents.append(obj.getIdent(returnType = 'unicode'))
	
	logger.warning(u"assert length %s-idents: '%s'" \
		% (objectType, idents))
	assert len(idents) == 0

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

m = mysqlBackend.host_getObjects()
f = fileBackend.host_getObjects()
print "m:", m, "\nf:", f


