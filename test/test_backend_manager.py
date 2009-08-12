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

os.mkdir(backendConfigDir)
f = open(dipatchConfigFile, 'w')
f.write(
'''
.*: mysql
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
bt = BackendTest(bm)
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()


sys.exit(0)
########################################
bm = BackendManager(
	dispatchConfigFile = 'files/dispatch.conf',
	backendConfigDir   = 'files/backends',
	username           = bt.configserver1.getId(),
	password           = bt.configserver1.getOpsiHostKey(),
	aclFile            = 'files/acl.conf')
bt = BackendTest(bm)
bt.cleanupBackend()
bt.testObjectMethods()
#bt.testNonObjectMethods()


if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)





















