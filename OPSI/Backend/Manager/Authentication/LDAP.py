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

:author: Jan Schneider <j.schneider@uib.de>
:license: GNU Affero General Public License version 3
"""

from typing import Set
import ldap3

from OPSI.Backend.Manager.Authentication import AuthenticationModule
from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Logger import Logger

logger = Logger()


class LDAPAuthentication(AuthenticationModule):
	def __init__(self, ldap_url: str, base_dn: str, realm: str):
		self._ldap_url = ldap_url
		self._base_dn = base_dn
		self._realm = realm
		self._ldap = None
	
	def authenticate(self, username: str, password: str) -> None:
		self._ldap = None
		try:
			logger.info("Connecting to ldap server '%s'", self._ldap_url)
			self._ldap = ldap3.Connection(server=self._ldap_url, user=f"{username}@{self._realm}", password=password)
			if not self._ldap.bind():
				raise Exception("bind failed: %s" % self._ldap.result)
		except Exception as error:
			raise BackendAuthenticationError("LDAP authentication failed for user '%s': %s" % (username, error))

	def get_groupnames(self, username: str) -> Set[str]:
		groupnames = set()
		if not self._ldap:
			return groupnames
		
		self._ldap.search(self._base_dn, "(objectclass=group)", search_scope = ldap3.SUBTREE, attributes=["cn", "member"])
		for entry in sorted(self._ldap.entries):
			if not "member" in entry.entry_attributes:
				continue
			for member in entry.member:
				if member.split(',')[0].split('=', 1)[1].lower() == username.lower():
					groupnames.add(entry.cn.value)
					break
		return groupnames
