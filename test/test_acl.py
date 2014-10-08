#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import sys

from OPSI.Logger import Logger, LOG_DEBUG2
from OPSI.Backend import *
from OPSI.Backend.MySQL import MySQLBackend
from OPSI.Backend.BackendManager import *
from OPSI.Util.File.Opsi import BackendACLFile
# from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)

TMP_CONFIG_DIR = '/tmp/opsi_test_acl_conf'

if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)
os.mkdir(TMP_CONFIG_DIR)

aclFile = os.path.join(TMP_CONFIG_DIR, 'acl.conf')
with open(aclFile, 'w') as f:
	f.write(
'''
host_.*: opsi_depotserver(depot1.uib.local, depot2.uib.local); opsi_client(self,  attributes (attr1, attr2)) ; sys_user(some user, some other user) ; sys_group(a_group, group2)
'''
	)

print(BackendACLFile(aclFile).parse())

# Create a backend
backend = MySQLBackend(username='opsi', password='opsi', address='localhost', database='opsi')

# Fill backend
backendTest = BackendTest(backend)
backendTest.cleanupBackend()
backendTest.testObjectMethods()


# Create backend access control
backendAccessControl = BackendAccessControl(
	username = backendTest.client1.id,
	password = backendTest.client1.opsiHostKey,
	backend  = backend,
	acl      = [
		['productOnClient_create', [ {'type': u'self', 'ids': [], 'denyAttributes': [], 'allowAttributes': []} ] ],
	])

backendAccessControl.productOnClient_create(
			productId = backendTest.product1.id,
			productType = backendTest.product1.getType(),
			clientId = backendTest.client1.id,
			installationStatus = 'installed')
try:
	backendAccessControl.productOnClient_create(
		productId = backendTest.product1.id,
		productType = backendTest.product1.getType(),
		clientId = backendTest.client2.id,
		installationStatus = 'installed')
except Exception, e:
	logger.error(e)
	logger.notice("OK, permission was denied")
else:
	raise Exception("Permission was not denied")


#####################################
if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)
