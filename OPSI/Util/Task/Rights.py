# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2014-2019 uib GmbH - http://www.uib.de/

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
Setting access rights for opsi.

Opsi needs different access rights and ownerships for files and folders
during its use. To ease the setting of these permissions this modules
provides helpers for this task.

:copyright:  uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""

import grp
import os
import pwd
import stat
from dataclasses import dataclass
from functools import lru_cache

from OPSI.Config import (
	FILE_ADMIN_GROUP, OPSI_ADMIN_GROUP, DEFAULT_DEPOT_USER, DEFAULT_DEPOT_USER_HOME, OPSICONFD_USER
)
from OPSI.Logger import Logger
from OPSI.System.Posix import (
	getLocalFqdn, isCentOS, isOpenSUSE, isRHEL, isSLES, isUCS
)
from OPSI.Backend.Base.ConfigData import OPSI_PASSWD_FILE

from opsicommon.utils import Singleton

logger = Logger()

_HAS_ROOT_RIGHTS = os.geteuid() == 0

@dataclass
class FilePermission:
	path: str
	username: str
	groupname: str
	file_permissions: int

	@staticmethod
	@lru_cache(maxsize=None)
	def username_to_uid(username: str) -> int:
		return pwd.getpwnam(username)[2]

	@staticmethod
	@lru_cache(maxsize=None)
	def groupname_to_gid(groupname: str) -> int:
		return grp.getgrnam(groupname)[2]

	@property
	def uid(self) -> int:
		if not self.username:
			return -1
		return self.username_to_uid(self.username)

	@property
	def gid(self) -> int:
		if not self.groupname:
			return -1
		return self.groupname_to_gid(self.groupname)

	def chmod(self, path, stat_res=None):
		stat_res = stat_res or os.stat(path, follow_symlinks=False)
		cur_mode = stat_res.st_mode & 0o7777
		if cur_mode != self.file_permissions:
			logger.trace("%s: %o != %o", path, cur_mode, self.file_permissions)
			os.chmod(path, self.file_permissions, follow_symlinks=not stat.S_ISLNK(stat_res.st_mode))

	def chown(self, path, stat_res=None):
		stat_res = stat_res or os.stat(path, follow_symlinks=False)
		if self.uid not in (-1, stat_res.st_uid) or self.gid not in (-1, stat_res.st_gid):
			logger.trace("%s: %d:%d != %d:%d", path, stat_res.st_uid, stat_res.st_gid, self.uid, self.gid)
			# Unprivileged user cannot change file owner
			uid = self.uid if _HAS_ROOT_RIGHTS else -1
			os.chown(path, uid, self.gid, follow_symlinks=not stat.S_ISLNK(stat_res.st_mode))

	def apply(self, path):
		stat_res = os.stat(path, follow_symlinks=False)
		self.chmod(path, stat_res)
		self.chown(path, stat_res)


@dataclass
class DirPermission(FilePermission):
	dir_permissions: int
	recursive: bool = True
	correct_links: bool = False
	modify_file_exe: bool = True

	def chmod(self, path, stat_res=None):
		stat_res = stat_res or os.stat(path, follow_symlinks=False)
		if stat.S_ISLNK(stat_res.st_mode) and not self.correct_links:
			return

		cur_mode = stat_res.st_mode & 0o7777
		new_mode = self.file_permissions
		if stat.S_ISDIR(stat_res.st_mode):
			new_mode = self.dir_permissions
		elif stat.S_ISREG(stat_res.st_mode) and not self.modify_file_exe:
			# Do not modify executable flag
			if cur_mode & 0o100 and new_mode & 0o400:
				# User: executable bit currently set and new mode readable
				new_mode |= 0o100
			if cur_mode & 0o010 and new_mode & 0o040:
				# Group: executable bit currently set and new mode readable
				new_mode |= 0o010
			if cur_mode & 0o001 and new_mode & 0o004:
				# Other: executable bit currently set and new mode readable
				new_mode |= 0o001

		if cur_mode != new_mode:
			logger.trace("%s: %o != %o", path, cur_mode, new_mode)
			os.chmod(path, new_mode, follow_symlinks=not stat.S_ISLNK(stat_res.st_mode))

	def chown(self, path, stat_res=None):
		stat_res = stat_res or os.stat(path, follow_symlinks=False)
		if stat.S_ISLNK(stat_res.st_mode) and not self.correct_links:
			return None
		return super().chown(path, stat_res)

def _get_default_depot_user_ssh_dir():
	return os.path.join(DEFAULT_DEPOT_USER_HOME, ".ssh")

class PermissionRegistry(metaclass=Singleton):
	def __init__(self):
		self._permissions = {}
		self.reinit()

	def reinit(self):
		self._permissions = {}
		self.register_default_permissions()

	def register_permission(self, *permission: DirPermission):
		for perm in permission:
			self._permissions[perm.path] = perm

	def remove_permissions(self):
		self._permissions = {}

	@property
	def permissions(self):
		return self._permissions

	#def get_permissions(self, start_path="/"):
	#	for path in sorted(self._permissions):
	#		if path.startswith(start_path):
	#			yield self._permissions[path]

	def register_default_permissions(self):
		self.register_permission(
			DirPermission("/etc/opsi", OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o660, 0o770),
			#FilePermission("/etc/opsi/modules", OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o660),
			DirPermission("/var/log/opsi", OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o660, 0o770),
			DirPermission("/var/lib/opsi", OPSICONFD_USER, FILE_ADMIN_GROUP, 0o660, 0o770),
			#FilePermission(OPSI_PASSWD_FILE, OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o660),
		)
		self.register_permission(
			DirPermission("/etc/opsi/ssl", OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o600, 0o750),
			FilePermission("/etc/opsi/ssl/opsi-ca-cert.pem", OPSICONFD_USER, OPSI_ADMIN_GROUP, 0o644)
		)
		depot_dirs = getDepotDirectories()
		self.register_permission(
			DirPermission(depot_dirs["depot"], OPSICONFD_USER, FILE_ADMIN_GROUP, 0o660, 0o2770, modify_file_exe=False),
			DirPermission(depot_dirs["repository"], OPSICONFD_USER, FILE_ADMIN_GROUP, 0o660, 0o2770),
			DirPermission(depot_dirs["workbench"], OPSICONFD_USER, FILE_ADMIN_GROUP, 0o660, 0o2770, modify_file_exe=False)
		)

		pxe_dir = getPxeDirectory()
		if pxe_dir:
			self.register_permission(
				DirPermission(pxe_dir, OPSICONFD_USER, FILE_ADMIN_GROUP, 0o664, 0o775)
			)

		webserver_dir = getWebserverRepositoryPath()
		if webserver_dir:
			username, groupname = getWebserverUsernameAndGroupname()
			self.register_permission(
				DirPermission(webserver_dir, username, groupname, 0o664, 0o775)
			)

		ssh_dir = _get_default_depot_user_ssh_dir()
		self.register_permission(
			DirPermission(ssh_dir, DEFAULT_DEPOT_USER, FILE_ADMIN_GROUP, 0o640, 0o750, recursive=False),
			FilePermission(os.path.join(ssh_dir, 'id_rsa'), DEFAULT_DEPOT_USER, FILE_ADMIN_GROUP, 0o640),
			FilePermission(os.path.join(ssh_dir, 'id_rsa.pub'), DEFAULT_DEPOT_USER, FILE_ADMIN_GROUP, 0o644),
			FilePermission(os.path.join(ssh_dir, 'authorized_keys'), DEFAULT_DEPOT_USER, FILE_ADMIN_GROUP, 0o600)
		)

def setRightsOnSSHDirectory(userId=None, groupId=None, path=_get_default_depot_user_ssh_dir()):
	if not os.path.exists(path):
		raise FileNotFoundError(f"Path '{path}' not found")

	username = DEFAULT_DEPOT_USER
	groupname = FILE_ADMIN_GROUP

	if userId is not None:
		username = pwd.getpwuid(userId).pw_name
	if groupId is not None:
		groupname = grp.getgrgid(groupId).gr_name

	PermissionRegistry().register_permission(
		DirPermission(path, username, groupname, 0o640, 0o750, recursive=False),
		FilePermission(os.path.join(path, 'id_rsa'), username, groupname, 0o640),
		FilePermission(os.path.join(path, 'id_rsa.pub'), username, groupname, 0o644),
		FilePermission(os.path.join(path, 'authorized_keys'), username, groupname, 0o600)
	)
	set_rights()

def set_rights(start_path='/'):  # pylint: disable=too-many-branches
	logger.debug("Setting rights on %s", start_path)
	permissions = PermissionRegistry().permissions
	permissions_to_process = []
	parent = None
	for path in sorted(list(permissions)):
		if not os.path.relpath(path, start_path).startswith(".."):
			# Sub path of start_path
			permissions_to_process.append(permissions[path])
		elif not os.path.relpath(start_path, path).startswith(".."):
			if not parent or len(parent.path) < len(path):
				parent = permissions[path]

	if not permissions_to_process and parent:
		logger.notice("Setting rights on '%s'", start_path)
		parent.apply(start_path)

	for permission in permissions_to_process:
		if not os.path.lexists(permission.path):
			continue

		recursive = os.path.isdir(permission.path) and getattr(permission, "recursive", True)

		logger.notice("Setting rights %son '%s'", "recursively " if recursive else "", permission.path)
		permission.apply(permission.path)

		if not recursive:
			continue

		for root, dirs, files in os.walk(permission.path, topdown=True):
			#logger.debug("Processing '%s'", root)
			for name in files:
				abspath = os.path.join(root, name)
				if abspath in permissions:
					continue
				if not permission.modify_file_exe and os.path.islink(abspath):
					continue
				permission.apply(abspath)

			remove_dirs = []
			for name in dirs:
				abspath = os.path.join(root, name)
				if abspath in permissions:
					remove_dirs.append(name)
					continue
				permission.apply(abspath)

			if remove_dirs:
				for name in remove_dirs:
					dirs.remove(name)

def setRights(path="/"):
	# Deprecated
	return set_rights(path)

def setPasswdRights():
	"""
	Setting correct permissions on ``/etc/opsi/passwd``.
	"""
	return set_rights(OPSI_PASSWD_FILE)

CACHED_DEPOT_DIRS = {}
def getDepotDirectories():
	global CACHED_DEPOT_DIRS  # pylint: disable=global-statement
	if not CACHED_DEPOT_DIRS:
		CACHED_DEPOT_DIRS = {
			"depot": "/var/lib/opsi/depot",
			"repository": "/var/lib/opsi/repository",
			"workbench": "/var/lib/opsi/workbench"
		}
		try:
			from OPSI.Backend.BackendManager import BackendManager  # pylint: disable=import-outside-toplevel
			with BackendManager() as backend:
				depot = backend.host_getObjects(type='OpsiDepotserver', id=getLocalFqdn())[0]
				for name, url in (
					("depot", depot.getDepotLocalUrl()),
					("repository", depot.getRepositoryLocalUrl()),
					("workbench", depot.getWorkbenchLocalUrl())
				):
					if url.startswith('file:///'):
						CACHED_DEPOT_DIRS[name] = url[7:]
		except IndexError:
			logger.warning("Failed to get directories from depot: No depots found")
		except Exception as err:  # pylint: disable=broad-except
			logger.warning("Failed to get directories from depot: %s", err)
	return CACHED_DEPOT_DIRS

def getDepotDirectory():
	return getDepotDirectories()["depot"]

def getRepositoryDirectory():
	return getDepotDirectories()["repository"]

def getWorkbenchDirectory():
	return getDepotDirectories()["workbench"]

def getPxeDirectory():
	if isSLES() or isOpenSUSE():
		return '/var/lib/tftpboot/opsi'
	return '/tftpboot/linux'

def getWebserverRepositoryPath():
	"""
	Returns the path to the directory where packages for Linux netboot installations may be.

	On an unsuported distribution or without the relevant folder
	existing `None` will be returned.
	"""
	if isUCS():
		return '/var/www/opsi'
	if isOpenSUSE() or isSLES():
		return '/srv/www/htdocs/opsi'
	return '/var/www/html/opsi'

def getWebserverUsernameAndGroupname():
	'''
	Returns the name of the user and group belonging to the webserver in the default configuration.

	:raises RuntimeError: If running on an Unsupported distribution.
	'''
	if isOpenSUSE() or isSLES():
		return 'wwwrun', 'www'
	if isCentOS() or isRHEL():
		return 'apache', 'apache'
	return 'www-data', 'www-data'
