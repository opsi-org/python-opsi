# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from typing import Self

import pytest

from opsi.network import _network, ip_address_in_network, ipv6_available, ping, resolve_hostname
from opsi.system.info import is_linux


class MockSocket:
	def __init__(self) -> None:
		self.bound_address: tuple[str, int] | None = None

	def __enter__(self) -> Self:
		return self

	def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
		return None

	def bind(self, address: tuple[str, int]) -> None:
		self.bound_address = address


@pytest.mark.parametrize(
	"address, network, expected",
	[
		("10.10.1.1", "10.10.0.0/16", True),
		("10.10.1.1", "10.10.0.0/23", True),
		("10.10.1.1", "10.10.0.0/24", False),
		("10.10.1.1", "10.10.0.0/25", False),
		("10.10.1.1", "0.0.0.0/0", True),
		("10.10.1.1", "10.10.0.0/255.255.0.0", True),
		(IPv4Address("192.168.1.1"), IPv4Network("192.168.1.0/24"), True),
		(IPv4Address("192.168.1.1"), IPv4Network("192.168.2.0/24"), False),
	],
)
def test_ip_address_in_network(address: str | IPv4Address | IPv6Address, network: str | IPv4Network | IPv6Network, expected: bool) -> None:
	assert ip_address_in_network(address, network) == expected


@pytest.mark.parametrize(
	"address, network, expected",
	[
		(IPv6Address("::ffff:192.168.1.10"), IPv4Network("192.168.1.0/24"), True),
		(IPv6Address("::ffff:192.168.2.10"), IPv4Network("192.168.1.0/24"), False),
	],
)
def test_ip_address_in_network_ipv4_mapped_ipv6(address: IPv6Address, network: IPv4Network, expected: bool) -> None:
	assert ip_address_in_network(address, network) == expected


def test_ipv6_available_returns_true_if_loopback_socket_can_be_bound(monkeypatch: pytest.MonkeyPatch) -> None:
	mock_socket = MockSocket()

	def socket_factory(family: int, sock_type: int) -> MockSocket:
		assert family == _network.socket.AF_INET6
		assert sock_type == _network.socket.SOCK_DGRAM
		return mock_socket

	monkeypatch.setattr(_network.socket, "has_ipv6", True)
	monkeypatch.setattr(_network.socket, "socket", socket_factory)

	assert ipv6_available() is True
	assert mock_socket.bound_address == ("::1", 0)


def test_ipv6_available_returns_false_if_python_has_no_ipv6_support(monkeypatch: pytest.MonkeyPatch) -> None:
	def socket_factory(family: int, sock_type: int) -> MockSocket:
		raise AssertionError("socket must not be created if IPv6 support is disabled")

	monkeypatch.setattr(_network.socket, "has_ipv6", False)
	monkeypatch.setattr(_network.socket, "socket", socket_factory)

	assert ipv6_available() is False


def test_ipv6_available_returns_false_if_loopback_socket_cannot_be_bound(monkeypatch: pytest.MonkeyPatch) -> None:
	class FailingSocket(MockSocket):
		def bind(self, address: tuple[str, int]) -> None:
			raise OSError("IPv6 is unavailable")

	monkeypatch.setattr(_network.socket, "has_ipv6", True)
	monkeypatch.setattr(_network.socket, "socket", lambda family, sock_type: FailingSocket())

	assert ipv6_available() is False


@pytest.mark.parametrize(
	"hostname, expected_address",
	[
		("localhost", IPv4Address("127.0.0.1")),
		("::1", IPv6Address("::1")),
		("127.0.0.1", IPv4Address("127.0.0.1")),
	]
	+ [("ip6-localhost", IPv6Address("::1"))]
	if is_linux()
	else [],
)
def test_resolve_hostname(hostname: str, expected_address: IPv4Address | IPv6Address) -> None:
	ip_addresses = resolve_hostname(hostname)
	assert any(isinstance(addr, type(expected_address)) and addr == expected_address for addr in ip_addresses)


@pytest.mark.admin_permissions
@pytest.mark.parametrize(
	"destination, reachable",
	[
		("127.0.0.1", True),
		(IPv4Address("127.0.0.1"), True),
		("localhost", True),
		("192.0.2.1", False),
	]
	+ [
		("::1", True),
		(IPv6Address("::1"), True),
		("2001:db8::1", False),
	]
	if ipv6_available()
	else []
	+ [
		("ip6-localhost", True),
	]
	if is_linux() and ipv6_available()
	else [],
)
def test_ping(destination: str | IPv4Address | IPv6Address, reachable: bool) -> None:
	ping_result = ping(destination, count=1, timeout=2.0)
	if reachable:
		assert ping_result.total_time < 1.0
		assert ping_result.packets_send == 1
		assert ping_result.packets_received == 1
		assert ping_result.packet_loss == 0.0
		assert ping_result.rtt_avg is not None
		assert ping_result.rtt_min is not None
		assert ping_result.rtt_max is not None
		assert 0.0 < ping_result.rtt_avg < 0.01
		assert 0.0 < ping_result.rtt_min < 0.01
		assert 0.0 < ping_result.rtt_max < 0.01
	else:
		assert ping_result.total_time < 3.0
		assert ping_result.packets_send == 1
		assert ping_result.packets_received == 0
		assert ping_result.packet_loss == 100.0
		assert ping_result.rtt_avg is None
		assert ping_result.rtt_min is None
		assert ping_result.rtt_max is None


@pytest.mark.admin_permissions
def test_ping_count() -> None:
	ping_result = ping("127.0.0.1", count=3)
	# Total time should be at least 2 seconds (3 pings with 1 second wait between them)
	assert 2.0 < ping_result.total_time < 3.0
	assert ping_result.packets_send == 3
	assert ping_result.packets_received == 3
	assert ping_result.packet_loss == 0.0
	assert ping_result.rtt_min is not None
	assert ping_result.rtt_max is not None
	assert ping_result.rtt_avg is not None
	assert 0.0 < ping_result.rtt_avg < 0.01
	assert 0.0 < ping_result.rtt_min < 0.01
	assert 0.0 < ping_result.rtt_max < 0.01
