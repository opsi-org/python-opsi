#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, shutil

from OPSI.Logger import *
from OPSI import Tools
from OPSI.Backend.BackendManager import *
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from backend import *

logger = Logger()
logger.setConsoleLevel(LOG_NOTICE)
logger.setConsoleColor(True)

TMP_CONFIG_DIR = '/tmp/opsi_test_backend_manager_conf'

if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)
os.mkdir(TMP_CONFIG_DIR)

dispatchConfigFile = os.path.join(TMP_CONFIG_DIR, 'dispatch.conf')
backendConfigDir = os.path.join(TMP_CONFIG_DIR, 'backends')
aclFile = os.path.join(TMP_CONFIG_DIR, 'acl.conf')
extensionConfigDir = '../files/backendManager/compose.d'

os.mkdir(backendConfigDir)

f = open(dispatchConfigFile, 'w')
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
	dispatchConfigFile = dispatchConfigFile,
	backendConfigDir = backendConfigDir)
bt = BackendManagerTest(bm)
bt.cleanupBackend()
bt.testObjectMethods()

if False:
	bm = BackendManager(
		dispatchConfigFile = dispatchConfigFile,
		backendConfigDir   = backendConfigDir,
		username           = bt.configserver1.getId(),
		password           = bt.configserver1.getOpsiHostKey(),
		aclFile            = aclFile)
	bt = BackendManagerTest(bm)
	bt.cleanupBackend()
	bt.testObjectMethods()

def testComposition():
	bm = BackendManager(
		dispatchConfigFile = dispatchConfigFile,
		backendConfigDir   = backendConfigDir,
		extensionconfigdir = extensionConfigDir,
		username           = bt.configserver1.getId(),
		password           = bt.configserver1.getOpsiHostKey(),
		aclFile            = aclFile)
	
	#print "===========>>>>>>>>>>>>>>>>", bm.getInterface()
	#print bm.authenticated()
	#sys.exit(0)
	
	hostIds = bm.host_getIdents()
	logger.comment(hostIds)
	for host in bt.hosts:
		assert host.id in hostIds
	
	values = bm.configState_getValues(configId = [], objectId = [])
	logger.comment(values)
	for host in bt.hosts:
		assert host.id in values.keys()
	
	generalConfig = bm.getGeneralConfig_hash()
	logger.comment(generalConfig)
	
	generalConfig = bm.getGeneralConfig_hash(objectId = bt.client1.id)
	logger.comment(generalConfig)
	
	value = bm.getGeneralConfigValue(key = bt.config1.id, objectId = None)
	logger.comment(value)
	assert value == bt.config1.defaultValues[0]
	
	generalConfig = {'test-key-1': 'test-value-1', 'test-key-2': 'test-value-2', 'opsiclientd.depot_server.depot_id': bt.depotserver1.id}
	bm.setGeneralConfig(config = generalConfig, objectId = None)
	
	value = bm.getGeneralConfigValue(key = generalConfig.keys()[0], objectId = bt.client1.id)
	logger.comment(value)
	assert value == generalConfig[generalConfig.keys()[0]]
	
	bm.setGeneralConfigValue(generalConfig.keys()[1], bt.client1.id, objectId = bt.client1.id)
	bm.setGeneralConfigValue(generalConfig.keys()[1], 'changed', objectId = None)
	value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = None)
	logger.comment(value)
	assert value == 'changed'
	value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = bt.client1.id)
	logger.comment(value)
	assert value == bt.client1.id
	
	bm.deleteGeneralConfig(bt.client1.id)
	value = bm.getGeneralConfigValue(key = generalConfig.keys()[1], objectId = bt.client1.id)
	logger.comment(value)
	assert value == 'changed'
	
	groupIds = bm.getGroupIds_list()
	logger.comment(groupIds)
	for group in bt.groups:
		assert group.id in groupIds
	
	groupId = 'a test group'
	bm.createGroup(groupId, members = [ bt.client1.id, bt.client2.id ], description = "A test group", parentGroupId="")
	groups = bm.group_getObjects(id = groupId)
	logger.comment(groups)
	assert len(groups) == 1
	
	objectToGroups = bm.objectToGroup_getObjects(groupId = groupId)
	logger.comment(objectToGroups)
	assert len(objectToGroups) == 2
	for objectToGroup in objectToGroups:
		assert objectToGroup.objectId in [ bt.client1.id, bt.client2.id ]
	
	bm.deleteGroup(groupId = groupId)
	groups = bm.group_getObjects(id = groupId)
	assert len(groups) == 0
	
	ipAddress = bm.getIpAddress(hostId = bt.client1.id)
	logger.comment(ipAddress)
	assert ipAddress == bt.client1.ipAddress
	
	serverName = 'test-server'
	domain = 'uib.local'
	serverId = bm.createServer(serverName = serverName, domain = domain, description = 'Some description', notes=None)
	logger.comment(serverId)
	assert serverId == serverName + '.' + domain
	
	serverIds = bm.host_getIdents(type = 'OpsiConfigserver')
	logger.comment(serverIds)
	assert serverId in serverIds
	
	clientName = 'test-client'
	clientId = bm.createClient(clientName = clientName, domain = domain, description = 'a description', notes = 'notes...', ipAddress = '192.168.1.91', hardwareAddress = '00:01:02:03:01:aa')
	logger.comment(clientId)
	assert clientId == clientName + '.' + domain
	
	clientIds = bm.host_getIdents(type = 'OpsiClient')
	logger.comment(clientIds)
	assert clientId in clientIds
	
	bm.deleteServer(serverId)
	serverIds = bm.host_getIdents(type = 'OpsiConfigserver')
	logger.comment(serverIds)
	assert serverId not in serverIds
	
	bm.deleteClient(clientId)
	clientIds = bm.host_getIdents(type = 'OpsiClient')
	logger.comment(clientIds)
	assert clientId not in clientIds
	
	lastSeen = '2009-01-01 00:00:00'
	description = 'Updated description'
	notes = 'Updated notes'
	opsiHostKey = '00000000001111111111222222222233'
	mac = '00:01:02:03:40:12'
	bm.setHostLastSeen(hostId = bt.client1.id, timestamp = lastSeen)
	bm.setHostDescription(hostId = bt.client1.id, description = description)
	bm.setHostNotes(hostId = bt.client1.id, notes = notes)
	bm.setOpsiHostKey(hostId = bt.client1.id, opsiHostKey = opsiHostKey)
	bm.setMacAddress(hostId = bt.client1.id, mac = mac)
	
	host = bm.host_getObjects(id = bt.client1.id)[0]
	logger.comment(host.lastSeen)
	logger.comment(host.description)
	logger.comment(host.notes)
	logger.comment(host.opsiHostKey)
	logger.comment(host.hardwareAddress)
	
	assert lastSeen == host.lastSeen
	assert description == host.description
	assert notes == host.notes
	assert opsiHostKey == host.opsiHostKey
	assert mac == host.hardwareAddress
	
	res = bm.getOpsiHostKey(hostId = bt.client1.id)
	logger.comment(res)
	assert opsiHostKey == res
	
	res = bm.getMacAddress(hostId = bt.client1.id)
	logger.comment(res)
	assert mac == res
	
	host = bm.getHost_hash(hostId = bt.client1.id)
	logger.comment(host)
	
	serverIds = bm.getServerIds_list()
	logger.comment(serverIds)
	
	serverId = bm.getServerId(clientId = bt.client1.id)
	logger.comment(serverId)
	
	depotName = 'test-depot'
	depotRemoteUrl = 'smb://test-depot/xyz'
	depotId = bm.createDepot(depotName = depotName, domain = domain,
		depotLocalUrl = 'file:///xyz', depotRemoteUrl = depotRemoteUrl,
		repositoryLocalUrl = 'file:///abc', repositoryRemoteUrl = 'webdavs://test-depot:4447/products',
		network = '0.0.0.0/0', description = 'Some description', notes = 'Some notes', maxBandwidth = 100000)
	logger.comment(depotId)
	assert depotId == depotName + '.' + domain
	
	depotIds = bm.getDepotIds_list()
	logger.comment(depotIds)
	
	depot = bm.getDepot_hash(depotId)
	logger.comment(depot)
	assert depot['depotRemoteUrl'] == depotRemoteUrl
	
	bm.deleteDepot(depotId)
	depotIds = bm.getDepotIds_list()
	logger.comment(depotIds)
	assert not depotId in depotIds
	
	bm.lockProduct(productId = bt.product1.id, depotIds = [ bt.depotserver1.id ])
	productLocks = bm.getProductLocks_hash(depotIds = [])
	logger.comment(productLocks)
	for (prductId, depotIds) in productLocks.items():
		assert prductId == bt.product1.id
		assert len(depotIds) == 1
		assert depotIds[0] == bt.depotserver1.id 
	
	bm.unlockProduct(productId = bt.product1.id, depotIds = [])
	productLocks = bm.getProductLocks_hash(depotIds = [])
	logger.comment(productLocks)
	assert not productLocks
	
	productId1 = 'test-localboot-1'
	bm.createLocalBootProduct(productId = productId1, name = 'Some localboot product', productVersion = '1.0', packageVersion = '1', licenseRequired=0,
		   setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		   priority=0, description="", advice="", windowsSoftwareIds=[], depotIds=[])
	
	productId2 = 'test-netboot-1'
	bm.createNetBootProduct(productId = productId2, name = 'Some localboot product', productVersion = '1.0', packageVersion = '1', licenseRequired=0,
		   setupScript="", uninstallScript="", updateScript="", alwaysScript="", onceScript="",
		   priority=0, description="", advice="", pxeConfigTemplate = 'some_template', windowsSoftwareIds=[], depotIds=[])
	
	productIdents = bm.product_getIdents(returnType = 'tuple')
	logger.comment(productIdents)
	assert (productId1,'1.0','1') in productIdents
	assert (productId2,'1.0','1') in productIdents
	
	product = bm.getProduct_hash(productId = productId1, depotId = bt.depotserver1.id)
	logger.comment(product)
	
	products = bm.getProducts_hash()
	logger.comment(Tools.objectToBeautifiedText(products))
	
	products = bm.getProducts_listOfHashes()
	logger.comment(Tools.objectToBeautifiedText(products))
	
	products = bm.getProducts_listOfHashes(depotId = bt.depotserver1.id)
	logger.comment(Tools.objectToBeautifiedText(products))
	
	for client in bt.clients:
		productIds = bm.getInstalledProductIds_list(objectId = client.id)
		logger.comment(productIds)
		
		productIds = bm.getInstalledLocalBootProductIds_list(objectId = client.id)
		logger.comment(productIds)
		
		productIds = bm.getInstalledNetBootProductIds_list(objectId = client.id)
		logger.comment(productIds)
		
	productIds = bm.getProvidedLocalBootProductIds_list(depotId = bt.depotserver1.id)
	logger.comment(productIds)
	
	productIds = bm.getProvidedNetBootProductIds_list(depotId = bt.depotserver1.id)
	logger.comment(productIds)
	
	for client in bt.clients:
		status = bm.getProductInstallationStatus_hash(productId = bt.product1.id, objectId = client.id)
		logger.comment(status)
	
	bm.setProductState(productId = bt.product1.id, objectId = client.id, installationStatus = "not_installed", actionRequest = "setup")
	bm.setProductInstallationStatus(productId = bt.product1.id, objectId = client.id, installationStatus = "installed")
	bm.setProductActionProgress(productId = bt.product1.id, hostId = client.id, productActionProgress = "something 90%")
	bm.setProductActionRequest(productId = bt.product1.id, clientId = client.id, actionRequest = 'uninstall')
	
	for product in bt.products:
		actions = bm.getPossibleProductActions_list(productId = product.id)
		logger.comment(actions)
	
	actions = bm.getPossibleProductActions_hash()
	logger.comment(actions)
	
	depotId = bm.getDepotId(clientId = bt.client1.id)
	logger.comment(depotId)
	assert depotId == bt.depotserver1.id
	
	clientId = bm.getClientIdByMac(mac = bt.client2.hardwareAddress)
	logger.comment(bt.client2.id)
	assert clientId == bt.client2.id
	
	productIds = bm.getInstallableProductIds_list(clientId = bt.client1.id)
	logger.comment(productIds)
	
	productIds = bm.getInstallableLocalBootProductIds_list(clientId = bt.client1.id)
	logger.comment(productIds)
	
	productIds = bm.getInstallableNetBootProductIds_list(clientId = bt.client1.id)
	logger.comment(productIds)
	
	status = bm.getProductInstallationStatus_listOfHashes(objectId = bt.client1.id)
	logger.comment(status)
	
	actions = bm.getProductActionRequests_listOfHashes(clientId = bt.client1.id)
	logger.comment(actions)
	
	states = bm.getLocalBootProductStates_hash()
	logger.comment(Tools.objectToBeautifiedText(states))
	
testComposition()


if os.path.exists(TMP_CONFIG_DIR):
	shutil.rmtree(TMP_CONFIG_DIR)





















