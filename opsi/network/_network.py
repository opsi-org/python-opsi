# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import socket
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network


def ipv6_available() -> bool:
	"""
	Check whether IPv6 is available on the local system.

	Returns
	-------
	bool
		True if IPv6 is available, False otherwise.
	"""
	if not socket.has_ipv6:
		return False

	try:
		with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as ipv6_socket:
			ipv6_socket.bind(("::1", 0))
	except OSError:
		return False

	return True


def ip_address_in_network(address: str | IPv4Address | IPv6Address, network: str | IPv4Network | IPv6Network) -> bool:
	"""
	Checks if the given IP address is in the given network range.
	Returns ``True`` if the given address is part of the network.
	Returns ``False`` if the given address is not part of the network.

	:param address: The IP which we check.
	:type address: str
	:param network: The network address written with slash notation.
	:type network: str
	"""
	if not isinstance(address, (IPv4Address, IPv6Address)):
		address = ip_address(address)
	if isinstance(address, IPv6Address) and address.ipv4_mapped:
		address = address.ipv4_mapped

	if not isinstance(network, (IPv4Network, IPv6Network)):
		network = ip_network(network)

	return address in network
