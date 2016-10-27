#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   This module is part of the desktop management solution opsi

   (open pc server integration) http://www.opsi.org

   Copyright (C) 2010 Andrey Petrov
   Copyright (C) 2010-2016 uib GmbH

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
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

import os
from pickle import dumps, loads, HIGHEST_PROTOCOL
from types import StringType

from twisted.internet import reactor
from twisted.internet.protocol import ReconnectingClientFactory, ClientCreator
from twisted.internet.defer import maybeDeferred, Deferred, succeed
from twisted.internet.address import UNIXAddress
from twisted.protocols.amp import Argument, String, Integer, Command, AMP, MAX_VALUE_LENGTH
from twisted.python.failure import Failure

from OPSI.Logger import LOG_DEBUG, Logger
from OPSI.Util import randomString

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO

logger = Logger()


USE_BUFFERED_RESPONSE = "__USE_BUFFERED_RESPONSE__"


class RemoteArgument(Argument):

	def toString(self, obj):
		return dumps(obj, HIGHEST_PROTOCOL)

	def fromString(self, str):
		return loads(str)


class RemoteExecutionException(Exception):
	pass


class OpsiProcessException(Exception):

	def __init__(self, failure):
		self.failure = failure

	def __str__(self):
		return str(self.failure)

	def __getstate__(self):
		return self.failure.__getstate__()

	def __setstate__(self, state):
		self.failure = Failure()
		self.failure.__setstate__(state)


class RemoteProcessCall(Command):

	arguments = [
		('name', String()),
		('argString', String()),
		('tag', Integer())
	]

	response = [
		('tag', Integer()),
		('result', RemoteArgument())
	]

	errors = {
		RemoteExecutionException: 'RemoteExecutionError',
		OpsiProcessException: 'OpsiProcessError'
	}

	requiresAnswer = True


class ChunkedArgument(Command):

	arguments = [
		('tag', Integer()),
		('chunk', String())
	]

	response = [('result', Integer())]

	errors = {
		RemoteExecutionException: 'RemoteExecutionError',
		OpsiProcessException: 'OpsiProcessError'
	}

	requiresAnswer = True


class ResponseBufferPush(Command):

	arguments = [
		('tag', Integer()),
		('chunk', String())
	]

	response = [('result', Integer())]

	errors = {
		RemoteExecutionException: 'RemoteExecutionError',
		OpsiProcessException: 'OpsiProcessError'
	}

	requiresAnswer = True


class OpsiProcessAddress(UNIXAddress):

	def __init__(self, name):
		assert name.endswith(".socket")
		UNIXAddress.__init__(self, name)
		self.dir, name = self.name.rsplit("/", 1)
		self._name = name.rsplit(".", 1)[0]

	@property
	def name(self):
		return os.path.join(self.dir, self._name+".socket")

	def generateUniqueName(self):
		return os.path.join(self.dir, "%s-%s.socket" % (self._name, randomString(32)))


class OpsiQueryingProtocol(AMP):

	def __init__(self):
		AMP.__init__(self)
		self.tag = 1
		self.responseBuffer = {}
		self.dataSink = None

	def getNextTag(self):
		self.tag = self.tag + 1
		return self.tag

	def openDataSink(self, address):
		try:
			if not self.dataSink:
				self.dataSink = reactor.listenUNIX("%s.dataport" % address, OpsiProcessProtocolFactory(self))
		except Exception as e:
			logger.error(u"Could not open data socket %s: %s" % ("%s.dataport" % address, e))
			raise e

	def closeDataSink(self):
		self.dataSink.factory.stopTrying()
		if self.dataSink is not None:
			self.dataSink.loseConnection()
			self.dataSink = None

	def _callRemote(self, command, **kwargs):
		deferred = Deferred()

		def p(response):
			deferred.callback(response)
		result = self.callRemote(command, **kwargs)
		result.addBoth(p)
		return deferred

	def sendRemoteCall(self, method, args=[], kwargs={}):
		d = Deferred()

		argString = dumps((args, kwargs), HIGHEST_PROTOCOL)
		tag = self.getNextTag()

		chunks = [argString[i:i + MAX_VALUE_LENGTH] for i in xrange(0, len(argString), MAX_VALUE_LENGTH)]

		if len(chunks) > 1:
			for chunk in chunks[:-1]:
				def sendChunk(tag, chunk):
					deferedSend = lambda x: self.callRemote(
							commandType=ChunkedArgument, tag=tag, chunk=chunk)
					return deferedSend

				d.addCallback(sendChunk(tag=tag, chunk=chunk))

		d.addCallback(lambda x: self.callRemote(RemoteProcessCall, name=method, tag=tag, argString=chunks[-1]))
		d.callback(None)
		return d

	@ResponseBufferPush.responder
	def chunkedResponseReceived(self, tag, chunk):
		self.responseBuffer.setdefault(tag, StringIO.StringIO()).write(chunk)
		return {'result': tag}

	def getResponseBuffer(self, tag):
		return self.responseBuffer.pop(tag)


class OpsiResponseProtocol(AMP):

	def __init__(self):
		AMP.__init__(self)
		self.buffer = {}
		self.dataport = None

	def assignDataPort(self, protocol):
		self.dataport = protocol

	def closeDataPort(self, result=None):
		if self.dataport is not None:
			if self.dataport.transport is not None:
				self.dataport.transport.loseConnection()
			self.dataport = None
		return result

	@RemoteProcessCall.responder
	def remoteProcessCallReceived(self, tag, name, argString):
		args = self.buffer.pop(tag, argString)

		if type(args) is not StringType:
			args.write(argString)
			args, closed = args.getvalue(), args.close()

		args, kwargs = loads(args)

		method = getattr(self.factory._remote, name, None)

		if method is None:
			raise RemoteExecutionException(u"Daemon has no method %s" % (name))
		rd = Deferred()
		d = maybeDeferred(method, *args, **kwargs)

		d.addCallback(lambda result: self.processResult(result, tag))
		d.addCallback(rd.callback)
		d.addErrback(self.processFailure)
		d.addErrback(rd.errback)
		return rd

	def processResult(self, result, tag):
		r = dumps(result, HIGHEST_PROTOCOL)
		chunks = [r[i:i + MAX_VALUE_LENGTH] for i in xrange(0, len(r), MAX_VALUE_LENGTH)]
		dd = Deferred()

		def handleConnectionFailure(fail):
			logger.error(u"Failed to connect to socket %s: %s" % (self.factory._dataport, fail.getErrorMessage()))
			return fail

		if len(chunks) > 1:
			if self.dataport is None:
				logger.info(u"Connecting do data port %s" % self.factory._dataport)
				dd.addCallback(lambda x: ClientCreator(reactor, AMP).connectUNIX(self.factory._dataport))
				dd.addErrback(handleConnectionFailure)
				dd.addCallback(self.assignDataPort)
			else:
				dd = succeed(None)

			for chunk in chunks:
				def sendChunk(tag, chunk):
					deferedSend = lambda x: self.dataport.callRemote(
							commandType=ResponseBufferPush, tag=tag, chunk=chunk)
					return deferedSend
				dd.addCallback(sendChunk(tag, chunk))

			dd.addCallback(lambda x: {"tag": tag, "result": USE_BUFFERED_RESPONSE})

		else:
			dd.addCallback(lambda x: {"tag": tag, "result": result})
		dd.addBoth(self.closeDataPort)
		dd.callback(None)
		return dd

	@ChunkedArgument.responder
	def chunkReceived(self, tag, chunk):
		buffer = self.buffer.setdefault(tag, StringIO.StringIO())
		buffer.write(chunk)
		return {'result': tag}

	def processFailure(self, failure):
		logger.logFailure(failure, logLevel=LOG_DEBUG)
		raise OpsiProcessException(failure)


class OpsiProcessProtocol(OpsiQueryingProtocol, OpsiResponseProtocol):
	def __init__(self):
		OpsiQueryingProtocol.__init__(self)
		OpsiResponseProtocol.__init__(self)


class OpsiProcessProtocolFactory(ReconnectingClientFactory):

	protocol = OpsiProcessProtocol

	def __init__(self, remote=None, dataport=None, reactor=reactor):
		self._remote = remote
		self._dataport = dataport
		self._protocol = None
		self._notifiers = []
		self._reactor = reactor

	def buildProtocol(self, addr):
		p = ReconnectingClientFactory.buildProtocol(self, addr)
		p.address = addr
		self._protocol = p
		self.notifySuccess(p)
		return p

	def addNotifier(self, callback, errback=None):
		self._notifiers.append((callback, errback))

	def removeNotifier(self, callback, errback=None):
		if (callback, errback) in self._notifiers:
			self._notifiers.remove((callback, errback))

	def notifySuccess(self, *args, **kwargs):
		for callback, errback in self._notifiers:
			self._reactor.callLater(0, callback, *args, **kwargs)

	def notifyFailure(self, failure):
		for callback, errback in self._notifiers:
			if errback is not None:
				self._reactor.callLater(0, errback, failure)

	def clientConnectionFailed(self, connector, reason):
		ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

		if self.maxRetries is not None and (self.retries > self.maxRetries):
			self.notifyFailure(reason)  # Give up

	def shutdown(self):
		self.stopTrying()
		if self._protocol is not None:
			if self._protocol.transport is not None:
				self._protocol.transport.loseConnection()
			if self._protocol.dataport:
				self._protocol.closeDataPort()
			if self._protocol.dataSink:
				self._protocol.closeDataSink()


class RemoteDaemonProxy(object):

	def __init__(self, protocol):
		self._protocol = protocol
		self._dataport = None

	def __getattr__(self, method):

		def callRemote(*args, **kwargs):
			result = Deferred()

			def processResponse(response):
				r = response["result"]
				if r == USE_BUFFERED_RESPONSE:

					buffer = self._dataport.getResponseBuffer(response["tag"])

					if buffer is None:
						raise Exception(u"Expected a buffered response but no response buffer was found for tag %s" % r["tag"])

					s = buffer.getvalue()

					buffer.close()

					obj = loads(s)

					result.callback(obj)
				else:
					result.callback(r)

			def processFailure(failure):
				logger.logFailure(failure, logLevel=LOG_DEBUG)
				if failure.type == OpsiProcessException:
					try:
						failure.raiseException()
					except OpsiProcessException as e:
						result.errback(e.failure)
					except Exception as e:
						raise e
					else:
						logger.error(u"This should not happen!")
						result.errback(failure)
				else:
					result.errback(failure)
			d = self._protocol.sendRemoteCall(
				method=method,
				args=args,
				kwargs=kwargs
			)
			d.addCallback(processResponse)
			d.addErrback(processFailure)
			return result
		return callRemote

	def attachDataPort(self, dataport):
		self._dataport = dataport


class OpsiProcessConnector(object):

	factory = OpsiProcessProtocolFactory
	remote = RemoteDaemonProxy

	def __init__(self, socket, timeout=None, reactor=reactor):
		self._factory = OpsiProcessProtocolFactory()
		self._connected = None
		self._socket = socket
		self._timeout = timeout
		self._reactor = reactor
		self._protocol = None

	def connect(self):
		self._connected = Deferred()

		def success(result):
			self._factory.removeNotifier(success, failure)
			self._protocol = result
			self._remote = self.remote(self._protocol)
			d, self._connected = self._connected, None
			self._connectDataPort()
			d.callback(self._remote)

		def failure(fail):
			self._factory.removeNotifier(success, failure)
			d, self._connected = self._connected, None
			d.errback(fail)

		self._factory = self.factory(reactor=self._reactor)
		try:
			self._reactor.connectUNIX(self._socket, self._factory)
			self._factory.addNotifier(success, failure)
		except Exception as e:
			logger.error(u"Failed to connect to socket %s: %s"(self._socket, e))
			self._connected.errback(Failure())

		return self._connected

	def _connectDataPort(self):
		f = OpsiProcessProtocolFactory()
		f.addNotifier(self._remote.attachDataPort)
		self._dataport = self._reactor.listenUNIX("%s.dataport" % self._socket, f)
		return self._dataport

	def connectionFailed(self, reason):
		d, self._connected = self._connected, None
		d.errback(reason)

	def disconnect(self):
		if self._factory:
			self._factory.shutdown()
		if self._remote:
			if self._remote._protocol.transport:
				self._remote._protocol.transport.loseConnection()
			if self._dataport:
				self._dataport.stopListening()
			self._remote = None
		if self._connected:
			self._connected = None
