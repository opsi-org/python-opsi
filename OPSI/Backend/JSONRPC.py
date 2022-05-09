# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
JSONRPC backend.

This backend executes the calls on a remote backend via JSONRPC.
"""

from opsicommon.client.jsonrpc import JSONRPCClient

from OPSI import __version__
from OPSI.Backend.Base import Backend

__all__ = ("JSONRPCBackend",)


class JSONRPCBackend(Backend, JSONRPCClient):  # pylint: disable=too-many-instance-attributes
	"""
	This Backend gives remote access to a Backend reachable via jsonrpc.
	"""
	def __init__(self, address: str, **kwargs) -> None:  # pylint: disable=too-many-branches,too-many-statements
		"""
		Backend for JSON-RPC access to another opsi service.

		:param compression: Should requests be compressed?
		:type compression: bool
		"""

		self._name = "jsonrpc"

		Backend.__init__(self, **kwargs)

		connection_pool_size = 250
		for option, value in kwargs.copy().items():
			if option.lower().replace("_", "") in ("connectionpoolsize", "httppoolmaxsize"):
				if value not in (None, ""):
					connection_pool_size = int(value)
				del kwargs[option]
		kwargs["connection_pool_size"] = connection_pool_size

		JSONRPCClient.__init__(self, address, **kwargs)

		self._application = f"opsi-jsonrpc-backend/{__version__}"

	def jsonrpc_getSessionId(self) -> str:
		return self.session_id

	def backend_exit(self) -> None:
		self.disconnect()
