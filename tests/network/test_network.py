# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

import pytest

from opsi.network import ip_address_in_network, ping, resolve_hostname


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


@pytest.mark.parametrize(
	"hostname, expected_address",
	[
		("localhost", IPv4Address("127.0.0.1")),
		("ip6-localhost", IPv6Address("::1")),
		("::1", IPv6Address("::1")),
		("127.0.0.1", IPv4Address("127.0.0.1")),
	],
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
		("::1", True),
		("ip6-localhost", True),
		(IPv6Address("::1"), True),
		("2001:db8::1", False),
	],
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
		assert 2.0 <= ping_result.total_time < 3.0
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
