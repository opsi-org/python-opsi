# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2019 uib GmbH <info@uib.de>

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
opsi python library - Resource

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from twisted.internet import defer

import OPSI.web2.dav.static
from OPSI.Logger import Logger
from OPSI.Service.Worker import (WorkerOpsi, WorkerOpsiJsonRpc,
	WorkerOpsiJsonInterface, WorkerOpsiDAV)
from OPSI.Types import forceUnicode
from OPSI.web2 import http, resource, server, responsecode

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
			logger.debug2(u"{0}.renderHTTP()", self.__class__.__name__)
			if not self.WorkerClass:
				raise RuntimeError(u"No worker class defined in resource %s" % self.__class__.__name__)
			worker = self.WorkerClass(self._service, request, self)
			return worker.process()
		except Exception as exc:
			logger.logException(exc)


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

