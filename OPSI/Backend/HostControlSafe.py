# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

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
HostControl Backend: Safe edition

:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
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

	def hostControlSafe_start(self, hostIds=[]):
		''' Switches on remote computers using WOL. '''
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_start(self, hostIds)

	def hostControlSafe_shutdown(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_shutdown(self, hostIds)

	def hostControlSafe_reboot(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_reboot(self, hostIds)


	def hostControlSafe_fireEvent(self, event, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_fireEvent(self, event, hostIds)

	def hostControlSafe_showPopup(self, message, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_showPopup(self, message, hostIds)

	def hostControlSafe_uptime(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_uptime(self, hostIds)

	def hostControlSafe_getActiveSessions(self, hostIds=[]):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_getActiveSessions(self, hostIds)

	def hostControlSafe_opsiclientdRpc(self, method, params=[], hostIds=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_opsiclientdRpc(self, method, params, hostIds, timeout)
	
	def hostControlSafe_reachable(self, hostIds=[], timeout=None):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_reachable(self, hostIds, timeout)

	def hostControlSafe_execute(self, command, hostIds=[], waitForEnding=True, captureStderr=True, encoding=None, timeout=300):
		if not hostIds:
			raise BackendMissingDataError(u"No matching host ids found")
		return HostControlBackend.hostControl_execute(self, command, hostIds, waitForEnding, captureStderr, encoding, timeout)
