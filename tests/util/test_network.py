# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

import pytest

from opsi.util.network import ip_address_in_network


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
