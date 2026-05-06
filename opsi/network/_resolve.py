# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import socket
from ipaddress import IPv4Address, IPv6Address, ip_address


def resolve_hostname(hostname: str) -> list[IPv4Address | IPv6Address]:
	addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
	ip_addresses = set()

	for result in addr_info:
		ip_addresses.add(ip_address(result[4][0]))

	return list(ip_addresses)
