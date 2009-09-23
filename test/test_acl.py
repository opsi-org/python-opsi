#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, shutil

from OPSI.Logger import *
from OPSI.Backend import *
from OPSI.Backend.MySQL import *
from OPSI.Backend.BackendManager import *
from OPSI.Backend.Object import *
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)

TMP_CONFIG_DIR = '/tmp/opsi_test_acl_conf'

if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)
os.mkdir(TMP_CONFIG_DIR)

aclFile = os.path.join(TMP_CONFIG_DIR, 'acl.conf')
f = open(aclFile, 'w')
f.write(
'''
host_.*: opsi_depotserver(depot1.uib.local, depot2.uib.local); opsi_client(self,  attributes (attr1, attr2)) ; sys_user(some user, some other user) ; sys_group(a_group, group2)
'''
)
f.close()

from OPSI.Util.File import OpsiBackendACLFile
print OpsiBackendACLFile(aclFile).parse()


# Create a backend
backend = MySQLBackend(username = 'opsi', password = 'opsi', address = 'localhost', database = 'opsi')

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
		['host_getObjects',        [ {'type': u'opsi_client', 'ids': [ backendTest.client1.id ], 'denyAttributes': [], 'allowAttributes': []} ] ],
		['config_getObjects',      [ {'type': u'opsi_client', 'ids': [ backendTest.client2.id ], 'denyAttributes': [], 'allowAttributes': []} ] ],
	])

backendAccessControl.host_getObjects()
try:
	backendAccessControl.config_getObjects()
except Exception, e:
	logger.error(e)
else:
	raise Exception("Permission was not denied")

# Create backend access control
backendAccessControl = BackendAccessControl(
	username = backendTest.client1.id,
	password = backendTest.client1.opsiHostKey,
	backend  = backend,
	acl      = [
		['host_getObjects',        [ {'type': u'self',        'ids': [], 'denyAttributes': [],                'allowAttributes': []} ] ],
		['host_getObjects',        [ {'type': u'opsi_client', 'ids': [], 'denyAttributes': [ 'opsiHostKey' ], 'allowAttributes': []} ] ],
	])

for host in backendAccessControl.host_getObjects():
	if (host.id == backendTest.client1.id):
		assert host.opsiHostKey == backendTest.client1.opsiHostKey
	else:
		assert host.opsiHostKey == None

# Create backend access control
backendAccessControl = BackendAccessControl(
	username = backendTest.client1.id,
	password = backendTest.client1.opsiHostKey,
	backend  = backend,
	acl      = [
		['host_.*',       [ {'type': u'self',        'ids': [], 'denyAttributes': [],                'allowAttributes': [         ]} ] ],
		['host_get.*',    [ {'type': u'opsi_client', 'ids': [], 'denyAttributes': [ 'opsiHostKey' ], 'allowAttributes': [         ]} ] ],
		['host_update.*', [ {'type': u'opsi_client', 'ids': [], 'denyAttributes': [],                'allowAttributes': [ 'notes' ]} ] ]
	])

backendTest.client1.setDescription("A new description")
backendTest.client2.setDescription("A new description")
backendTest.client3 = OpsiClient(id = backendTest.client3.id, notes = backendTest.client3.notes)

backendAccessControl.host_updateObject(backendTest.client1)
try:
	backendAccessControl.host_updateObject(backendTest.client2)
except Exception, e:
	logger.error(e)
else:
	raise Exception("Permission was not denied")

backendAccessControl.host_updateObject(backendTest.client3)
backendTest.client3 = backendAccessControl.host_getObjects(id = backendTest.client3.id)[0]

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

























