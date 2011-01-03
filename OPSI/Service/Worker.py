#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Worker    =
   = = = = = = = = = = = = = = = = = = =
   
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

import base64, urllib
from twisted.internet import defer, reactor
from OPSI.web2 import responsecode, http_headers, http, stream

from OPSI.Logger import *
from OPSI.Types import OpsiAuthenticationError, OpsiBadRpcError

logger = Logger()

class Worker:
	def __init__(self, service, request, resource):
		self.service   = service
		self.request   = request
		self.query     = u''
		self.resource  = resource
		self.session   = None
	
	def process(self):
		logger.info(u"Worker %s started processing" % self)
		deferred = defer.Deferred()
		deferred.addCallback(self._getSession)
		deferred.addCallback(self._authenticate)
		deferred.addCallback(self._createBackend)
		deferred.addCallback(self._getQuery)
		deferred.addCallback(self._decodeQuery)
		deferred.addCallback(self._setResponse)
		deferred.addCallback(self._setCookie)
		deferred.addCallback(self._freeSession)
		deferred.addErrback(self._errback)
		deferred.callback(None)
		return deferred
	
	def _getSessionHandler(self):
		if hasattr(self.service, 'getSessionHandler'):
			return self.service.getSessionHandler()
		return None
		
	def _errback(self, failure):
		logger.debug2("%s._errback" % self.__class__.__name__)
		
		self._freeSession(failure)
		
		result = self._renderError(failure)
		result.code = responsecode.INTERNAL_SERVER_ERROR
		result = self._setCookie(result)
		try:
			failure.raiseException()
		except AttributeError, e:
			logger.debug(e)
			result = http.Response()
			result.code = responsecode.NOT_FOUND
		except OpsiAuthenticationError, e:
			logger.error(e)
			result.code = responsecode.UNAUTHORIZED
			result.headers.setHeader('www-authenticate', [('basic', { 'realm': 'OPSI Configuration Service' } )])
		except OpsiBadRpcError, e:
			logger.error(e)
			result.code = responsecode.BAD_REQUEST
		except Exception, e:
			# logger.logException(e)
			logger.error(failure)
		
		return result
	
	def _delayResult(self, seconds, result):
		class DelayResult:
			def __init__(self, seconds, result):
				self.result = result
				self.deferred = defer.Deferred()
				reactor.callLater(seconds, self.returnResult)
				
			def returnResult(self):
				self.deferred.callback(self.result)
		return DelayResult(seconds, result).deferred
		
	def _renderError(self, failure):
		result = http.Response()
		result.headers.setHeader('content-type', http_headers.MimeType("text", "html", {"charset": "utf-8"}))
		error = u'Unknown error'
		try:
			failure.raiseException()
		except Exception, e:
			error = forceUnicode(e)
		result.stream = stream.IByteStream(error.encode('utf-8'))
		return result
	
	def _freeSession(self, result):
		if self.session:
			logger.debug(u"Freeing session %s" % self.session)
			self.session.decreaseUsageCount()
		return result
	
	def _getAuthorization(self):
		(user, password) = (u'', u'')
		logger.debug(u"Trying to get username and password from Authorization header")
		auth = self.request.headers.getHeader('Authorization')
		if auth:
			logger.debug(u"Authorization header found (type: %s)" % auth[0])
			try:
				encoded = auth[1]
				
				logger.confidential(u"Auth encoded: %s" % encoded)
				parts = unicode(base64.decodestring(encoded), 'latin-1').split(':')
				if (len(parts) > 6):
					user = u':'.join(parts[:6])
					password = u':'.join(parts[6:])
				else:
					user = parts[0]
					password = u':'.join(parts[1:])
				user = user.strip()
				logger.confidential(u"Client supplied username '%s' and password '%s'" % (user, password))
			except Exception, e:
				logger.error(u"Bad Authorization header from '%s': %s" % (self.request.remoteAddr.host, e))
		return (user, password)
		
	def _getSession(self, result):
		''' This method restores a session or generates a new one. '''
		self.session = None
		
		logger.confidential(u"Request headers: %s " % self.request.headers)
		
		# Get user agent
		userAgent = None
		try:
			userAgent = self.request.headers.getHeader('user-agent')
		except Exception, e:
			logger.info(u"Client '%s' did not supply user-agent" % self.request.remoteAddr.host)
		if not userAgent:
			userAgent = 'unknown'
		
		# Get session handler
		sessionHandler = self._getSessionHandler()
		
		# Get authorization
		(user, password) = self._getAuthorization()
		
		# Get session id from cookie request header
		sessionId = u''
		try:
			for (k, v) in self.request.headers.getAllRawHeaders():
				if (k.lower() == 'cookie'):
					for cookie in v:
						for c in cookie.split(';'):
							if (c.find('=') == -1):
								continue
							(name, value) = c.split('=', 1)
							if (name.strip() == self.service.config['sessionName']):
								sessionId = forceUnicode(value.strip())
								break
					break
		except Exception, e:
			logger.error(u"Failed to get cookie from header: %s" % e)
		
		if not sessionId:
			logger.notice(u"Application '%s' on client '%s' did not send cookie" % (userAgent, self.request.remoteAddr.host))
			if not password:
				raise OpsiAuthenticationError(u"Application '%s' on client '%s' did neither supply session id nor password" % (userAgent, self.request.remoteAddr.host))
		
		# Get Session object
		self.session = sessionHandler.getSession(sessionId, self.request.remoteAddr.host)
		if (sessionId == self.session.uid):
			logger.info(u"Reusing session for client '%s', application '%s'" % (self.request.remoteAddr.host, userAgent))
		elif sessionId:
			logger.notice(u"Application '%s' on client '%s' supplied non existing session id: %s" % (userAgent, self.request.remoteAddr.host, sessionId))
		
		if sessionHandler and self.session.ip and (self.session.ip != self.request.remoteAddr.host):
			logger.critical(u"Client ip '%s' does not match session ip '%s', deleting old session and creating a new one" \
				% (self.request.remoteAddr.host, self.session.ip) )
			sessionHandler.deleteSession(self.session.uid)
			self.session = sessionHandler.getSession()
		
		# Set ip
		self.session.ip = self.request.remoteAddr.host
		
		# Set user-agent / application
		if self.session.userAgent and (self.session.userAgent != userAgent):
			logger.warning(u"Application changed from '%s' to '%s' for existing session of client '%s'" \
				% (self.session.userAgent, userAgent, self.request.remoteAddr.host))
		self.session.userAgent = userAgent
		
		logger.confidential(u"Session id is '%s' for client '%s', application '%s'" \
			% (self.session.uid, self.request.remoteAddr.host, self.session.userAgent))
		
		# Set user and password
		if not self.session.password:
			self.session.password = password
		
		if not self.session.user:
			if not user:
				raise Exception(u"No username from %s (application: %s)" % (self.session.ip, self.session.userAgent))
			self.session.user = user
			
		# Set hostname
		if not self.session.hostname and self.session.isHost:
			logger.info(u"Storing hostname '%s' in session" % self.session.user)
			self.session.hostname = self.session.user
		
		logger.confidential(u"Session content: %s" % self.session.__dict__)
		return result
	
	def _setCookie(self, result):
		if not self.session:
			return result
		
		# Add cookie to headers
		cookie = http_headers.Cookie(self.session.name.encode('ascii', 'replace'), self.session.uid.encode('ascii', 'replace'), path='/')
		if not isinstance(result, http.Response):
			result = http.Response()
		result.headers.setHeader('set-cookie', [ cookie ] )
		return result
		
	def _authenticate(self, result):
		''' This function tries to authenticate a user.
		    Raises an exception on authentication failure. '''
		return result
	
	def _getQuery(self, result):
		self.query = ''
		if   (self.request.method == 'GET'):
			self.query = urllib.unquote( self.request.querystring )
		elif (self.request.method == 'POST'):
			# Returning deferred needed for chaining
			d = stream.readStream(self.request.stream, self._handlePostData)
			d.addErrback(self._errback)
			return d
		else:
			raise ValueError(u"Unhandled method '%s'" % self.request.method)
		return result
		
	def _handlePostData(self, chunk):
		#logger.debug2(u"_handlePostData %s" % unicode(chunk, 'utf-8', 'replace'))
		self.query += chunk
		
	def _decodeQuery(self, result):
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
		logger.debug2(u"query: %s" % self.query)
		return result
	
	def _generateResponse(self, result):
		if not isinstance(result, http.Response):
			result = http.Response()
		result.code = responsecode.OK
		result.headers.setHeader('content-type', http_headers.MimeType("text", "html", {"charset": "utf-8"}))
		result.stream = stream.IByteStream("")
		return result
	
	def _setResponse(self, result):
		return self._generateResponse(result)
		

