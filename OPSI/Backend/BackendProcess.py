#!/usr/bin/python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2010-2016 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Backend processes.

These are mainly used when running any kind of opsi server.

:copyright: uib GmbH <info@uib.de>
:author: Christian Kampka <c.kampka@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
import os
import time
import base64
import functools
from hashlib import md5

from twisted.application.service import Service
from twisted.internet.protocol import Protocol
from twisted.internet import reactor, defer
from twisted.conch.ssh import keys

from OPSI.Backend.BackendManager import BackendManager, backendManagerFactory
from OPSI.Service.Process import OpsiPyDaemon
from OPSI.Util.Configuration import BaseConfiguration
from OPSI.Util.AMP import OpsiProcessProtocolFactory, OpsiProcessConnector
from OPSI.Util.Twisted import ResetableLoop
from OPSI.Service.JsonRpc import JsonRpcRequestProcessor
from OPSI.Logger import LOG_WARNING, Logger

__all__ = [
	'BackendProcessConfiguration', 'BackendDataExchangeProtocol',
	'OpsiBackendService', 'OpsiBackendProcessConnector',
	'OpsiBackendProcess'
]

logger = Logger()


class BackendProcessConfiguration(BaseConfiguration):

	def _makeParser(self):
		parser = BaseConfiguration._makeParser(self)

		parser.add_option("--socket", dest="socket")
		parser.add_option("--logFile", dest="logFile")
		return parser


class BackendDataExchangeProtocol(Protocol):

	def dataReceived(self, data):
		pass

	def write(self, data):
		self.transport.write(data)


class OpsiBackendService(Service):

	def __init__(self, config):
		self._config = config

		self._backendManager = None
		self._socket = None
		self._lastContact = time.time()
		self._check = ResetableLoop(self.checkConnected)

	def checkConnected(self):
		if (time.time() - self._lastContact) > 300:
			reactor.stop()

	def setLogging(self, console=LOG_WARNING, file=LOG_WARNING):
		logger.setConsoleLevel(console)
		logger.setFileLevel(file)
		logger.startTwistedLogging()
		logger.logWarnings()

	def startService(self):
		logger.info(u"Starting opsi backend Service")
		logger.setLogFile(self._config.logFile)

		if not os.path.exists(os.path.dirname(self._config.socket)):
			os.makedirs(os.path.dirname(self._config.socket))

		self.factory = OpsiProcessProtocolFactory(self, "%s.dataport" % self._config.socket)
		logger.debug(u"Opening socket %s for interprocess communication." % self._config.socket)
		try:
			self._socket = reactor.listenUNIX(self._config.socket, self.factory)
		except Exception as e:
			logger.error("Could not connect to socket %s from worker." % self._config.socket)
		self._check.start(10)


	def initialize(self, user, password, forceGroups, dispatchConfigFile,
			backendConfigDir, extensionConfigDir, aclFile, depotId, postpath,
			startReactor):

		self.user = user
		self.password = password
		self.forceGroups = forceGroups
		self.dispatchConfigFile = dispatchConfigFile
		self.backendConfigDir = backendConfigDir
		self.extensionConfigDir = extensionConfigDir
		self.aclFile = aclFile
		self.depotId = depotId
		self.postpath = postpath
		self.startReactor = startReactor

		self._backend = BackendManager(
			dispatchConfigFile=dispatchConfigFile,
			backendConfigDir=backendConfigDir,
			extensionConfigDir=extensionConfigDir,
			depotBackend=bool(depotId)
		)

		backendinfo = self._backend.backend_info()
		modules = backendinfo['modules']
		helpermodules = backendinfo['realmodules']
		publicKey = keys.Key.fromString(data = base64.decodestring('AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDojY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDUlk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP')).keyObject
		data = u''; mks = modules.keys(); mks.sort()
		for module in mks:
			if module in ('valid', 'signature'):
				continue
			if helpermodules.has_key(module):
				val = helpermodules[module]
				if int(val) > 0:
					modules[module] = True
			else:
				val = modules[module]
				if (val == False): val = 'no'
				if (val == True):  val = 'yes'

			data += u'%s = %s\r\n' % (module.lower().strip(), val)
		if not bool(publicKey.verify(md5(data).digest(), [ long(modules['signature']) ])) or \
			not modules.get('high_availability'):
			raise Exception(u"Failed to verify modules signature")


		self._backendManager = backendManagerFactory(
			user               = user,
			password           = password,
			forceGroups        = forceGroups,
			dispatchConfigFile = dispatchConfigFile,
			backendConfigDir   = backendConfigDir,
			extensionConfigDir = extensionConfigDir,
			aclFile            = aclFile,
			depotId            = depotId,
			postpath           = postpath,
			context            = self._backend
		)

	def stopService(self):
		self._check.stop()

		if self._backend:
			self._backend.backend_exit()
		if self._backendManager:
			self._backendManager.backend_exit()
		if self._socket is not None:
			d = defer.Deferred()
			if self.factory is not None:
				d.addCallback(lambda x: self.factory.shutdown())
			d.addCallback(lambda x: self._cleanup)
			d.callback(None)

	def _cleanup(self):
		if os.path.exists(self._socket):
			os.unlink(self._socket)

	def processQuery(self, query, gzip=False):
		self.isRunning()
		decoder = JsonRpcRequestProcessor(query, self._backendManager, gzip=gzip)
		decoder.decodeQuery()
		decoder.buildRpcs()
		d = decoder.executeRpcs(False)
		d.addCallback(lambda x: decoder.getResults())
		return d

	def isRunning(self):
		self._lastContact = time.time()
		if self._check.running:
			self._check.reset()
		return True

	def __getattr__(self, name):
		if self._backendManager is not None:
			return getattr(self._backendManager, name, None)


class OpsiBackendProcessConnector(OpsiProcessConnector):

	def __init__(self, socket, timeout=None, reactor=reactor):
		OpsiProcessConnector.__init__(self, socket=socket, timeout=timeout, reactor=reactor)
		self._dataport = None

	def connect(self):
		def connected(remote):
			self.remote = remote
			remote.attachDataPort(self._dataport)
			return remote

		d = OpsiProcessConnector.connect(self)
		d.addCallback(connected)
		return d

	def assignDataPort(self, dataport):
		self._dataport = dataport
		self.remote.attachDataPort(self._dataport)


class OpsiBackendProcess(OpsiPyDaemon):

	user = "opsiconfd"
	serviceClass = OpsiBackendService
	configurationClass = BackendProcessConfiguration
	allowRestart = False

	def __init__(self, socket, args=[], reactor=reactor, logFile=logger.getLogFile()):
		self._socket = socket

		args.extend(["--socket", socket, "--logFile", logFile])
		OpsiPyDaemon.__init__(self, socket=socket, args=args, reactor=reactor)
		self._uid, self._gid = None, None

		self.check = ResetableLoop(self.checkRunning)

	def start(self):
		logger.info(u"Starting new backend worker process")
		d = OpsiPyDaemon.start(self)
		d.addCallback(lambda x: self._startCheck(30, False))
		return d

	def _startCheck(self, interval, now=False):
		self.check.start(interval=interval, now=now)

	def checkRunning(self):
		d = self.isRunning()
		d.addCallback(self.restart)

	def restart(self, isRunning):
		if not isRunning and self.allowRestart:
			d = self.stop()
			d.addCallback(lambda x: self.start)

	def processQuery(self, request, gzip=False):

		def reschedule(result):
			self.check.reset()
			return result

		d = self.callRemote("processQuery", request, gzip=gzip)
		d.addCallback(reschedule)
		d.addCallback(self.maybeStopped)
		return d

	def maybeStopped(self, result):
		if 'backend_exit' in map((lambda x: x.method), result):
			d = self.stop()
			d.addCallback(lambda x: result)
			return d
		else:
			return defer.succeed(result)

	def stop(self):
		logger.info(u"Stopping backend worker process (pid: %s)" % self._process.pid)
		self.allowRestart = False
		try:
			if self.check.running:
				self.check.stop()
		except Exception as e:
			logger.error(e)

		return OpsiPyDaemon.stop(self)

	def backend_exit(self):
		if self.check.running:
			self.check.stop()
		d = self.callRemote("backend_exit")
		d.addCallback(lambda x: self.stop())
		return d

	def __getattr__(self, name):
		logger.debug("Generating method '%s' on the fly." % name)
		return functools.partial(self.callRemote, name)

	def __str__(self):
		return "<OpsiBackendProcess (Socket: %s)>" % self.socket

	def __unicode__(self):
		return unicode(str(self))
