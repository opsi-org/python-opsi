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
import grp
import pwd
import os
import pam

from OPSI.Backend.Manager.Authentication import AuthenticationModule
from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Logger import Logger
from OPSI.System.Posix import isRHEL, isCentOS, isOpenSUSE, isSLES
from OPSI.Types import forceUnicode

logger = Logger()


class PAMAuthentication(AuthenticationModule):
	def __init__(self, pam_service: str = None):
		self._pam_service = pam_service
		if not self._pam_service:
			if os.path.exists("/etc/pam.d/opsi-auth"):
				# Prefering our own - if present.
				self._pam_service = 'opsi-auth'
			elif isSLES() or isOpenSUSE():
				self._pam_service = 'sshd'
			elif isCentOS() or isRHEL():
				self._pam_service = 'system-auth'
			else:
				self._pam_service = 'common-auth'
	
	def authenticate(self, username: str, password: str) -> None:
		'''
		Authenticate a user by PAM (Pluggable Authentication Modules).
		Important: the uid running this code needs access to /etc/shadow
		if os uses traditional unix authentication mechanisms.

		:param service: The PAM service to use. Leave None for autodetection.
		:type service: str
		:raises BackendAuthenticationError: If authentication fails.
		'''
		logger.confidential("Trying to authenticate user %s with password %s by PAM", username, password)
		logger.debug2("Attempting PAM authentication as user %s (service=%s)...", username, self._pam_service)

		try:
			auth = pam.pam()
			if not auth.authenticate(username, password, service=self._pam_service):
				logger.debug2("PAM authentication failed: %s (code %s)", auth.reason, auth.code)
				raise RuntimeError(auth.reason)

			logger.debug2("PAM authentication successful.")
		except Exception as error:
			raise BackendAuthenticationError("PAM authentication failed for user '%s': %s" % (username, error))

	def get_groupnames(self, username: str) -> Set[str]:
		"""
		Read the groups of a user.

		:returns: Group the user is a member of.
		:rtype: set()
		"""
		logger.debug("Reading groups of user %s...", username)
		primary_group = forceUnicode(grp.getgrgid(pwd.getpwnam(username)[3])[0])
		logger.debug("Primary group of user %s is %s", username, primary_group)

		groups = set(forceUnicode(group[0]) for group in grp.getgrall() if group[0] and username in group[3])
		if primary_group:
			groups.add(primary_group)
		logger.debug("User %s is member of groups: %s", username, groups)
		return groups
