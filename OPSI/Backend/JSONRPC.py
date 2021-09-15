# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
JSONRPC backend.

This backend executes the calls on a remote backend via JSONRPC.
"""

from OPSI import __version__
from OPSI.Backend.Base import Backend

from opsicommon.client.jsonrpc import JSONRPCClient

__all__ = ('JSONRPCBackend',)

class JSONRPCBackend(Backend, JSONRPCClient):  # pylint: disable=too-many-instance-attributes

	def __init__(self, address, **kwargs):  # pylint: disable=too-many-branches,too-many-statements
		"""
		Backend for JSON-RPC access to another opsi service.

		:param compression: Should requests be compressed?
		:type compression: bool
		"""

		self._name = 'jsonrpc'

		Backend.__init__(self, **kwargs)
		JSONRPCClient.__init__(self, address, **kwargs)

		self._application = 'opsi-jsonrpc-backend/%s' % __version__

	def jsonrpc_getSessionId(self):
		if not self._session.cookies or not self._session.cookies._cookies:  # pylint: disable=protected-access
			return None
		for tmp1 in self._session.cookies._cookies.values():  # pylint: disable=protected-access
			for tmp2 in tmp1.values():
				for cookie in tmp2.values():
					return f"{cookie.name}={cookie.value}"

	def backend_exit(self):
		self.disconnect()
