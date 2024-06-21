# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Authentication helper.
"""

from __future__ import annotations

from typing import Self

from opsicommon.logging import get_logger

from OPSI.Config import OPSI_ADMIN_GROUP
from OPSI.Exceptions import BackendAuthenticationError
from OPSI.Util.File.Opsi import OpsiConfFile

logger = get_logger("opsi.general")


class AuthenticationModule:
	def __init__(self) -> None:
		pass

	def get_instance(self) -> Self:
		return self.__class__()

	def authenticate(self, username: str, password: str) -> None:
		raise BackendAuthenticationError("Not implemented")

	def get_groupnames(self, username: str) -> set[str]:  # pylint: disable=unused-argument
		return set()

	def get_admin_groupname(self) -> str:
		return OPSI_ADMIN_GROUP

	def get_read_only_groupnames(self) -> set[str]:
		return set(OpsiConfFile().getOpsiGroups("readonly") or [])

	def user_is_admin(self, username: str) -> bool:
		return self.get_admin_groupname() in self.get_groupnames(username)

	def user_is_read_only(self, username: str, forced_user_groupnames: set[str] = None) -> bool:
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
