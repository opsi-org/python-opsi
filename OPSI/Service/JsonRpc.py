#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - JsonRpc     =
   = = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

import time, zlib, urllib, copy

from twisted.internet.defer import maybeDeferred, Deferred, succeed
from twisted.internet import threads

from OPSI.Util import objectToHtml, toJson, fromJson
from OPSI.Logger import *
from OPSI.Types import *
from OPSI.Object import serialize, deserialize
from OPSI.web2 import stream
logger = Logger()

class JsonRpc(object):
	def __init__(self, instance, interface, rpc):
		self._instance  = instance
		self._interface = interface
		self.started    = None
		self.ended      = None
		self.type       = rpc.get('type')
		self.rpcVersion = rpc.get('jsonrpc', None)
		self.tid        = rpc.get('tid', rpc.get('id'))
		self.action     = rpc.get('action')
		self.method     = rpc.get('method')
		self.params     = rpc.get('params', rpc.get('data'))
		if not self.params:
			self.params = []
		self.result    = None
		self.exception = None
		self.traceback = None
		if not self.tid:
			raise Exception(u"No transaction id ((t)id) found in rpc")
		if not self.method:
			raise Exception(u"No method found in rpc")
	
	def isStarted(self):
		return bool(self.started)
	
	def hasEnded(self):
		return bool(self.ended)
	
	def getMethodName(self):
		if self.action:
			return u'%s_%s' % (self.action, self.method)
		return self.method
	
	def getDuration(self):
		if not self.started or not self.ended:
			return None
		return round(self.ended - self.started, 3)
		
	def execute(self, result=None):
		# Execute rpc
		self.result = None
		params = []
		for param in self.params:
			params.append(param)
		try:
			self.started = time.time()
			
			methodInterface = None
			for m in self._interface:
				if (self.getMethodName() == m['name']):
					methodInterface = m
					break
			if not methodInterface:
				raise OpsiRpcError(u"Method '%s' is not valid" % self.getMethodName())
			
			keywords = {}
			if methodInterface['keywords']:
				l = 0
				if methodInterface['args']:
					l += len(methodInterface['args'])
				if methodInterface['varargs']:
					l += len(methodInterface['varargs'])
				if (len(params) >= l):
					if not type(params[-1]) is types.DictType:
						raise Exception(u"kwargs param is not a dict: %s" % params[-1])
					for (key, value) in params.pop(-1).items():
						keywords[str(key)] = deserialize(value)
			
			params = deserialize(params)
			
			pString = forceUnicode(params)[1:-1]
			if keywords:
				pString += u', ' + forceUnicode(keywords)
			if (len(pString) > 200):
				pString = pString[:200] + u'...'
			
			logger.notice(u"-----> Executing: %s(%s)" % (self.getMethodName(), pString))
			
			instance = self._instance
			if keywords:
				self.result = eval( "instance.%s(*params, **keywords)" % self.getMethodName() )
			else:
				self.result = eval( "instance.%s(*params)" % self.getMethodName() )
			
			logger.info(u'Got result')
			logger.debug2(self.result)
		
		except Exception, e:
			logger.logException(e, LOG_INFO)
			logger.error(u'Execution error: %s' % forceUnicode(e))
			self.exception = e
			self.traceback = []
			tb = sys.exc_info()[2]
			while (tb != None):
				f = tb.tb_frame
				c = f.f_code
				self.traceback.append(u"     line %s in '%s' in file '%s'" % (tb.tb_lineno, c.co_name, c.co_filename))
				tb = tb.tb_next
		self.ended = time.time()
		
	def getResponse(self):
		response = {}
		if (self.type == 'rpc'):
			response['tid']    = self.tid
			response['action'] = self.action
			response['method'] = self.method
			if self.exception:
				response['type']    = 'exception'
				response['message'] = { 'class': self.exception.__class__.__name__, 'message': forceUnicode(self.exception) }
				response['where']   = self.traceback
			else:
				response['type']   = 'rpc'
				response['result'] = self.result
		else:
			response['id'] = self.tid
			if (self.rpcVersion == '2.0'):
				response['jsonrpc'] = '2.0'
			if self.exception:
				if (self.rpcVersion == '2.0'):
					code = 0
					try:
						code = int(getattr(e, 'errno'))
					except:
						pass
					response['error']  = { 'code': code, 'message': forceUnicode(self.exception), 'data': {'class': self.exception.__class__.__name__}  }
				else:
					response['error']  = { 'class': self.exception.__class__.__name__, 'message': forceUnicode(self.exception) }
				response['result'] = None
			else:
				response['error']  = None
				response['result'] = self.result
		return response

	def __getstate__(self):
		state = self.__dict__
		state['_instance'] = None
		state['_interface'] = None
		return state
		
	
	
class JsonRpcRequestProcessor(object):
	
	def __init__(self, request, callInstance, callInterface=None):
		self.request = request
		self.callInstance = callInstance
		if callInterface is None:
			self.callInterface = callInstance.backend_getInterface()
		else:
			self.callInterface = callInterface
		self.query = None
		self.rpcs = []
	
		d = self.getQuery()
	
	
	def getQuery(self):
		self.query = ''
		if   (self.request.method == 'GET'):
			self.query = urllib.unquote( self.request.querystring )
			return succeed(self.query)
		elif (self.request.method == 'POST'):
			# Returning deferred needed for chaining
			def handlePostData(chunk):
				self.query += chunk
			d = stream.readStream(self.request.stream, handlePostData)
			return d
		else:
			raise ValueError(u"Unhandled method '%s'" % self.request.method)

	
	def decodeQuery(self):
		try:
			if (self.request.method == 'POST'):
				contentType = self.request.headers.getHeader('content-type')
				logger.debug(u"Content-Type: %s" % contentType)
				if contentType and contentType.mediaType.startswith('gzip'):
					logger.debug(u"Expecting compressed data from client")
					self.query = zlib.decompress(self.query)
			self.query = unicode(self.query, 'utf-8')
		except (UnicodeError, UnicodeEncodeError), e:
			self.service.statistics().addEncodingError('query', self.session.ip, self.session.userAgent, unicode(e))
			self.query = unicode(self.query, 'utf-8', 'replace')
		return self.query
	
	
	def buildRpcs(self):
		if not self.query:
			return None
		if not self.callInstance:
			raise Exception(u"Call instance not defined in %s" % self)
		if not self.callInterface:
			raise Exception(u"Call interface not defined in %s" % self)
		
		rpcs = []
		try:
			rpcs = fromJson(self.query, preventObjectCreation = True)
			if not rpcs:
				raise Exception(u"Got no rpcs")
		
		except Exception, e:
			raise OpsiBadRpcError(u"Failed to decode rpc: %s" % e)
		
		for rpc in forceList(rpcs):
			rpc = JsonRpc(instance = self.callInstance, interface = self.callInterface, rpc = rpc)
			self.rpcs.append(rpc)
		
		return self.rpcs
	
	def _executeRpc(self, rpc, thread=True):
		if thread:
			deferred = threads.deferToThread(rpc.execute)
		else:
			deferred = maybeDeferred(rpc.execute)
		return deferred
		
	def executeRpcs(self, thread=True):
		deferred = Deferred()
		for rpc in self.rpcs:
			deferred.addCallback(lambda x: self._executeRpc(rpc, thread))
		deferred.callback(None)
		return deferred
	
	def getResults(self):
		#if len(self.rpcs) == 0:
		#	raise ValueError("No rpcs to generate results from.")
		return self.rpcs
			

