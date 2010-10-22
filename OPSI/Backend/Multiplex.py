# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Multiplex   =
   = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009, 2010 uib GmbH
   
   http://www.uib.de/
   
   All rights reserved.
   
   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
   
   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.
   
   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>, Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

# Imports
import threading, socket, sys, time, functools, traceback
from twisted.conch.ssh import keys

if (sys.version_info < (2,6)):
	from sets import Set as set

# OPSI imports
from OPSI.Backend.Backend import *
from OPSI.Backend.JSONRPC import *
from OPSI.Util.Thread import *
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import *

logger = Logger()

# ======================================================================================================
# =                                   CLASS MULTIPLEXBACKEND                                           =
# ======================================================================================================
class MultiplexBackend(object):
	'''
	This backend acts as a dispatcher to multiplex commands received from one client
	onto multiple config servers. It relays all commands to all available servers, collects all results
	and maps the results transparently back to the client.
	'''
	
	__serviceCache = {}
	
	def __init__(self, username = '', password = '', address = '', *args, **kwargs):

		#self.__dict__['__services'] = self.__serviceCache

		# Default values
		self.__services = self.__serviceCache
		self.__possibleMethods = []
		self.__connectLock = threading.Lock()
		self.__socketTimeout = None
		self.__connectTimeout = 30
		self.__maxConcurrentCalls = 25
		self.__rpcQueuePollingTime = 0.01
		self.__timeBetweenCalls = 0.01
		self._defaultDomain = u'opsi.org'
		self._defaultServiceType = u"remote"
		self._ready = False
		self._buffer = {}
		self._context = self
		
		# Parse arguments
		for (option, value) in dict(kwargs).items():
			if   (option.lower() == 'sockettimeout') and not value is None:
				self.__socketTimeout = forceInt(value)
				del(kwargs[option])
			elif (option.lower() == 'connecttimeout') and not value is None:
				self.__connectTimeout = forceInt(value)
				del(kwargs[option])
			elif (option.lower() == 'defaultdomain'):
				self._defaultDomain = forceUnicode(value)
				del(kwargs[option])
			elif (option.lower() == 'context'):
				self._context = value
				del(kwargs[option])
				logger.info(u"Backend context was set to %s" % self._context)
				context = self._context
		
		logger.notice(u"Initializing services")
		if kwargs.has_key('services'):
			services = kwargs['services']
			for service in services:
				if service["url"] not in self.__services.keys():
					type = service.get("type", self._defaultServiceType)
					logger.debug(u"Initializing service %s as type %s" % (service["url"], type))
					
					s = getattr(sys.modules[__name__], "%sService" % type.lower().capitalize())
					self.__services[service['url']] = (
						s(	rpcQueuePollingTime = self.__rpcQueuePollingTime,
							socketTimeout       = self.__socketTimeout,
							connectTimeout      = self.__connectTimeout,
							multiplexBackend    = self,
							**service )
					)
				else:
					logger.notice(u"Using cached service for %s" % service['url'])
			del(kwargs['services'])
			
		for option in kwargs.keys():
			logger.warning(u"Unknown argument '%s' passed to MultiplexBackend constructor" % option)
		
		modules = self._context.backend_info()['modules']
		if not modules.get('customer'):
			raise Exception(u"Disabling multiplex backend: no customer in modules file")
		
		if not modules.get('valid'):
			raise Exception(u"Disabling multiplex backend: modules file invalid")
		
		if (modules.get('expires', '') != 'never') and (time.mktime(time.strptime(modules.get('expires', '2000-01-01'), "%Y-%m-%d")) - time.time() <= 0):
			raise Exception(u"Disabling multiplex backend: modules file expired")
		
		if not modules.get('multiplex'):
			raise Exception(u"Disabling mmultiplex backend: not in modules")
		
		logger.info(u"Verifying modules file signature")
		publicKey = keys.Key.fromString(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''
		mks = modules.keys()
		mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue
			val = modules[module]
			if (val == False): val = 'no'
			if (val == True):  val = 'yes'
			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ])):
			raise Exception(u"Disabling mmultiplex backend: modules file invalid")
		logger.notice(u"Modules file signature verified (customer: %s)" % modules.get('customer'))
		
		self._threadPool = getGlobalThreadPool(size = len(self.__services.keys()))
		self.connect()
	
	def _getDepotIds(self):
		depotIds = []
		for service in self.__services.keys():
			depotIds.append(service.split("/")[2].split(":")[0])
		return depotIds
	
	def _getOpsiHostKey(self, depotId):
		for name, service in self.__services.iterItems():
			if (name.split("/")[2].split(":")[0].lower() == depotId.lower()):
				return service.opsiHostKey
		raise BackendMissingDataError(u"Depot id '%s' not found in config" % depotId)
	
	def connect(self):
		if not self._ready:
			self.__connectLock.acquire()
			try:
				for service in self.__services.values():
					if not service.isConnected():
						logger.notice(u"Service not connected. Trying to connect: %s" % service)
						service.connect()
				while not self.isReady():
					time.sleep(0.01)
			finally:
				self.__connectLock.release()
		
	def isReady(self):
		ready = True
		for service in self.__services.values():
			serviceReady = ( service.isConnected() or service.error is not None )
			ready = ready and serviceReady
		return ready
	
	def __getattr__(self, name):
		interface = self.backend_getInterface()
		if name in map((lambda x: x['name']), interface):
			func = functools.partial(self.dispatch, name)
			setattr(self, name, func)
			return func
		raise AttributeError(u"No service implements method %s." %name)
	
	def _getDispatcher(self, *args, **kwargs):
		def getDispatcherFromFilter(*args, **kwargs):
			dispatcher = set()
			args = list(args)
			args.extend(kwargs.values())
			for arg in args:
				if isinstance(arg, BaseObject):
					dispatcher.update(getDispatcherFromFilter(*arg.getIdent(returnType = 'list')))
				elif isinstance(arg, list):
					dispatcher.update(getDispatcherFromFilter(*arg))
				elif isinstance(arg, dict):
					dispatcher.update(getDispatcherFromFilter(**arg))
				else:
					for service in self.__services.values():
						if arg in map((lambda x: x.id), service.clients) \
						or arg in map((lambda x: x.id), service.depots):
							dispatcher.add(service)
			return dispatcher
		
		dispatcher = getDispatcherFromFilter(*args, **kwargs)
		if not len(dispatcher):
			dispatcher = self.__services.values()
			
		logger.debug2(u"Got dispatcher %s for args %s and kwargs %s." %(dispatcher, args, kwargs))
		return dispatcher
	
	#def dispatch_threaded(self, methodName, *args, **kwargs):
	#	logger.debug2(u"Dispatching %s with args %s and kwargs %s" % (methodName, args, kwargs))
	#	results = []
	#	calls = 0
	#	def pushResult(success, result, error):
	#		if not success or not result:
	#			results.append((success, result, error))
	#		else:
	#			jsonrpc = result
	#			(success, result, error) = (None, None, None)
	#			try:
	#				result = jsonrpc.waitForResult()
	#				success = True
	#			except Exception, e:
	#				error = e
	#				success = False
	#			results.append((success, result, error))
	#	
	#	dispatcher = self._getDispatcher(*args, **kwargs)
	#	logger.notice(u"Dispatching %s to %d services" % (methodName, len(dispatcher)))
	#	for service in dispatcher:
	#		if service.isConnected():
	#			logger.debug(u"Calling method %s of service %s" %(methodName, service.url))
	#			self._threadPool.addJob(getattr(service, methodName), pushResult, *args, **kwargs)
	#			calls +=1
	#	while len(results) != calls:
	#		time.sleep(0.1)
	#	
	#	r = None
	#	errors = []
	#	for (success, result, error) in results:
	#		if success:
	#			if   type(r) is list:
	#				r.extend(forceList(result))
	#			elif type(r) is dict:
	#				r.update(forceDict(result))
	#			elif type(r) in (str, unicode):
	#				r = forceUnicode(r) + forceUnicode(result)
	#			elif not r:
	#				r = result
	#		else:
	#			errors.append(error)
	#	if errors and methodName not in ('exit', 'backend_exit'):
	#		#logger.error(u"Error during dispatch: %s (Result: %s)" % (error, result))
	#		raise BackendError(u"Error during dispatch: %s" % (u', '.join(forceUnicodeList(errors))))
	#	return r
	
	def dispatch(self, methodName, *args, **kwargs):
		logger.debug2(u"Dispatching %s with args %s and kwargs %s" % (methodName, args, kwargs))
		results = []
		calls = 0
		def pushResult(jsonrpc, results):
			results.append((not jsonrpc.error, jsonrpc.result, jsonrpc.error))
		
		dispatcher = self._getDispatcher(*args, **kwargs)
		logger.notice(u"Dispatching %s to %d services" % (methodName, len(dispatcher)))
		for service in dispatcher:
			if service.isConnected():
				logger.debug(u"Calling method %s of service %s" % (methodName, service.url))
				meth = getattr(service, methodName)
				res = meth(*args, **kwargs)
				if isinstance(res, DeferredCall):
					res.setCallback(pushResult, results)
				else:
					results.append((True, res, None))
				calls +=1
				# Wait a little bit to avoid that all calls will start at once
				time.sleep(self.__timeBetweenCalls)
			if self.__maxConcurrentCalls:
				while (calls - len(results) >= self.__maxConcurrentCalls):
					time.sleep(0.05)
		logTime = 0
		while len(results) != calls:
			if (logTime >= 1):
				logTime = 0
				logger.info(u'Waiting for results, got (%d/%d)' % (len(results), calls))
			time.sleep(0.05)
			logTime += 0.05
		
		r = None
		errors = []
		for (success, result, error) in results:
			if success:
				if   type(r) is list:
					r.extend(forceList(result))
				elif type(r) is dict:
					r.update(forceDict(result))
				elif type(r) in (str, unicode):
					r = forceUnicode(r) + forceUnicode(result)
				elif not r:
					r = result
			else:
				errors.append(error)
		logger.debug(u"Dispatching %s done" % methodName)
		if errors and methodName not in ('exit', 'backend_exit'):
			#logger.error(u"Error during dispatch: %s (Result: %s)" % (error, result))
			raise BackendError(u"Error during dispatch: %s" % (u', '.join(forceUnicodeList(errors))))
		return r
	
	def backend_exit(self):
		logger.info(u"Shutting down multiplex backend")
		self.dispatch('backend_exit')
		logger.info(u"Freeing thread pool")
		self._threadPool.free()
	
	def auditHardware_getConfig(self, language=None):
		for service in self.__services.values():
			if service.isMasterService:
				deferredCall = service.auditHardware_getConfig(language)
				return deferredCall.waitForResult()
	
	def backend_getInterface(self):
		if len(self.__services.values()):
			for service in self.__services.values():
				if service.isConnected():
					if service.isMasterService:
						return service.backend_getInterface()
			if self.__services.values()[0].isConnected():
				return self.__services.values()[0].backend_getInterface()
		raise AttributeError(u"Could not determine the interface of any service.")
	
	def configState_insertObject(self, configState):
		self._configState_insertOrupdateObject(configState, isUpdate = False)
		
	def configState_updateObject(self, configState):
		self._configState_insertOrupdateObject(configState, isUpdate = True)
	
	def _configState_insertOrupdateObject(self, configState, isUpdate=False):
		if (configState.configId == u"clientconfig.depot.id"):
			for service in self.__services.values():
				dispatcher = self._getDispatcher(configState.values).pop()
				if "OpsiClient.%s" % configState.objectId in self._buffer:
					logger.notice(u"Creating client %s from buffer on depot %s" % (configState.objectId,dispatcher.url ))
					dispatcher.host_insertObject(self._buffer["OpsiClient.%s" % configState.objectId])
					del(self._buffer["OpsiClient.%s" % configState.objectId])
					dispatcher.configState_updateObjects(configState)
					dispatcher.refresh()
				
				elif (service.url == dispatcher.url):
					dispatcher.configState_updateObjects(configState)
				
				elif configState.objectId in map((lambda x: x.id),service.clients):
					
					source = service
					
					self.__connectLock.acquire()
					try:
						logger.notice(u"Moving client from %s to %s" %(source.url, dispatcher.url))
						
						clients = source.host_getObjects(type = 'OpsiClient', id = configState.objectId)
						dispatcher.host_insertObject(clients[0])
						
						otgs = source.objectToGroup_getObjects(groupType = 'HostGroup', objectId = configState.objectId)
						groups = source.group_getObjects(id = [otg.groupId for otg in otgs])
						if otgs:
							dispatcher.objectToGroup_createObjects(otgs)
						
						pocs = source.productOnClient_getObjects(clientId = configState.objectId)
						if pocs:
							dispatcher.productOnClient_createObjects(poc)
						
						pps = source.productPropertyState_getObjects(objectId = configState.objectId)
						if pps:
							dispatcher.productPropertyState_createObjects(pps)
						
						css = []
						for cs in source.configState_getObjects(objectId = configState.objectId):
							if (cs.configId == u"clientconfig.depot.id"):
								continue
							css.append(cs)
						if css:
							dispatcher.configState_createObjects(css)
						
						asoc = source.auditSoftwareOnClient_getObjects(clientId = configState.objectId)
						if asoc:
							try:
								dispatcher.auditSoftwareOnClient_createObjects(asoc)
							except Exception, e:
								logger.error(u"Failed do create auditSoftwareOnClients: %s" % e)
						
						ahoc = source.auditHardwareOnHost_getObjects(clientId = configState.objectId)
						if ahoc:
							dispatcher.auditHardwareOnHost_createObjects(ahoc)
						
						softwareLicenses = source.softwareLicense_getObjects(boundToHost = configState.objectId)
						if softwareLicenses:
							for license in softwareLicenses:
								license.setBoundToHost(None)
							source.softwareLicense_updateObjects(softwareLicenses)
						
						dispatcher.configState_updateObject(configState)
						
						dispatcher.refresh()
						try:
							if configState.objectId in map((lambda x:x.id), dispatcher.clients):
								logger.notice(u"Client successfully moved to %s" % dispatcher.url)
								source.host_deleteObjects(clients[0])
								if pocs:
									source.productOnClient_deleteObjects(pocs)
								if asoc:
									source.auditSoftwareOnClient_deleteObjects(asoc)
								if ahoc:
									source.auditHardwareOnHost_deleteObjects(ahoc)
								source.licenseOnClient_deleteObjects(source.licenseOnClient_getObjects(clientId = configState.objectId))
								if softwareLicenses:
									source.softwareLicense_deleteObjects(softwareLicenses)
								source.refresh()
							else:
								raise Exception(u"Client was not found on destination server %s." % dispatcher.url)
						except Exception,e:
							logger.error(e)
					finally:
						self.__connectLock.release()
		else:
			if isUpdate:
				return self.dispatch("configState_updateObject", configState)
			else:
				return self.dispatch("configState_insertObject", configState)
	
	def licenseOnClient_getObjects(self, attributes=[], **filter):
		if "licensePoolId" in filter.keys() and "clientId" in filter.keys() \
		    and filter["licensePoolId"] != [] and filter["clientId"] != []:
			dispatcher = set()
			for service in self.__services.values():
				for licensePoolId in filter["licensePoolId"]:
					for clientId in filter["clientId"]:
						if filter["licensePoolId"] in map((lambda x:x.id),service.licensePools) \
						   and filter["clientId"] in map((lambda x:x.id),service.clients):
							dispatcher.add(service)
			if not len(dispatcher):
				raise Exception(u"LicensePools %s and Clients %s are not on the same depots." % (filter["licensePoolId"], filter["clientId"]))
			result = []
			for service in dispatcher:
				result.extend(service.licenseOnClient_getObjects(attributes, **filter))
			return result
		return self.dispatch("licenseOnClient_getObjects", attributes, **filter)
	
	def configState_getObjects(self, attributes=[], **filter):
		configStates = self.dispatch("configState_getObjects", attributes, **filter)
		return configStates
	
	def configState_updateObjects(self, configs):
		for config in forceObjectClassList(configs, Config):
			dispatcher = self._getDispatcher(config.values)
			for d in dispatcher:
				if "OpsiClient.%s" % config.objectId in self._buffer:
					dispatcher.host_createObject(self._buffer["OpsiClient.%s" % config.objectId])
					del(self._buffer["OpsiClient.%s" % config.objectId])
				self.dispatch("configState_updateObjects", configs)
	
	def host_insertObject(self, host):
		modules = self._context.backend_info()['modules']
		publicKey = keys.Key.fromString(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''; mks = modules.keys(); mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue
			val = modules[module]
			if (val == False): val = 'no'
			if (val == True):  val = 'yes'
			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ])):
			raise Exception(u"Failed to verify modules signature")
		if isinstance(host, OpsiClient):
			self._buffer["OpsiClient.%s" % host.id] = host
		else:
			self.dispatch("host_insertObject", host)
	
	def licensePool_insertObject(self, licensePool):
		if len(self.__services.values()):
			for service in self.__services.values():
				if licensePool.id in map((lambda x: x.id), service.licensePools):
					return service.licensePool_updateObject(licensePool)
		raise NotImplementedError(u"Multiplex backend does not support the creation of license pools.")
	
	def licensePool_create(self, *args, **kwargs):
		raise NotImplementedError(u"Multiplex backend does not support the creation of license pools.")
	
	def licensePool_createObjects(self, *args, **kwargs):
		raise NotImplementedError(u"Multiplex backend does not support the creation of license pools.")
	
	def licensePool_updateObject(self,licensePool):
		if len(self.__services.values()):
			for service in self.__services.values():
				if licensePool.id in map((lambda x: x.id), service.licensePools):
					result = service.licensePool_updateObject(licensePool)
					service.refresh()
					return result
	
	def softwareLicense_insertObject(self, softwareLicense):
		softwareLicense.setDefaults()
		self._buffer["SoftwareLicense.%s" % softwareLicense.id] = softwareLicense
	
	def softwareLicenseToLicensePool_insertObject(self, softwareLicenseToLicensePool):
		for service in self.__services.values():
			if softwareLicenseToLicensePool.licensePoolId in map((lambda x: x.id), service.licensePools):
				if "SoftwareLicense.%s" % softwareLicenseToLicensePool.softwareLicenseId in self._buffer:
					service.softwareLicense_insertObject(self._buffer["SoftwareLicense.%s" % softwareLicenseToLicensePool.softwareLicenseId])
					del(self._buffer["SoftwareLicense.%s" % softwareLicenseToLicensePool.softwareLicenseId])
				return service.softwareLicenseToLicensePool_insertObject(softwareLicenseToLicensePool)
		return self.dispatch("softwareLicenseToLicensePool_insertObject",softwareLicenseToLicensePool )
	
	def softwareLicenseToLicensePool_getObjects(self, attributes=[], **filter):
		if "licensePoolId" in filter.keys():
			licensePoolId = filter["licensePoolId"]
			for service in self.__services.values():
				if licensePoolId in map((lambda x: x.id), service.licensePools):
					return service.softwareLicenseToLicensePool_getObjects(attributes, **filter)
		return self.dispatch("softwareLicenseToLicensePool_getObjects", attributes, **filter)
					
			
	def host_renameOpsiDepotserver(self, id, newId):
		raise NotImplementedError(u"Multiplex backend does not support renaming of depot servers.")
	
	def softwareLicense_getObjects(self, attributes=[], **filter):
		if "id" in filter.keys() and "SoftwareLicense.%s" % filter["id"] in self._buffer:
			result = self._buffer["SoftwareLicense.%s" % filter["id"]]
			return [result]
		return self.dispatch("softwareLicense_getObjects", attributes, **filter)
	
class Service(object):
	def __init__(self, master=False):
		self.clients = []
		self.depots = []
		self.licensePools = []
		
		self.isMaster = master
		self._connected = False
		self.error = None
	
	def isMasterService(self):
		return self.isMaster
	
	def isConnected(self):
		return self._connected
	
	def connect(self):
		pass

class RemoteService(Service, JSONRPCBackend):
	def __init__(self, url, domain, opsiHostKey, rpcQueuePollingTime, socketTimeout, connectTimeout, multiplexBackend, **kwargs):
		self.url = url
		self.domain = domain
		self.opsiHostKey = opsiHostKey
		self.socketTimeout = socketTimeout
		self.connectTimeout = connectTimeout
		self.multiplexBackend = multiplexBackend
		Service.__init__(self, **kwargs)
		JSONRPCBackend.__init__(
			self,
			address             = url,
			connectOnInit       = False,
			connectTimeout      = self.connectTimeout,
			socketTimeout       = self.socketTimeout,
			username            = self.url.split('/')[2].split(':')[0],
			password            = self.opsiHostKey,
			application         = u'opsi multiplex backend %s' % __version__,
			deflate             = True,
			rpcQueuePollingTime = rpcQueuePollingTime,
			**kwargs
		)
		self.error = None
	
	def connect(self):
		def _connect(service):
			JSONRPCBackend.connect(service)
			service.refresh()
		logger.debug(u"Connecting to service %s" %self.url )
		
		self.multiplexBackend._threadPool.addJob(function = _connect, callback = self._onConnect, service = self)
	
	def _onConnect(self, success, result, error):
		if success:
			self.error = None
			logger.notice(u"Successfully connected to service %s (Thread: %s)" % (self.url, threading.currentThread()))
			self.setAsync(True)
		else:
			self.error = error
			logger.error(u"Failed to connect to service %s: %s (Thread: %s)" % (self.url, error, threading.currentThread()))
	
	def refresh(self):
		self.setAsync(True)
		self.clients = []
		self.depots = []
		jsonrpc1 = self.host_getObjects(attributes = ['id'])
		jsonrpc2 = self.licensePool_getObjects()
		for host in jsonrpc1.waitForResult():
			if   host.getType() in ('OpsiConfigserver', 'OpsiDepotserver'):
				self.depots.append(host)
			elif host.getType() in ('OpsiClient'):
				self.clients.append(host)
		self.licensePools = jsonrpc2.waitForResult()
		
	def licensePool_getObjects(self, attributes=[], **filter):
		self.licensePools = self._jsonRPC("licensePool_getObjects", [attributes, filter])
		return self.licensePools
	
	def __unicode__(self):
		return u"<RemoteService %s >" % self.url
	
	def __str__(self):
		return self.__unicode__().encode("ascii", "replace")
	
	def __repr__(self):
		return self.__str__()
	
	#def __del__(self):
	#	try:
	#		if self.isConnected():
	#			self.disconnect()
	#	finally:
	#		try:
	#			JSONRPCBackend.__del__(self)
	#		except:
	#			pass
	
	
