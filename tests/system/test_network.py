# opsicommon is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2020-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
test_system_network
"""

import os
import platform
import socket
from ipaddress import ip_network
from pathlib import Path
from unittest import mock

import pytest

from opsi.system.network import get_domain, get_fqdn, get_hostnames, get_network_info, prepare_proxy_environment
from opsi.system.network._common import _gethostbyaddr_with_timeout
from opsi.testing.helper import environment


def test_get_network_info() -> None:
	network_info = get_network_info(include_link_local=True)
	assert network_info.interfaces
	assert network_info.routes
	assert network_info.dns_nameservers
	assert network_info.search_domains
	default_routes = [route for route in network_info.routes if route.is_default]
	assert default_routes
	default_route_interfaces = [interface for interface in network_info.interfaces if interface.is_default_gateway]
	assert default_route_interfaces
	assert set(route.interface_name for route in default_routes) == set(interface.name for interface in default_route_interfaces)
	assert any(interface.is_loopback for interface in network_info.interfaces)
	assert any(not interface.is_loopback for interface in network_info.interfaces)
	for interface in network_info.interfaces:
		if interface.prefixlen and interface.broadcast:
			network = ip_network(f"{interface.address}/{interface.prefixlen}", strict=False)
			assert interface.broadcast == network.broadcast_address
	if platform.system() == "Linux":
		# TODO: Currently not working on Windows and macOS, needs further investigation
		assert all(interface.mac_address == "00:00:00:00:00:00" for interface in network_info.interfaces if interface.is_loopback)


def test_get_fqdn() -> None:
	fqdn = socket.getfqdn()
	if "." in fqdn:
		assert fqdn == socket.getfqdn()
	try:
		with mock.patch("socket.getfqdn", lambda x=None: "hostname"):
			assert "." in get_fqdn()
	except RuntimeError:
		pass

	with (
		mock.patch("socket.getfqdn", lambda x=None: ""),
		mock.patch("opsi.system.network._common.get_hostnames", lambda: ["hostname1", "hostname2", "hostname1.domain.test", "alias"]),
	):
		assert get_fqdn() == "hostname1.domain.test"


def test_get_domain() -> None:
	with mock.patch("socket.getfqdn", lambda x=None: "hostname.domain.org"):
		assert get_domain() == "domain.org"


def test_get_hostnames() -> None:
	hostnames = get_hostnames()
	print(hostnames)
	assert "localhost" in hostnames


def test_gethostbyaddr_with_timeout() -> None:
	exc: Exception | None = None
	try:
		_gethostbyaddr_with_timeout("test.unavail.lan", 0.001)
	except (TimeoutError, socket.error) as err:
		exc = err
	assert exc
	assert _gethostbyaddr_with_timeout("127.0.0.1", 1.0)[0] in ("localhost", socket.gethostname())
	assert _gethostbyaddr_with_timeout("127.0.0.1", 1.0)[0] in ("localhost", socket.gethostname())


def test_prepare_proxy_environment() -> None:
	with environment({"http_proxy": "http://my.proxy.server:3128", "https_proxy": "https://my.proxy.server:3129", "no_proxy": ""}):
		session = prepare_proxy_environment("my.test.server", proxy_url="http://my.proxy.server:3130")
		assert session.proxies.get("http") == "http://my.proxy.server:3130"

		session = prepare_proxy_environment("my.test.server")
		assert not session.proxies  # rely on environment, proxy not set explicitly

		# Do not use proxy
		prepare_proxy_environment("my.test.server", proxy_url=None)
		assert os.environ.get("no_proxy") == "*"


@pytest.mark.linux
def test_prepare_proxy_environment_file(tmp_path: Path) -> None:
	from opsi.system.linux import update_environment_from_config_files

	with environment({"https_proxy": "", "http_proxy": "", "no_proxy": ""}):
		with open(tmp_path / "somefile.env", "w", encoding="utf-8") as f:
			f.write("https_proxy=https://my.proxy.server:3129\n")
			f.write("export http_proxy=http://my.proxy.server:3128\n")
			f.write('export no_proy=""\n')
		update_environment_from_config_files([tmp_path / "somefile.env"])
		assert os.environ.get("http_proxy") == "http://my.proxy.server:3128"
		assert os.environ.get("https_proxy") == "https://my.proxy.server:3129"
		assert os.environ.get("no_proxy") == ""  # not '""'!
