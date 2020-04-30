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
	def __init__(self, ldap_url: str, bind_user: str = None, group_filter: str = None):
		"""
		Authentication module using LDAP.

		This can be used to authenticate users against OpenLDAP
		or an Active Directory server.

		:param ldap_url: The ldap connection url.
		:param bind_user: (optional) The simple bind is performed with this user.
			The ``bind_user`` has to contain the placeholder ``{username}`` which will be
			replaced by the username auth autenticating user.
			The placeholder ``{base}`` will be replaced by the base dn.
			For active directory ``{username}@your.realm`` should work.
			For OpenLDAP a dn like ``uid={username},ou=Users,{base}`` should be used.
			If ommitted the bind_user will be guessed.
		:param group_filter: (optional) The filter which is used when searching groups.
		Examples::
			>>> active_directory_auth = LDAPAuthentication("ldaps://ad.company.de/dc=company,dc=de", "{username}@company.de")
			>>> open_ldap_auth = LDAPAuthentication("ldap://ldap.company.de/dc=company,dc=de", "uid={username},dc=Users,{base}")
		"""
		self._uri = ldap3.utils.uri.parse_uri(ldap_url)
		self._bind_user = bind_user
		self._group_filter = group_filter
		self._ldap = None
		if self._bind_user is None:
			if self._uri["base"]:
				realm = '.'.join([dc.split('=')[1] for dc in self._uri["base"].split(",")])
			else:
				realm = self._uri["host"]
			self._bind_user = "{username}@" + realm
	
	@property
	def server_url(self):
		url = self._uri["host"]
		if self._uri["port"]:
			url = url + ":" + str(self._uri["port"])
		if self._uri["ssl"]:
			url = "ldaps://" + url
		else:
			url = "ldap://" + url
		return url
	
	def authenticate(self, username: str, password: str) -> None:
		"""
		Authenticate a user by LDAP bind

		:raises BackendAuthenticationError: If authentication fails.
		"""
		self._ldap = None
		try:
			bind_user = self._bind_user.replace("{username}", username).replace("{base}", self._uri["base"])
			logger.debug("Binding as user %s to server %s", bind_user, self.server_url)
			self._ldap = ldap3.Connection(server=self.server_url, user=bind_user, password=password)
			if not self._ldap.bind():
				raise Exception("bind failed: %s" % self._ldap.result)
		except Exception as error:
			raise BackendAuthenticationError("LDAP authentication failed for user '%s': %s" % (username, error))
	
	def get_groupnames(self, username: str) -> Set[str]:
		groupnames = set()
		if not self._ldap:
			return groupnames
		
		group_filter = [self._group_filter]
		if self._group_filter is None:
			group_filter = ["(objectclass=group)", "(objectclass=posixGroup)"]
		
		for i, gf in enumerate(group_filter):
			try:
				self._ldap.search(self._uri["base"], gf, search_scope=ldap3.SUBTREE, attributes=["cn", "member", "memberUid"])
				break
			except ldap3.core.exceptions.LDAPObjectClassError as e:
				if i + 1 == len(group_filter):
					raise
				logger.debug(e)
		
		for entry in sorted(self._ldap.entries):
			if "member" in entry.entry_attributes:
				for member in entry.member:
					if member.split(',')[0].split('=', 1)[1].lower() == username.lower():
						groupnames.add(entry.cn.value)
						break
			if "memberUid" in entry.entry_attributes:
				for member in entry.memberUid:
					if member.lower() == username.lower():
						groupnames.add(entry.cn.value)
						break
		return groupnames
