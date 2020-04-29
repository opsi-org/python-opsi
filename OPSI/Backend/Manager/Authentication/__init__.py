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
Authentication helper.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from typing import Set, List

from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Util.File.Opsi import OpsiConfFile
from OPSI.Logger import Logger

logger = Logger()

class AuthenticationModule:
	def __init__(self):
		pass
	
	def authenticate(self, username: str, password: str) -> None:
		raise BackendAuthenticationError("Not implemented")

	def get_groupnames(self, username: str) -> Set[str]:
		return set()
	
	def get_admin_groupname(self) -> str:
		return OPSI_ADMIN_GROUP
	
	def get_read_only_groupnames(self) -> Set[str]:
		return set(OpsiConfFile().getOpsiGroups('readonly') or [])
	
	def user_is_admin(self, username: str) -> bool:
		return self.get_admin_groupname() in self.get_groupnames(username)
	
	def user_is_read_only(self, username: str, forced_user_groupnames: Set[str] = None) -> bool:
		user_groupnames = set()
		if forced_user_groupnames is None:
			user_groupnames = self.get_groupnames(username)
		else:
			user_groupnames = forced_user_groupnames
		
		read_only_groupnames = self.get_read_only_groupnames()
		for group_name in user_groupnames:
			if group_name in read_only_groupnames:
				return True
		return False
	