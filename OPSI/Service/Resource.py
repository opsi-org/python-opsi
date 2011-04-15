#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Resource   =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008, 2009 uib GmbH
   
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

from twisted.internet import defer
from OPSI.web2 import http, resource, server
import OPSI.web2.dav.static
from OPSI.Service.Worker import WorkerOpsi, WorkerOpsiJsonRpc, WorkerOpsiJsonInterface, WorkerOpsiDAV

from OPSI.Logger import *

logger = Logger()

class ResourceOpsi(resource.Resource):
	WorkerClass = WorkerOpsi
	isLeaf = True
	
	def __init__(self, service):
		resource.Resource.__init__(self)
		self._service = service
	
	def checkPrivileges(self, request, privileges, recurse=False, principal=None, inherited_aces=None):
		deferred = defer.Deferred()
		deferred.callback(None)
		return deferred
	
	def isCollection(self):
		return not self.isLeaf
	
	def hasProperty(self, property, request):
		deferred = defer.Deferred()
		deferred.callback(None)
		return deferred
	
	def renderHTTP(self, request):
		''' Process request. '''
		try:
			logger.debug2(u"%s.renderHTTP()" % self.__class__.__name__)
			if not self.WorkerClass:
				raise Exception(u"No worker class defined in resource %s" % self.__class__.__name__)
			worker = self.WorkerClass(self._service, request, self)
			return worker.process()
		except Exception, e:
			logger.logException(e)

class ResourceOpsiJsonRpc(ResourceOpsi):
	WorkerClass = WorkerOpsiJsonRpc
	isLeaf = False
	
	def __init__(self, service):
		ResourceOpsi.__init__(self, service)
	
	def locateChild(self, request, segments):
		return self, server.StopTraversal

class ResourceOpsiJsonInterface(ResourceOpsiJsonRpc):
	WorkerClass = WorkerOpsiJsonInterface
	
	def __init__(self, service):
		ResourceOpsi.__init__(self, service)
		self._interface = service.getInterface()


class ResourceOpsiDAV(OPSI.web2.dav.static.DAVFile):
	WorkerClass = WorkerOpsiDAV
	
	def __init__(self, service, path, readOnly=True, defaultType="text/plain", indexNames=None, authRequired=True):
		path = forceUnicode(path).encode('utf-8')
		OPSI.web2.dav.static.DAVFile.__init__(self, path, defaultType, indexNames)
		self._service = service
		self._readOnly = readOnly
		self._authRequired = authRequired
		
	def createSimilarFile(self, path):
		return self.__class__(self._service, path, readOnly=self._readOnly, defaultType=self.defaultType, indexNames=self.indexNames[:], authRequired = self._authRequired)
	
	def renderHTTP(self, request):
		try:
			if self._readOnly and request.method not in ('GET', 'PROPFIND', 'OPTIONS', 'USERINFO', 'HEAD'):
				logger.warning(u"Command %s not allowed (readonly)" % request.method)
				return http.Response(
					code	= responsecode.FORBIDDEN,
					stream	= "Readonly!" )
			worker = self.WorkerClass(self._service, request, self)
			return worker.process()
		except Exception, e:
			logger.logException(e)
	
	def renderHTTP_super(self, request, worker):
		deferred = super(ResourceOpsiDAV, self).renderHTTP(request)
		if isinstance(deferred, defer.Deferred):
			deferred.addErrback(worker._errback)
		return deferred

