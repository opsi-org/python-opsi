#!/usr/bin/python

from OPSI.Logger import *
from OPSI.Backend.LDAP import *
from OPSI.Backend.Backend import ExtendedConfigDataBackend
from OPSI.Types import *
from OPSI.Object import *

logger = Logger()
logger.setConsoleLevel(LOG_NOTICE)
logger.setConsoleColor(True)

address    = u'localhost'
baseDn     = u'dc=uib,dc=local'
opsiBaseDn = u'cn=opsi,dc=uib,dc=local'
username   = u'cn=admin,dc=uib,dc=local'
password   = u'linux123'

backend = ExtendedConfigDataBackend(LDAPBackend(address = address, username = username, password = password))

ldap = LDAPSession(address = address, username = username, password = password)
ldap.connect()

for container in ('configs', 'configStates', 'objectToGroups', 'productOnClients', 'productOnDepots', 'productPropertyStates'):
	ldapObj = LDAPObject(u"cn=%s,%s" % (container, opsiBaseDn))
	if ldapObj.exists(ldap):
		logger.notice(u"Deleting container: %s" % ldapObj.getDn())
		ldapObj.deleteFromDirectory(ldap, recursive = True)

backend.backend_createBase()

logger.notice(u"Converting opsiHost")
search = LDAPObjectSearch(ldap, baseDn, filter = u'(objectClass=opsiConfigserver)')
for obj in search.getObjects():
	logger.info(u"Found config server: %s" % obj.getDn())
	try:
		obj.readFromDirectory(ldap)
		hostId = forceHostId(obj.getCn())
		obj.removeObjectClass('opsiHost')
		obj.removeObjectClass('opsiDepotserver')
		obj.removeObjectClass('opsiConfigserver')
		obj.addObjectClass('OpsiHost')
		obj.addObjectClass('OpsiDepotserver')
		obj.addObjectClass('OpsiConfigserver')
		obj.writeToDirectory(ldap)
	except Exception, e:
		obj.deleteFromDirectory(ldap)
		logger.error(e)

search = LDAPObjectSearch(ldap, baseDn, filter = u'(objectClass=opsiDepotserver)')
for obj in search.getObjects():
	logger.info(u"Found depot server: %s" % obj.getDn())
	try:
		obj.readFromDirectory(ldap)
		hostId = forceHostId(obj.getCn())
		obj.removeObjectClass('opsiHost')
		obj.removeObjectClass('opsiDepotserver')
		obj.addObjectClass('OpsiHost')
		obj.addObjectClass('OpsiDepotserver')
		obj.writeToDirectory(ldap)
	except Exception, e:
		obj.deleteFromDirectory(ldap)
		logger.error(e)

search = LDAPObjectSearch(ldap, baseDn, filter = u'(objectClass=opsiClient)')
for obj in search.getObjects():
	logger.info(u"Found client: %s" % obj.getDn())
	try:
		obj.readFromDirectory(ldap)
		hostId = forceHostId(obj.getCn())
		obj.removeObjectClass('opsiHost')
		obj.removeObjectClass('opsiClient')
		obj.addObjectClass('OpsiHost')
		obj.addObjectClass('OpsiClient')
		obj.writeToDirectory(ldap)
	except Exception, e:
		obj.deleteFromDirectory(ldap)
		logger.error(e)
	
serverIds = backend.host_getIdents(returnType = 'unicode', type = u'OpsiConfigserver')
depotIds  = backend.host_getIdents(returnType = 'unicode', type = u'OpsiDepotserver')
clientIds = backend.host_getIdents(returnType = 'unicode', type = u'OpsiClient')

logger.notice(u"Converting opsiGeneralConfig")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiGeneralConfig)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found general config: %s" % obj.getDn())
		hostId = forceHostId(obj.getCn())
		for opsiKeyValuePair in obj.getAttribute('opsiKeyValuePair', default = [], valuesAsList = True):
			try:
				logger.info(u"Converting general config: %s" % opsiKeyValuePair)
				(configId, value) = opsiKeyValuePair.split(u'=', 1)
				if   hostId in serverIds:
					backend.config_createObjects( UnicodeConfig(id = configId, defaultValues = [ value ]) )
				elif hostId in clientIds:
					backend.config_createObjects( UnicodeConfig(id = configId) )
					backend.configState_createObjects( ConfigState(configId = configId, objectId = hostId, values = [ value ] ) )
			except Exception, e:
				logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))

logger.notice(u"Converting opsiNetworkConfig")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiNetworkConfig)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found network config: %s" % obj.getDn())
		hostId = forceHostId(obj.getCn())
		for (key, value) in obj.getAttributeDict(valuesAsList = False).items():
			try:
				if not value:
					continue
				configId = None
				if   (key == 'opsiDepotserverReference'):
					configId = u'clientconfig.depot.id'
					value = forceHostId(value.split(',')[0].split('=')[1])
				elif (key == 'opsiDepotDrive'):
					configId = u'clientconfig.depot.drive'
				elif (key == 'opsiNextBootServiceURL'):
					configId = u'clientconfig.configserver.url'
				elif (key == 'opsiWinDomain'):
					logger.error(u"TODO: winDomain")
				
				if not configId:
					continue
				
				logger.info(u"Converting network config %s" % key)
				
				if   hostId in serverIds:
					backend.config_createObjects( UnicodeConfig(id = configId, defaultValues = [ value ]) )
				elif hostId in clientIds:
					backend.config_createObjects( UnicodeConfig(id = configId) )
					backend.configState_createObjects( ConfigState(configId = configId, objectId = hostId, values = [ value ] ) )
			except Exception, e:
				logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))
		
logger.notice(u"Converting opsiGroup")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiGroup)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found opsi group: %s" % obj.getDn())
		groupId = forceGroupId(obj.getCn())
		obj.deleteFromDirectory(ldap, recursive = True)
		backend.group_createObjects( HostGroup(id = groupId) )
		objectToGroups = []
		for value in obj.getAttribute('uniqueMember', default = [], valuesAsList = True):
			try:
				objectId = forceHostId(value.split(',')[0].split('=')[1])
				objectToGroups.append( ObjectToGroup(groupId = groupId, objectId = objectId) )
			except Exception, e:
				logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))
		backend.objectToGroup_createObjects(objectToGroups)
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))


localbootProductIds = []
netbootProductIds = []
deleteDns = []
for objectClass in ('opsiLocalBootProduct', 'opsiNetBootProduct'):
	logger.notice(u"Converting %s" % objectClass)
	search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=%s)' % objectClass)
	for obj in search.getObjects():
		try:
			obj.readFromDirectory(ldap)
			logger.info(u"Found product: %s" % obj.getDn())
			
			depotId = forceHostId( obj.getDn().split(',')[1].split('=')[1] )
			containerDn = ','.join(obj.getDn().split(',')[1:])
			if not containerDn in deleteDns:
				deleteDns.append(containerDn)
			
			Class = LocalbootProduct
			if (objectClass == 'opsiNetBootProduct'):
				Class = NetbootProduct
			
			product = Class(
				id                 = obj.getCn(),
				productVersion     = obj.getAttribute('opsiProductVersion',         default = None, valuesAsList = False),
				packageVersion     = obj.getAttribute('opsiPackageVersion',         default = None, valuesAsList = False),
				name               = obj.getAttribute('opsiProductName',            default = None, valuesAsList = False),
				licenseRequired    = obj.getAttribute('opsiProductLicenseRequired', default = None, valuesAsList = False),
				setupScript        = obj.getAttribute('opsiSetupScript',            default = None, valuesAsList = False),
				uninstallScript    = obj.getAttribute('opsiUninstallScript',        default = None, valuesAsList = False),
				updateScript       = obj.getAttribute('opsiUpdateScript',           default = None, valuesAsList = False),
				alwaysScript       = obj.getAttribute('opsiAlwaysScript',           default = None, valuesAsList = False),
				onceScript         = obj.getAttribute('opsiOnceScript',             default = None, valuesAsList = False),
				priority           = obj.getAttribute('opsiProductPriority',        default = None, valuesAsList = False),
				description        = obj.getAttribute('description',                default = None, valuesAsList = False),
				advice             = obj.getAttribute('opsiProductAdvice',          default = None, valuesAsList = False),
				productClassNames  = obj.getAttribute('opsiProductClassProvided',   default = None, valuesAsList = True),
				windowsSoftwareIds = obj.getAttribute('opsiWindowsSoftwareId',      default = None, valuesAsList = True)
			)
			if (objectClass == 'opsiNetBootProduct'):
				if not product.id in netbootProductIds:
					netbootProductIds.append(product.id)
				product.setPxeConfigTemplate( obj.getAttribute('opsiPxeConfigTemplate', default = None, valuesAsList = False) )
			else:
				if not product.id in localbootProductIds:
					localbootProductIds.append(product.id)
			
			backend.product_createObjects(product)
			
			backend.productOnDepot_createObjects(
				ProductOnDepot(
					productId      = product.getId(),
					productType    = product.getType(),
					productVersion = product.getProductVersion(),
					packageVersion = product.getPackageVersion(),
					depotId        = depotId,
					locked         = obj.getAttribute('opsiProductIsLocked', default = False, valuesAsList = False)
				)
			)
		except Exception, e:
			logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))


logger.notice(u"Converting opsiProductPropertyDefinition")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiProductPropertyDefinition)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found product property: %s" % obj.getDn())
		#obj.deleteFromDirectory(ldap, recursive = True)
		
		
		productId = forceProductId( obj.getDn().split(',')[2].split('=')[1] )
		depotId   = forceHostId( obj.getDn().split(',')[3].split('=')[1] )
		
		productOnDepot = backend.productOnDepot_getObjects(productId = productId, depotId = depotId)
		if not productOnDepot:
			raise Exception(u"Product '%s' not found on depot '%s'" % (productId, depotId))
		productOnDepot = productOnDepot[0]
		
		defaultValues = obj.getAttribute('opsiProductPropertyDefaultValue',  default = None, valuesAsList = True)
		backend.productProperty_createObjects(
			UnicodeProductProperty(
				productId       = productOnDepot.productId,
				productVersion  = productOnDepot.productVersion,
				packageVersion  = productOnDepot.packageVersion,
				propertyId      = obj.getCn(),
				description     = obj.getAttribute('description',                      default = None, valuesAsList = False),
				possibleValues  = obj.getAttribute('opsiProductPropertyPossibleValue', default = None, valuesAsList = True),
				defaultValues   = defaultValues
			)
		)
		if defaultValues:
			backend.productPropertyState_createObjects(
				ProductPropertyState(
					productId   = productOnDepot.productId,
					propertyId  = obj.getCn(),
					objectId    = depotId,
					values      = defaultValues
				)
			)
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))

logger.notice(u"Converting opsiProductDependency")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiProductDependency)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found product dependency: %s" % obj.getDn())
		
		action    = forceActionRequest( obj.getDn().split(',')[1].split('=')[1] )
		productId = forceProductId( obj.getDn().split(',')[3].split('=')[1] )
		depotId   = forceHostId( obj.getDn().split(',')[4].split('=')[1] )
		
		productOnDepot = backend.productOnDepot_getObjects(productId = productId, depotId = depotId)
		if not productOnDepot:
			raise Exception(u"Product '%s' not found on depot '%s'" % (productId, depotId))
		productOnDepot = productOnDepot[0]
		
		backend.productDependency_createObjects(
			ProductDependency(
				productId                  = productOnDepot.productId,
				productVersion             = productOnDepot.productVersion,
				packageVersion             = productOnDepot.packageVersion,
				productAction              = action,
				requiredProductId          = obj.getAttribute('opsiRequiredProductId',          default = None, valuesAsList = False),
				requiredAction             = obj.getAttribute('opsiActionRequired',             default = None, valuesAsList = False),
				requiredInstallationStatus = obj.getAttribute('opsiInstallationStatusRequired', default = None, valuesAsList = False),
				requirementType            = obj.getAttribute('opsiRequirementType',            default = None, valuesAsList = False)
			)
		)
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))


for deleteDn in deleteDns:
	try:
		logger.notice(u"Deleting %s" % deleteDn)
		LDAPObject(deleteDn).deleteFromDirectory(ldap, recursive = True)
	except Exception, e:
		logger.error(e)



logger.notice(u"Converting opsiProductState")
search = LDAPObjectSearch(ldap, opsiBaseDn, filter = u'(objectClass=opsiProductState)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found product state: %s" % obj.getDn())
		
		productType = 'LocalbootProduct'
		if obj.getCn() in netbootProductIds:
			productType = 'NetbootProduct'
		
		installationStatus = None
		try:
			installationStatus = forceInstallationStatus(obj.getAttribute('opsiProductInstallationStatus', default = None, valuesAsList = False))
		except:
			pass
		actionRequest = None
		try:
			actionRequest = forceActionRequest(obj.getAttribute('opsiProductActionRequestForced', default = None, valuesAsList = False))
		except:
			pass
		
		if (installationStatus == 'not_installed') and (actionRequest == 'none'):
			continue
		
		clientId = forceHostId( obj.getDn().split(',')[1].split('=')[1] )
		if not clientId in clientIds:
			continue
		
		backend.productOnClient_insertObject(
			ProductOnClient(
				productId          = obj.getCn(),
				productType        = productType,
				productVersion     = obj.getAttribute('opsiProductVersion', default = None, valuesAsList = False),
				packageVersion     = obj.getAttribute('opsiPackageVersion', default = None, valuesAsList = False),
				clientId           = clientId,
				installationStatus = installationStatus,
				actionRequest      = actionRequest,
				actionProgress     = obj.getAttribute('opsiProductActionProgress', default = None, valuesAsList = False)
			)
		)
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))


logger.notice(u"Converting opsiProductProperty")
search = LDAPObjectSearch(ldap, u'cn=productProperties,%s' % opsiBaseDn, filter = u'(objectClass=opsiProductProperty)')
for obj in search.getObjects():
	try:
		obj.readFromDirectory(ldap)
		logger.info(u"Found product property: %s" % obj.getDn())
		
		clientId = forceHostId( obj.getDn().split(',')[1].split('=')[1] )
		if not clientId in clientIds:
			continue
		
		productId = obj.getAttribute('opsiProductReference', valuesAsList = False).split(',')[0].split('=')[1]
		
		productPropertyStates = []
		for opsiKeyValuePair in obj.getAttribute('opsiKeyValuePair', default = [], valuesAsList = True):
			try:
				logger.info(u"Converting product property: %s" % opsiKeyValuePair)
				(propertyId, value) = opsiKeyValuePair.split(u'=', 1)
				if (value == ''):
					continue
				productPropertyStates.append(
					ProductPropertyState(
						productId   = productId,
						propertyId  = propertyId,
						objectId    = clientId,
						values      = [ value ]
					)
				)
			except Exception, e:
				logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))
		backend.productPropertyState_createObjects(productPropertyStates)
	except Exception, e:
		logger.error(u"Failure while processing %s: %s" % (obj.getDn(), e))


for container in ('generalConfigs', 'networkConfigs', 'productClasses', 'productLicenses', 'productProperties', 'productStates'):
	ldapObj = LDAPObject(u"cn=%s,%s" % (container, opsiBaseDn))
	if ldapObj.exists(ldap):
		logger.notice(u"Deleting container: %s" % ldapObj.getDn())
		ldapObj.deleteFromDirectory(ldap, recursive = True)



	
	
	
	
	
