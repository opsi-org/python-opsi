# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
HostControl Backend: Safe edition
"""

from typing import Any, Dict, List

from OPSI.Backend.Base.Backend import Backend
from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Exceptions import BackendMissingDataError

__all__ = ("HostControlSafeBackend",)


class HostControlSafeBackend(HostControlBackend):
	"""
	This backend is the same as the HostControl-backend but it will not
	allow to call methods without hostId
	"""

	def __init__(self, backend: Backend, **kwargs) -> None:
		self._name = "hostcontrolsafe"
		HostControlBackend.__init__(self, backend, **kwargs)

	def hostControlSafe_start(self, hostIds: List[str] = None) -> Dict[str, Any]:
		"""Switches on remote computers using WOL."""
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_start(self, hostIds or [])

	def hostControlSafe_shutdown(self, hostIds: List[str] = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_shutdown(self, hostIds or [])

	def hostControlSafe_reboot(self, hostIds: List[str] = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_reboot(self, hostIds or [])

	def hostControlSafe_fireEvent(self, event: str, hostIds: List[str] = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_fireEvent(self, event, hostIds or [])

	def hostControlSafe_showPopup(  # pylint: disable=too-many-arguments
		self, message: str, hostIds: List[str] = None, mode: str = "prepend", addTimestamp: bool = True, displaySeconds: float = 0
	) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_showPopup(self, message, hostIds or [], mode, addTimestamp, displaySeconds)

	def hostControlSafe_uptime(self, hostIds: List[str] = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_uptime(self, hostIds or [])

	def hostControlSafe_getActiveSessions(self, hostIds: List[str] = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_getActiveSessions(self, hostIds or [])

	def hostControlSafe_opsiclientdRpc(
		self, method: str, params: List = None, hostIds: List[str] = None, timeout: int = None
	) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_opsiclientdRpc(self, method, params or [], hostIds or [], timeout)

	def hostControlSafe_reachable(self, hostIds: List[str] = None, timeout: int = None) -> Dict[str, Any]:
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_reachable(self, hostIds or [], timeout)

	def hostControlSafe_execute(  # pylint: disable=too-many-arguments
		self,
		command: str,
		hostIds: List[str] = None,
		waitForEnding: bool = True,
		captureStderr: bool = True,
		encoding: str = None,
		timeout: int = 300,
	):
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_execute(self, command, hostIds or [], waitForEnding, captureStderr, encoding, timeout)
