#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   This module is part of the desktop management solution opsi
   
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 Andrey Petrov
   Copyright (C) 2010 uib GmbH
   
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

from twisted.internet import reactor
from twisted.internet.task import deferLater
from twisted.internet.protocol import ReconnectingClientFactory, ClientCreator
from twisted.internet.defer import DeferredList, maybeDeferred, Deferred, succeed
from twisted.internet.unix import Connector
from twisted.protocols.amp import Argument, String, Integer, Boolean, Command, AMP, MAX_VALUE_LENGTH

import base64, hashlib
from pickle import dumps, loads, HIGHEST_PROTOCOL
from types import StringType
from OPSI.Logger import *
logger = Logger()

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO



USE_BUFFERED_RESPONSE = "__USE_BUFFERED_RESPONSE__"

class RemoteArgument(Argument):
	
	def toString(self, obj):
		return dumps(obj, HIGHEST_PROTOCOL)
	
	def fromString(self, str):
		return loads(str)

class RemoteProcessException(Exception):
	pass

class RemoteProcessCall(Command):
	
	arguments = [	('name', String()),
			('argString', String()),
			('tag', Integer())]
	
	response = [	('tag', Integer()),
			('result', RemoteArgument())]

	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class ChunkedArgument(Command):
	
	arguments = [	('tag', Integer()),
			('argString', String())]

	response = [('result', Integer())]
	
	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True

class ResponseBufferPush(Command):
	
	arguments = [	('tag', Integer()),
			('chunk', String())]

	response = [('result', Integer())]
	
	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class OpsiQueryingProtocol(AMP):
	
	def __init__(self):
		AMP.__init__(self)
		self.tag = 1
		self.responseBuffer = {}
		self.dataSink = None
		
	def getNextTag(self):
		self.tag += 1
		return self.tag
	
	def openDataSink(self):
		
		self.dataSink = reactor.listenUNIX("%s.dataport" % self.addr.name, OpsiProcessProtocolFactory(self))
		
	def _callRemote(self, command, **kwargs):
		
		deferred = Deferred()

		def p(response):
			deferred.callback(response)
		result = self.callRemote(command, **kwargs)
		result.addBoth(p)
		return deferred
	
	def sendRemoteCall(self, method, args=[], kwargs={}):
		
		d = Deferred()
		result = Deferred()
		
		argString = dumps((args,kwargs), HIGHEST_PROTOCOL)
		tag = self.getNextTag()
		
		chunks = [argString[i:i + MAX_VALUE_LENGTH] for i in xrange(0, len(argString), MAX_VALUE_LENGTH)]

		if len(chunks) > 1:
			for chunk in chunks[:-1]:
				def sendChunk(tag, chunk):
					deferedSend = lambda x: self.dataport.callRemote(
							commandType=ResponseBufferPush, tag=tag, chunk=chunk)
					return deferedSend
					
				d.addCallback(sendChunk(tag=tag, argString=chunk))
		d.addCallback(lambda x: self.callRemote(RemoteProcessCall, name=method, tag=tag, argString=chunks[-1]))
		d.callback(None)
		return d

	
	@ResponseBufferPush.responder
	def chunkedResponseReceived(self, tag, chunk):
		self.responseBuffer.setdefault(tag, StringIO.StringIO()).write(chunk)
		return {'result': tag}
	

	def getResponseBuffer(self,tag):
		return self.dataSink.factory._protocol.responseBuffer.pop(tag)
	
class OpsiResponseProtocol(AMP):
	
	def __init__(self):
		AMP.__init__(self)
		self.buffer = {}
		self.dataport = None

	def assignDataPort(self, protocol):
		self.dataport = protocol

	@RemoteProcessCall.responder
	def remoteProcessCallReceived(self, tag, name, argString):

		args = self.buffer.pop(tag, argString)
		
		if type(args) is not StringType:
			args.write(argString)
			args, closed = args.getvalue(), args.close()
				
		args, kwargs = loads(args)

		method = getattr(self.factory._remote, name, None)
		

		if method is None:
			raise RemoteProcessException(u"Daemon has no method %s" % (name))
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
		
		if len(chunks) > 1:
			if self.dataport is None:
				dd.addCallback(lambda x: ClientCreator(reactor, AMP).connectUNIX(self.factory._dataport))
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
			dd.addCallback(lambda x: {"tag": tag, "result":result})
		dd.callback(None)
		return dd

	@ChunkedArgument.responder
	def chunkReceived(self, tag, argString):
		buffer = self.buffer.setdefault(tag, StringIO.StringIO())
		buffer.write(argString)
		return {'result': tag}
	

	def processFailure(self, failure):
		logger.logFailure(failure)
		raise RemoteProcessException(failure.value)


class OpsiProcessProtocol(OpsiQueryingProtocol, OpsiResponseProtocol):
	def __init__(self):
		OpsiQueryingProtocol.__init__(self)
		OpsiResponseProtocol.__init__(self)


class OpsiProcessProtocolFactory(ReconnectingClientFactory):
	
	protocol = OpsiProcessProtocol
	
	def __init__(self, remote=None, dataport = None):
		self._remote = remote
		self._dataport = dataport
		self._protocol = None
		
	def buildProtocol(self, addr):
		p = ReconnectingClientFactory.buildProtocol(self, addr)
		p.addr = addr
		self._protocol = p
		return p
	
class RemoteDaemonProxy(object):
	
	def __init__(self, protocol):
		
		self._protocol = protocol
	
	def __getattr__(self, method):
		
		def callRemote(*args, **kwargs):
			result = Deferred()
			
			def processResponse(response):
				r = response["result"]
				if r == USE_BUFFERED_RESPONSE:
					buffer = self._protocol.getResponseBuffer(response["tag"])
					
					if buffer is None:
						raise Exception("Expected a buffered response but no response buffer was found for tag %s" % r["tag"])

					s = buffer.getvalue()
					
					buffer.close()
					
					obj = loads(s)

					result.callback(obj)
				else:
					result.callback(r)

			
			def processFailure(failure):
				logger.error(failure.getErrorMessage())
				result.errback(failure)
			d = self._protocol.sendRemoteCall(	method=method,
								args=args,
								kwargs=kwargs)
			d.addCallback(processResponse)
			d.addErrback(processFailure)
			return result
		return callRemote
	
class OpsiProcessConnector(Connector):
	
	factory = OpsiProcessProtocolFactory
	remote = RemoteDaemonProxy
	
	def __init__(self, socket, timeout=None, reactor=reactor):
		self._factory = OpsiProcessProtocolFactory()
		self._connected = None
		Connector.__init__(self, address=socket, factory=self._factory, timeout=timeout,reactor=reactor,checkPID=0)
		
	def connect(self):
		Connector.connect(self)
		self._connected = Deferred()
		return self._connected
	
	def buildProtocol(self, addr):
		p = Connector.buildProtocol(self,addr)
		p.openDataSink()
		self._remote = self.remote(p)
		reactor.callLater(0.1, self._connected.callback, self._remote) # dirty hack, needs to be delayed until boxsender is set up
		return p
			
	def connectionFailed(self, reason):
		Connector.connectionFailed(self, reason)
		self._connected.errback(reason)
	
	def disconnect(self):
		if self._factory:
			self._factory.stopTrying()
		Connector.disconnect(self)
		self._remote = None


