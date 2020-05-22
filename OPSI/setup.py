# -*- coding: utf-8 -*-

# This file is part of opsi.
# Copyright (C) 2020 uib GmbH <info@uib.de>

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
:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""

import os
import pwd
import grp
import subprocess

from OPSI.Config import OPSI_ADMIN_GROUP, FILE_ADMIN_GROUP, DEFAULT_DEPOT_USER

from .logging import logger
from .config import config

def create_group(groupname: str, system: bool = False):
	logger.notice("Creating group: {0}", groupname)
	cmd = ["groupadd"]
	if system:
		cmd.append("--system")
	cmd.append(groupname)
	logger.info("Running command: {0}", cmd)
	subprocess.check_call(cmd)

def create_user(username: str, primary_groupname: str, home: str, shell: str, system: bool = False):
	logger.notice("Creating user: {0}", username)
	cmd = ["useradd", "-g", primary_groupname, "-d", home, "-s", shell]
	if system:
		cmd.append("--system")
	cmd.append(username)
	logger.info("Running command: {0}", cmd)
	subprocess.check_call(cmd)

def add_user_to_group(username: str, groupname: str):
	logger.notice("Adding user '{0}' to group '{1}'", username, groupname)
	cmd = ["usermod", "-a", "-G", groupname, username]
	logger.info("Running command: {0}", cmd)
	subprocess.check_call(cmd)

def get_groups():
	groups = {}
	for group in grp.getgrall():
		groups[group.gr_name] = group
	return groups

def get_users():
	users = {}
	for user in pwd.getpwall():
		users[user.pw_name] = user
	return users

def setup_users_and_groups():
	groups = get_groups()
	users = get_users()
	
	if OPSI_ADMIN_GROUP not in groups:
		create_group(
			groupname=OPSI_ADMIN_GROUP,
			system=False
		)
		groups = get_groups()
	
	if FILE_ADMIN_GROUP not in groups:
		create_group(
			groupname=FILE_ADMIN_GROUP,
			system=True
		)
		groups = get_groups()
	
	if DEFAULT_DEPOT_USER not in users:
		create_user(
			username=DEFAULT_DEPOT_USER,
			primary_groupname=FILE_ADMIN_GROUP,
			home="/var/lib/opsi",
			shell="/bin/bash",
			system=True
		)
		users = get_users()

def setup_file_permissions():
	groups = get_groups()
	if "shadow" in groups:
		os.chown(path="/etc/shadow", uid=0, gid=groups["shadow"].gr_gid)
		os.chmod(path="/etc/shadow", mode=0o640)

def setup():
	logger.notice("Running setup")
	setup_users_and_groups()
	setup_file_permissions()
