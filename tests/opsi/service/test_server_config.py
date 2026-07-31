# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path
from textwrap import dedent
from time import sleep
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from opsi.opsi.service.server._config import DEFAULT_OPSICONFD_USER, OpsiConfig, get_opsiconfd_user
from opsi.testing.helper import environment


def test_upgrade_config_from_ini(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	data = """
	[groups]
	fileadmingroup = opsifileadmins
	#fileadmingroup = DOMAIN\\\\commented
	admingroup = DOMAIN\\opsiadmin

	[packages]
	use_pigz = True

	[ldap_auth]
	# Active Directory / Samba 4
	ldap_url = ldaps://ad.opsi.test/dc=ad,dc=opsi,dc=test
	"""
	data = dedent(data)
	config_file.write_text(data, encoding="utf-8", newline="")
	config = OpsiConfig()
	config.upgrade_config_file()
	new_data = config_file.read_text(encoding="utf-8")
	assert (
		dedent(
			"""
	[groups]
	fileadmingroup = "opsifileadmins"
	#fileadmingroup = "DOMAIN\\\\commented"
	admingroup = "DOMAIN\\\\opsiadmin"

	[packages]
	use_pigz = true

	[ldap_auth]
	# Active Directory / Samba 4
	ldap_url = "ldaps://ad.opsi.test/dc=ad,dc=opsi,dc=test"
	"""
		).strip()
		in new_data
	)


def test_fill_from_legacy_config_depotserver(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	dispatch_conf = tmp_path / "dispatch.conf"
	jsonrpc_conf = tmp_path / "jsonrpc.conf"

	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	config = OpsiConfig()

	dispatch_conf.write_text("# comment\n.* : jsonrpc\n", encoding="utf-8", newline="")
	jsonrpc_conf.write_text(
		dedent(
			"""
	module = 'JSONRPC'
	config = {
		"username" : "depot.opsi.test",
		"password" : "9a264fbe53fc58dd65030c1bd23983fa",
		"address" : "config.opsi.test"
	}
	"""
		),
		encoding="utf-8",
		newline="",
	)
	with (
		patch("opsi.opsi.service.server._config.DISPATCH_CONF", str(dispatch_conf)),
		patch("opsi.opsi.service.server._config.JSONRPC_CONF", str(jsonrpc_conf)),
	):
		assert config.get("host", "server-role") == "depotserver"
		assert config.get("host", "id") == "depot.opsi.test"
		assert config.get("host", "key") == "9a264fbe53fc58dd65030c1bd23983fa"
		assert config.get("service", "url") == "https://config.opsi.test:4447"


def test_fill_from_legacy_config_configserver(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	dispatch_conf = tmp_path / "dispatch.conf"
	mysql_conf = Path("tests/data/opsi-config/backends/mysql.conf")
	global_conf = tmp_path / "global.conf"

	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	config = OpsiConfig()

	dispatch_conf.write_text(".* : mysql\n", encoding="utf-8", newline="")
	with (
		patch("opsi.opsi.service.server._config.DISPATCH_CONF", str(dispatch_conf)),
		patch("opsi.opsi.service.server._config.MYSQL_CONF", str(mysql_conf)),
		patch("opsi.opsi.service.server._config.GLOBAL_CONF", str(global_conf)),
	):
		assert config.get("host", "server-role") == "configserver"
		assert config.get("host", "id")
		assert config.get("service", "url") == "https://localhost:4447"

		config_file.write_bytes(b"")
		OpsiConfig.reset_singleton()
		config = OpsiConfig()
		global_conf.write_text("\n\n hostname =  config.server.id \n\n", encoding="utf-8", newline="")
		assert config.get("host", "id") == "config.server.id"

		config_file.write_bytes(b"")
		OpsiConfig.reset_singleton()
		config = OpsiConfig()
		global_conf.write_text("\n\n", encoding="utf-8", newline="")
		with environment({"OPSI_HOST_ID": "", "OPSI_HOSTNAME": "env-config.server.id"}):
			assert config.get("host", "id") == "env-config.server.id"

		config_file.write_bytes(b"")
		OpsiConfig.reset_singleton()
		config = OpsiConfig()
		with environment({"OPSI_HOST_ID": "env-config2.server.id", "OPSI_HOSTNAME": ""}):
			assert config.get("host", "id") == "env-config2.server.id"


def test_read_config_file(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	data = """
	[ldap_auth]
	ldap_url = "ldaps://test"
	use_member_of_rdn = false
	"""
	config_file.write_text(dedent(data), encoding="utf-8", newline="")
	config = OpsiConfig()
	assert config._config_file_mtime == 0.0
	assert config.get("ldap_auth", "ldap_url") == "ldaps://test"
	assert config.get("ldap_auth", "use_member_of_rdn") is False
	mtime = config._config_file_mtime
	assert mtime != 0.0

	sleep(0.1)
	# Assert that a changed file is reread
	data = """
	[ldap_auth]
	ldap_url = "ldaps://test2"
	use_member_of_rdn = true
	"""
	config_file.write_text(dedent(data), encoding="utf-8", newline="")
	assert config.get("ldap_auth", "ldap_url") == "ldaps://test2"
	assert config.get("ldap_auth", "use_member_of_rdn") is True


def test_get_config(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	data = """
	[groups]
	fileadmingroup = "FaG"
	"""
	config_file.write_text(dedent(data), encoding="utf-8", newline="")
	config = OpsiConfig()
	assert isinstance(config.get("groups", "fileadmingroup"), str)
	assert config.get("groups", "fileadmingroup") == "fag"
	conf_dict = config.get("groups")
	for key, val in conf_dict.items():
		assert isinstance(key, str)
		assert isinstance(val, str)
	assert conf_dict["fileadmingroup"] == "fag"


def test_set_config(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	OpsiConfig.reset_singleton()
	OpsiConfig.config_file = str(config_file)
	data = """
	[groups]
	fileadmingroup = "fag"
	admingroup = "ag"
	"""
	config_file.write_text(dedent(data), encoding="utf-8", newline="")
	config = OpsiConfig()
	config.set("groups", "fileadmingroup", "new", persistent=True)
	new_data = config_file.read_text(encoding="utf-8")
	assert (
		dedent(
			"""
	[groups]
	fileadmingroup = "new"
	admingroup = "ag"
	"""
		).strip()
		in new_data
	)


def test_set_config_type_check() -> None:
	config = OpsiConfig()
	with pytest.raises(TypeError, match=r"Wrong type 'str' for config 'use_pigz' \(bool\) in category 'packages'"):
		config.set("packages", "use_pigz", "yes")

	with pytest.raises(TypeError, match=r"Wrong type 'bool' for config 'fileadmingroup' \(str\) in category 'groups'"):
		config.set("groups", "fileadmingroup", True)

	with pytest.raises(TypeError, match=r"Wrong type 'int' for config 'ldap_url' \(str\) in category 'ldap_auth'"):
		config.set("ldap_auth", "ldap_url", 123)


def test_set_config_invalid_category_or_config() -> None:
	config = OpsiConfig()
	with pytest.raises(ValueError, match=r"Invalid config 'invalid' for category 'packages'"):
		config.set("packages", "invalid", True)

	with pytest.raises(ValueError, match=r"Invalid category 'invalid'"):
		config.set("invalid", "invalid", True)


def test_get_opsiconfd_user_returns_process_user() -> None:
	processes = [
		SimpleNamespace(info={"name": "python", "username": "ignored"}),
		SimpleNamespace(info={"name": "opsiconfd", "username": "process_user"}),
	]
	with (
		patch("opsi.opsi.service.server._config.psutil.process_iter", return_value=processes),
		environment({"OPSICONFD_RUN_AS_USER": "env_user"}),
	):
		assert get_opsiconfd_user() == "process_user"


def test_get_opsiconfd_user_returns_env_user_without_process() -> None:
	with patch("opsi.opsi.service.server._config.psutil.process_iter", return_value=[]), environment({"OPSICONFD_RUN_AS_USER": "env_user"}):
		assert get_opsiconfd_user() == "env_user"


def test_get_opsiconfd_user_returns_default_without_process_or_env() -> None:
	with patch("opsi.opsi.service.server._config.psutil.process_iter", return_value=[]), environment({"OPSICONFD_RUN_AS_USER": ""}):
		assert get_opsiconfd_user() == DEFAULT_OPSICONFD_USER


def test_read_config_file_with_invalid_groups(tmp_path: Path) -> None:
	config_file = tmp_path / "opsi.conf"
	opsi_config = OpsiConfig()
	opsi_config.config_file = str(config_file)
	data = """
	[groups]
	fileadmingroup = "opsifile admins"
	admingroup = "opsiadmin"
	readonly = ""
	"""
	config_file.write_text(dedent(data), encoding="utf-8", newline="")
	with pytest.raises(ValueError):
		opsi_config.read_config_file()
	opsi_config.config_file = "/etc/opsi/opsi.conf"
	opsi_config.config_file = "/etc/opsi/opsi.conf"
	opsi_config.config_file = "/etc/opsi/opsi.conf"
	opsi_config.config_file = "/etc/opsi/opsi.conf"
