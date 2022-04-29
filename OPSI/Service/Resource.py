# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
opsi python library - Resource
"""

from opsicommon.logging import get_logger
from twisted.internet import defer
from twisted.web import resource, server

from OPSI.Service.Worker import WorkerOpsi, WorkerOpsiJsonInterface, WorkerOpsiJsonRpc

logger = get_logger("opsi.general")


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
		"""Process request."""
		try:
			logger.trace("%s.render()", self.__class__.__name__)
			if not self.WorkerClass:
				raise RuntimeError(f"No worker class defined in resource {self.__class__.__name__}")
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
		return self, server.StopTraversal  # pylint: disable=no-member


class ResourceOpsiJsonInterface(ResourceOpsiJsonRpc):
	WorkerClass = WorkerOpsiJsonInterface

	def __init__(self, service):
		ResourceOpsi.__init__(self, service)
		self._interface = service.getInterface()
