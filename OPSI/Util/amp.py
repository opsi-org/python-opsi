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
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.defer import DeferredList, maybeDeferred, Deferred
from twisted.internet.unix import Connector
from twisted.protocols.amp import Argument, String, Integer, Boolean, Command, AMP, MAX_VALUE_LENGTH

from pickle import dumps, loads
from types import StringType
from OPSI.Logger import *
logger = Logger()

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO

class RemoteArgument(Argument):
	
	def toString(self, obj):
		return dumps(obj)
	
	def fromString(self, str):
		return loads(str)

class RemoteProcessException(Exception):
	pass

class RemoteProcessCall(Command):
	
	arguments = [	('method', String()),
			('argString', String()),
			('tag', Integer())]
	
	response = [('result', RemoteArgument())]

	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class ChunkedArgument(Command):
	
	arguments = [	('tag', Integer()),
			('argString', String())]

	response = [('result', Integer())]
	
	errors = {RemoteProcessException: 'RemoteProcessError'}
	
	requiresAnswer = True
	
class OpsiProcessProtocol(AMP):
	
	def __init__(self):
		AMP.__init__(self)
		self.tag = 1
		self.buffer = {}

	def getNextTag(self):
		self.tag += 1
		return self.tag

	@RemoteProcessCall.responder
	def remoteProcessCallReceived(self, tag, method, argString):

		args = self.buffer.pop(tag, argString)
		
		if type(args) is not StringType:
			args.write(argString)
			args, closed = args.getvalue(), args.close()
				
		args, kwargs = loads(args)
		
		method = getattr(self.factory._remote, method, None)
		
		if method is None:
			raise RemoteProcessException(u"Daemon %s has no method %s" % (self.factory._remote, method.__name__))
		
		d = maybeDeferred(method, *args, **kwargs)
		d.addCallback(lambda result: {"result":result})
		d.addErrback(self.processFailure)
		return d

	@ChunkedArgument.responder
	def chunkReceived(self, tag, argString):
		self.buffer.setdefault(tag, StringIO.StringIO()).write(args)
		return tag
	
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
		
		argString = dumps((args,kwargs))
		tag = self.getNextTag()
		
		chunks = [argString[i:i + MAX_VALUE_LENGTH] for i in range(0, len(argString), MAX_VALUE_LENGTH)]

		if len(chunks) > 1:
			for c in chunks[:-1]:
				d.addCallback(lambda x: self.callRemote(commandType=ChunkedArgument, tag=tag, argString=c))

		d.addCallback(lambda x: self.callRemote(RemoteProcessCall, method=method, tag=tag, argString=chunks[-1]))
		d.callback(None)
		return d
	
	def processFailure(self, failure):
		raise RemoteProcessException(failure.getErrorMessage())
	
class OpsiProcessProtocolFactory(ReconnectingClientFactory):
	
	protocol = OpsiProcessProtocol
	
	def __init__(self, remote=None):
		self._remote = remote


	
class RemoteDaemonProxy(object):
	
	def __init__(self, protocol):
		
		self._protocol = protocol
	
	def __getattr__(self, method):
		
		def callRemote(*args, **kwargs):
			result = Deferred()
			d = self._protocol.sendRemoteCall(	method=method,
								args=args,
								kwargs=kwargs)
			d.addCallback(lambda response: result.callback(response["result"]))
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


