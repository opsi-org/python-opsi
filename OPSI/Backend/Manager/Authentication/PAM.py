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

import grp
import pwd
import os

import pam

from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Logger import Logger
from OPSI.System.Posix import Distribution
from OPSI.Types import forceUnicode

__all__ = ('authenticate', 'readGroups')

DISTRIBUTOR = Distribution().distributor or 'unknown'

logger = Logger()


def authenticate(username, password, service=None):
	'''
	Authenticate a user by PAM (Pluggable Authentication Modules).
	Important: the uid running this code needs access to /etc/shadow
	if os uses traditional unix authentication mechanisms.

	:param service: The PAM service to use. Leave None for autodetection.
	:type service: str
	:raises BackendAuthenticationError: If authentication fails.
	'''
	logger.confidential(
		u"Trying to authenticate user {0!r} with password {1!r} by PAM",
		username, password
	)

	pamService = service or getPAMService()
	logger.debug2(
		u"Attempting PAM authentication as user {0!r} (service={})...",
		username, pamService
	)
	try:
		# Create instance
		auth = pam.pam()
		auth.start(pamService)
		# Authenticate
		auth.set_item(pam.PAM_CONV, AuthConv(username, password))
		auth.authenticate()
		auth.acct_mgmt()
		logger.debug2("PAM authentication successful.")
	except pam.error as error:
		raise BackendAuthenticationError(u"PAM authentication failed for user '%s': %s" % (username, error))
	except Exception as error:
		raise BackendAuthenticationError(u"PAM authentication failed for user '%s': %s" % (username, error))


def getPAMService():
	"""
	Get the PAM service to use.

	:returns: Name of the service to use.
	:rtype: str
	"""
	if os.path.exists("/etc/pam.d/opsi-auth"):
		# Prefering our own - if present.
		return 'opsi-auth'
	elif 'suse' in DISTRIBUTOR.lower():
		return 'sshd'
	elif 'centos' in DISTRIBUTOR.lower() or 'redhat' in DISTRIBUTOR.lower():
		return 'system-auth'
	else:
		return 'common-auth'


class AuthConv:
	''' Handle PAM conversation '''
	def __init__(self, user, password):
		self.user = user
		self.password = password

	def __call__(self, auth, query_list, userData=None):
		response = []
		for (query, qtype) in query_list:
			logger.debug(u"PAM conversation: query {0!r}, type {1!r}", query, qtype)
			if qtype == pam.PAM_PROMPT_ECHO_ON:
				response.append((self.user, 0))
			elif qtype == pam.PAM_PROMPT_ECHO_OFF:
				response.append((self.password, 0))
			elif qtype in (pam.PAM_ERROR_MSG, pam.PAM_TEXT_INFO):
				response.append(('', 0))
			else:
				return None

		return response


def readGroups(username):
	"""
	Read the groups of a user.

	:returns: Group the user is a member of.
	:rtype: set()
	"""
	logger.debug("Reading groups of user {!r}...", username)
	primaryGroup = forceUnicode(grp.getgrgid(pwd.getpwnam(username)[3])[0])
	logger.debug(u"Primary group of user {0!r} is {1!r}", username, primaryGroup)

	groups = set(forceUnicode(group[0]) for group in grp.getgrall() if username in group[3])
	groups.add(primaryGroup)
	logger.debug(u"User {0!r} is member of groups: {1}", username, groups)

	return groups
