# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
opsi python library - Resource
"""

from twisted.internet import defer

from OPSI.Logger import Logger
from OPSI.Service.Worker import WorkerOpsi, WorkerOpsiJsonRpc, WorkerOpsiJsonInterface
from OPSI.Types import forceUnicode
from twisted.web import http, resource, server

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

	def render(self, request):
		''' Process request. '''
		try:
			logger.debug2(u"%s.render()", self.__class__.__name__)
			if not self.WorkerClass:
				raise RuntimeError(u"No worker class defined in resource %s" % self.__class__.__name__)
			worker = self.WorkerClass(self._service, request, self)
			worker.process()
			return server.NOT_DONE_YET
		except Exception as err:
			logger.error(err, exc_info=True)


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

