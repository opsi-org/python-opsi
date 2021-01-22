# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org
# Copyright (C) 2018 uib GmbH <info@uib.de>

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
PAM authentication.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from typing import Set
# pyright: reportMissingImports=false
import win32net  # pylint: disable=import-error
import win32security  # pylint: disable=import-error

from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Backend.Manager.Authentication import AuthenticationModule
from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Logger import Logger

logger = Logger()


class NTAuthentication(AuthenticationModule):
	def __init__(self, admin_group_sid: str = None):
		super().__init__()
		self._admin_group_sid = admin_group_sid
		self._admin_groupname = OPSI_ADMIN_GROUP
		if self._admin_group_sid is not None:
			try:
				self._admin_groupname = win32security.LookupAccountSid(
					None, win32security.ConvertStringSidToSid(self._admin_group_sid)
				)[0]
			except Exception as err:  # pylint: disable=broad-except
				logger.error("Failed to lookup group with sid '%s': %s", self._admin_group_sid, err)

	def get_instance(self):
		return NTAuthentication(self._admin_group_sid)

	def authenticate(self, username: str, password: str) -> None:
		'''
		Authenticate a user by Windows-Login on current machine

		:raises BackendAuthenticationError: If authentication fails.
		'''
		logger.confidential("Trying to authenticate user %s with password %s by win32security", username, password)

		try:
			win32security.LogonUser(
				username, 'None', password,
				win32security.LOGON32_LOGON_NETWORK, win32security.LOGON32_PROVIDER_DEFAULT
			)
		except Exception as err:  # pylint: disable=broad-except
			raise BackendAuthenticationError(
				f"Win32security authentication failed for user '{username}': {err}"
			) from err

	def get_admin_groupname(self) -> str:
		return self._admin_groupname

	def get_groupnames(self, username: str) -> Set[str]:
		"""
		Read the groups of a user.

		:returns: List og group names the user is a member of.
		:rtype: set()
		"""
		collected_groupnames = set()

		gresume = 0
		while True:
			(groups, gtotal, gresume) = win32net.NetLocalGroupEnum(None, 0, gresume)
			logger.trace("Got %s groups, total=%s, resume=%s", len(groups), gtotal, gresume)
			for groupname in (u['name'] for u in groups):
				logger.trace("Found group '%s'", groupname)
				uresume = 0
				while True:
					(users, utotal, uresume) = win32net.NetLocalGroupGetMembers(None, groupname, 0, uresume)
					logger.trace("Got %s users, total=%s, resume=%s", len(users), utotal, uresume)
					for sid in (u['sid'] for u in users):
						(group_username, _domain, _group_type) = win32security.LookupAccountSid(None, sid)
						if group_username.lower() == username.lower():
							collected_groupnames.add(groupname)
							logger.debug("User %s is member of group %s", username, groupname)
					if uresume == 0:
						break
			if gresume == 0:
				break

		return collected_groupnames
