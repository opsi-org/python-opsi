#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, shutil

from OPSI.Logger import *
from OPSI.Backend.BackendManager import *
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG2)
logger.setConsoleColor(True)

TMP_CONFIG_DIR = '/tmp/opsi_test_backend_manager_conf'

if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)
os.mkdir(TMP_CONFIG_DIR)

dipatchConfigFile = os.path.join(TMP_CONFIG_DIR, 'dispatch.conf')
backendConfigDir = os.path.join(TMP_CONFIG_DIR, 'backends')
aclFile = os.path.join(TMP_CONFIG_DIR, 'acl.conf')

os.mkdir(backendConfigDir)

f = open(dipatchConfigFile, 'w')
f.write(
'''
.*: mysql
'''
)
f.close()

f = open(aclFile, 'w')
f.write(
'''
.*: opsi_depotserver
'''
)
f.close()

f = open(os.path.join(backendConfigDir, 'mysql.conf'), 'w')
f.write(
'''
module = 'MySQL'
config = {
    "address":  "localhost",
    "database": "opsi",
    "username": "opsi",
    "password": "opsi"
}
'''
)
f.close()

bm = BackendManager(
	dispatchConfigFile = dipatchConfigFile,
	backendConfigDir = backendConfigDir)
bt = BackendManagerTest(bm)
bt.cleanupBackend()
bt.testObjectMethods()

bm = BackendManager(
	dispatchConfigFile = dipatchConfigFile,
	backendConfigDir   = backendConfigDir,
	username           = bt.configserver1.getId(),
	password           = bt.configserver1.getOpsiHostKey(),
	aclFile            = aclFile)
bt = BackendManagerTest(bm)
bt.cleanupBackend()
bt.testObjectMethods()

f = open(aclFile, 'w')
f.write(
'''
host_.*: opsi_depotserver
'''
)
f.close()

bm = BackendManager(
	dispatchConfigFile = dipatchConfigFile,
	backendConfigDir   = backendConfigDir,
	username           = bt.configserver1.getId(),
	password           = bt.configserver1.getOpsiHostKey(),
	aclFile            = aclFile)
bm.host_createObjects(bt.hosts)

exception = None
try:
	bm.product_createObjects(bt.products)
except Exception, e:
	exception = e
assert isinstance(exception, BackendPermissionDeniedError)


if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)





















