#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing a manual backend conversion.
"""

from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.File import FileBackend
from OPSI.Backend.Backend import ExtendedConfigDataBackend

logger = Logger()


def main():
	# TODO: make this a test that is run automatically
	#init and reset
	fileBackend = ExtendedConfigDataBackend(FileBackend())
	fileBackend.backend_deleteBase()
	fileBackend.backend_createBase()

	mysqlBackend = ExtendedConfigDataBackend(MySQLBackend(username='opsi', password='opsi', database='opsi'))
	mysqlBackend.backend_deleteBase()
	mysqlBackend.backend_createBase()


	def check(one, two):
		objectTypesToCheck = (
			'host', 'config', 'configState', 'product', 'productProperty',
			'productDependency', 'productOnDepot', 'productOnClient',
			'productPropertyState', 'group', 'objectToGroup'
		)

		for objectType in objectTypesToCheck:
			oneObjects = eval('%s.%s_getObjects()' % (one, objectType))
			twoObjects = eval('%s.%s_getObjects()' % (two, objectType))

			oneIdents = [oneObject.getIdent(returnType='unicode') for oneObject in oneObjects]
			twoIdents = [twoObject.getIdent(returnType='unicode') for twoObject in twoObjects]

			logger.warning(u"assert length %s\noneIdents: '%s'\ntwoIdents: '%s'" % (objectType, oneIdents, twoIdents))
			assert len(oneIdents) == len(twoIdents)

			for oneIdent in oneIdents:
				assert any(oneIdent == twoIdent for twoIdent in twoIdents)

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


	objectTypes = (
		'host', 'config', 'configState', 'product', 'productProperty',
		'productDependency', 'productOnDepot', 'productOnClient',
		'productPropertyState', 'group', 'objectToGroup'
	)
	for objectType in objectTypes:
		objects = eval('fileBackend.%s_getObjects()' % objectType)
		idents = [obj.getIdent(returnType = 'unicode') for obj in objects]

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

	print("-------------------------------------")
	print("- seem to work ... all tests passed -")
	print("-------------------------------------")


if __name__ == '__main__':
	logger.setConsoleLevel(LOG_DEBUG)
	logger.setConsoleColor(True)

	main()
