# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os
import platform
from pathlib import Path

import pytest

from opsi.opsi.service.server import DirPermission, FilePermission, PermissionRegistry, set_rights
from opsi.testing.helper import opsi_config

if platform.system().lower() == "linux":
	import grp
	import pwd


@pytest.fixture
def some_secondary_group_name() -> str:
	user_id = os.getuid()
	user = pwd.getpwuid(user_id)
	primary_gid = user.pw_gid
	for gid in os.getgrouplist(user.pw_name, primary_gid):
		if gid != primary_gid:
			return grp.getgrgid(gid).gr_name
	pytest.skip("No group for test found. Aborting.")
	return ""


@pytest.mark.linux
def test_permission_registry() -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()

		permission_count = len(registry.permissions)
		assert permission_count > 0

		registry.remove_permissions()
		assert len(registry.permissions) == 0

		registry.register_permission(DirPermission("/tmp", None, None, 0o600, 0o700, recursive=True))
		assert len(registry.permissions) == 1

		registry.register_default_permissions()
		assert len(registry.permissions) == permission_count + 1

		registry.register_permission(DirPermission("/tmp", None, None, 0o600, 0o700, recursive=True))
		assert len(registry.permissions) == permission_count + 1

		registry.reinit()
		assert len(registry.permissions) == permission_count


@pytest.mark.linux
def test_permission_registry_set_opsiconfd_user_reinitializes_default_permissions() -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()
		registry.set_opsiconfd_user("custom-opsiconfd")

		assert registry.permissions["/etc/opsi"].username == "custom-opsiconfd"
		assert registry.permissions["/var/log/opsi"].username == "custom-opsiconfd"
		assert registry.permissions["/var/lib/opsi"].username == "custom-opsiconfd"


@pytest.mark.linux
def test_set_rights_recursive(tmp_path: Path, some_secondary_group_name: str) -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()

		user_id = os.getuid()
		user = pwd.getpwuid(user_id)
		primary_gid = user.pw_gid
		username = user.pw_name
		some_secondary_group_id = grp.getgrnam(some_secondary_group_name).gr_gid

		dir1 = os.path.join(tmp_path, "dir1")
		fil1 = os.path.join(dir1, "fil1")
		fil2 = os.path.join(dir1, "fil2")
		dir2 = os.path.join(dir1, "dir2")
		fil3 = os.path.join(dir2, "fil3")
		fil4 = os.path.join(dir2, "fil4")
		dir3 = os.path.join(dir1, "dir3")
		fil5 = os.path.join(dir3, "fil5")
		fil6 = os.path.join(dir3, "fil6")
		fil7 = os.path.join(dir3, "fil7")
		dir4 = os.path.join(dir2, "dir4")

		for path in (dir1, dir2, dir3, dir4):
			os.mkdir(path)
			os.chmod(path, 0o707)
		for path in (fil1, fil2, fil3, fil4, fil5, fil6, fil7):
			open(path, "wb").close()
			os.chmod(path, 0o606)

		for permission in (
			DirPermission(dir1, username, some_secondary_group_name, 0o666, 0o777, recursive=True),
			DirPermission(dir2, None, None, 0o600, 0o700, recursive=True),
			FilePermission(fil1, None, None, 0o660),
			FilePermission(fil6, None, None, 0o660),
			FilePermission(fil7, username, some_secondary_group_name, 0o606),
		):
			registry.register_permission(permission)

		set_rights(dir1)

		for path in (dir1, dir2, dir3, dir4, fil1, fil2, fil3, fil4, fil5, fil6, fil7):
			assert os.stat(path).st_uid == user_id

		for path in (dir1, dir3, fil2, fil5, fil7):
			assert os.stat(path).st_gid == some_secondary_group_id
		for path in (dir2, dir4, fil1, fil3, fil4, fil6):
			assert os.stat(path).st_gid == primary_gid

		assert os.stat(dir1).st_mode & 0o7777 == 0o777
		assert os.stat(fil1).st_mode & 0o7777 == 0o660
		assert os.stat(fil2).st_mode & 0o7777 == 0o666
		assert os.stat(dir2).st_mode & 0o7777 == 0o700
		assert os.stat(fil3).st_mode & 0o7777 == 0o600
		assert os.stat(fil4).st_mode & 0o7777 == 0o600
		assert os.stat(dir3).st_mode & 0o7777 == 0o777
		assert os.stat(fil5).st_mode & 0o7777 == 0o666
		assert os.stat(fil6).st_mode & 0o7777 == 0o660
		assert os.stat(fil7).st_mode & 0o7777 == 0o606
		assert os.stat(dir4).st_mode & 0o7777 == 0o700


@pytest.mark.linux
def test_set_rights_modify_file_exe(tmp_path: Path) -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()

		dir1 = os.path.join(tmp_path, "dir1")
		fil1 = os.path.join(dir1, "fil1")
		fil2 = os.path.join(dir1, "fil2")
		fil3 = os.path.join(dir1, "fil3")

		for path in (dir1,):
			os.mkdir(path)
			os.chmod(path, 0o777)
		for path in (fil1, fil2, fil3):
			open(path, "wb").close()
		os.chmod(fil1, 0o666)
		os.chmod(fil2, 0o775)
		os.chmod(fil3, 0o777)

		registry.register_permission(DirPermission(dir1, None, None, 0o666, 0o770, modify_file_exe=False))

		set_rights(dir1)

		assert os.stat(dir1).st_mode & 0o7777 == 0o770
		assert os.stat(fil1).st_mode & 0o7777 == 0o666
		assert os.stat(fil2).st_mode & 0o7777 == 0o777
		assert os.stat(fil3).st_mode & 0o7777 == 0o777

		os.chmod(fil1, 0o666)
		os.chmod(fil2, 0o775)
		os.chmod(fil3, 0o777)

		registry.register_permission(DirPermission(dir1, None, None, 0o660, 0o770, modify_file_exe=False))

		set_rights(dir1)

		assert os.stat(dir1).st_mode & 0o7777 == 0o770
		assert os.stat(fil1).st_mode & 0o7777 == 0o660
		assert os.stat(fil2).st_mode & 0o7777 == 0o770
		assert os.stat(fil3).st_mode & 0o7777 == 0o770

		os.chmod(fil1, 0o666)
		os.chmod(fil2, 0o775)
		os.chmod(fil3, 0o777)

		registry.register_permission(DirPermission(dir1, None, None, 0o660, 0o770, modify_file_exe=True))

		set_rights(dir1)

		assert os.stat(dir1).st_mode & 0o7777 == 0o770
		assert os.stat(fil1).st_mode & 0o7777 == 0o660
		assert os.stat(fil2).st_mode & 0o7777 == 0o660
		assert os.stat(fil3).st_mode & 0o7777 == 0o660


@pytest.mark.linux
def test_set_rights_file_in_dir(tmp_path: Path) -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()
		registry.remove_permissions()

		dir1 = os.path.join(tmp_path, "dir1")
		dir2 = os.path.join(dir1, "dir2")
		fil1 = os.path.join(dir2, "fil1")
		fil2 = os.path.join(dir2, "fil2")

		for path in (dir1, dir2):
			os.mkdir(path)
			os.chmod(path, 0o777)
		for path in (fil1, fil2):
			open(path, "wb").close()
			os.chmod(path, 0o666)

		registry.register_permission(
			DirPermission(dir1, None, None, 0o660, 0o770, recursive=True), DirPermission(dir2, None, None, 0o600, 0o700, recursive=True)
		)

		set_rights(fil1)
		assert os.stat(fil1).st_mode & 0o7777 == 0o600
		assert os.stat(fil2).st_mode & 0o7777 == 0o666

		set_rights(fil2)
		assert os.stat(fil2).st_mode & 0o7777 == 0o600


@pytest.mark.linux
def test_set_rights_link(tmp_path: Path) -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()

		registry.remove_permissions()

		dir1 = os.path.join(tmp_path, "dir1")
		dir2 = os.path.join(dir1, "dir2")
		file1 = os.path.join(dir2, "file1")
		link1 = os.path.join(dir1, "link1")
		link2 = os.path.join(dir1, "link2")

		for path in (dir1, dir2):
			os.mkdir(path)
			os.chmod(path, 0o777)

		# create file1 in dir1
		open(file1, "wb").close()

		os.symlink(dir2, link1)
		os.symlink(file1, link2)
		orig_stat_link1 = os.stat(link1, follow_symlinks=False).st_mode
		orig_stat_link2 = os.stat(link2, follow_symlinks=False).st_mode
		registry.register_permission(DirPermission(dir1, None, None, 0o660, 0o770, recursive=True, modify_file_exe=False))
		registry.register_permission(FilePermission(link2, None, None, 0o660))

		set_rights(dir1)
		assert os.stat(dir1).st_mode & 0o7777 == 0o770
		assert os.stat(dir2).st_mode & 0o7777 == 0o770
		assert os.stat(link1, follow_symlinks=False).st_mode == orig_stat_link1
		assert os.stat(link2, follow_symlinks=False).st_mode == orig_stat_link2
		assert os.stat(file1).st_mode & 0o7777 == 0o660


@pytest.mark.linux
def test_set_rights_excludes(tmp_path: Path) -> None:
	with opsi_config({"groups.admingroup": "opsiadmin", "groups.fileadmingroup": "opsifileadmins", "depot_user.username": "pcpatch"}):
		registry = PermissionRegistry()

		registry.remove_permissions()

		dir1 = os.path.join(tmp_path, "dir1")
		file1 = os.path.join(dir1, "file1")
		file2 = os.path.join(dir1, ".snapshot")

		os.mkdir(dir1)
		os.chmod(dir1, 0o777)
		open(file1, "wb").close()
		open(file2, "wb").close()

		registry.register_permission(DirPermission(dir1, None, None, 0o600, 0o770, modify_file_exe=True))

		set_rights(dir1)
		print(os.stat(file1).st_mode & 0o7777)
		print(os.stat(file2).st_mode & 0o7777)
		assert os.stat(file1).st_mode & 0o7777 == 0o600
		assert os.stat(file2).st_mode & 0o7777 != 0o600
