# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2014-2019 uib GmbH <info@uib.de>

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
A simple Debug Shell.

:license: GNU Affero General Public License version 3
"""
from zope.interface import implements
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.credentials import IUsernamePassword
from twisted.cred.error import UnauthorizedLogin

from twisted.internet import defer
from twisted.python import failure

from twisted.conch.manhole import ColoredManhole
from twisted.conch.manhole_ssh import ConchFactory, TerminalRealm

from twisted.cred import portal
from twisted.internet import reactor

from OPSI.Backend.BackendManager import BackendAccessControl
from OPSI.Logger import Logger

logger = Logger()


class OpsiCredentialChecker(object):
	credentialInterfaces = (IUsernamePassword, )
	implements(ICredentialsChecker)

	def __init__(self, backend):
		self.backend = backend

	def requestAvatarId(self, credentials):
		try:
			auth = BackendAccessControl(
				backend=self.backend,
				username=credentials.username,
				password=credentials.password
			)
		except Exception:
			return failure.Failure()

		if auth.authenticated:
			return defer.succeed(credentials.username)
		else:
			return defer.fail(UnauthorizedLogin("invalid credentials."))


class DebugShell(object):

	def __init__(self, object, backend, namespace=globals(), port=6222, reactor=reactor):
		self.object = object
		self.backend = backend
		self.namespace = namespace

		self.sshPort = port
		self._sshConnection = None

		self.reactor = reactor

		self.checker = OpsiCredentialChecker(self.backend)

	def getRealm(self):
		realm = TerminalRealm()
		realm.chainedProtocolFactory.protocolFactory = lambda x: ColoredManhole(namespace=self.namespace)
		return realm

	def open(self):
		realm = self.getRealm()
		factory = ConchFactory(portal.Portal(realm, [self.checker]))
		self._sshConnection = self.reactor.listenTCP(self.sshPort, factory)

	def close(self):
		self._sshConnection.stopListening()
