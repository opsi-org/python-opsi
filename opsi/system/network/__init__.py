# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ._common import (
	DNSNameserver,
	NetworkInfo,
	NetworkInterface,
	NetworkRoute,
	get_domain,
	get_fqdn,
	get_hostnames,
	get_network_info,
	prepare_proxy_environment,
)

__all__ = [
	"get_hostnames",
	"get_domain",
	"get_network_info",
	"get_fqdn",
	"NetworkInterface",
	"NetworkRoute",
	"DNSNameserver",
	"NetworkInfo",
	"prepare_proxy_environment",
]
