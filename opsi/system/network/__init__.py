# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.exception import OperatingSystemUnsupportedError
from opsi.system.info import get_system, is_linux, is_macos, is_windows
from opsi.system.network._network import (
	DNSNameserver,
	NetworkInfo,
	NetworkInterface,
	NetworkRoute,
	get_domain,
	get_fqdn,
	get_hostnames,
	get_network_info,
	mount_network_share,
	prepare_proxy_environment,
)

if is_linux():
	from opsi.system.network._linux import mount_cifs_share, mount_webdav_share, unmount_network_share
elif is_macos():
	from opsi.system.network._macos import mount_cifs_share, mount_webdav_share, unmount_network_share
elif is_windows():
	from opsi.system.network._windows import mount_cifs_share, mount_webdav_share, unmount_network_share
else:
	raise OperatingSystemUnsupportedError(f"{get_system()} not supported")

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
	"mount_network_share",
	"mount_cifs_share",
	"mount_webdav_share",
	"unmount_network_share",
]
