# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
HostControl Backend: Safe edition
"""

from OPSI.Backend.HostControl import HostControlBackend
from OPSI.Exceptions import BackendMissingDataError

__all__ = ('HostControlSafeBackend', )

class HostControlSafeBackend(HostControlBackend):
	"""
	This backend is the same as the HostControl-backend but it will not
	allow to call methods without hostId
	"""

	def __init__(self, backend, **kwargs):
		self._name = 'hostcontrolsafe'
		HostControlBackend.__init__(self, backend, **kwargs)

	def hostControlSafe_start(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		''' Switches on remote computers using WOL. '''
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_start(self, hostIds)

	def hostControlSafe_shutdown(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_shutdown(self, hostIds)

	def hostControlSafe_reboot(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_reboot(self, hostIds)


	def hostControlSafe_fireEvent(self, event, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_fireEvent(self, event, hostIds)

	def hostControlSafe_showPopup(self, message, hostIds=[], displaySeconds=-1):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_showPopup(self, message, hostIds, displaySeconds)

	def hostControlSafe_uptime(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_uptime(self, hostIds)

	def hostControlSafe_getActiveSessions(self, hostIds=[]):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_getActiveSessions(self, hostIds)

	def hostControlSafe_opsiclientdRpc(self, method, params=[], hostIds=[], timeout=None):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_opsiclientdRpc(self, method, params, hostIds, timeout)

	def hostControlSafe_reachable(self, hostIds=[], timeout=None):  # pylint: disable=dangerous-default-value
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_reachable(self, hostIds, timeout)

	def hostControlSafe_execute(self, command, hostIds=[], waitForEnding=True, captureStderr=True, encoding=None, timeout=300):  # pylint: disable=dangerous-default-value,too-many-arguments
		if not hostIds:
			raise BackendMissingDataError("No matching host ids found")
		return HostControlBackend.hostControl_execute(self, command, hostIds, waitForEnding, captureStderr, encoding, timeout)
