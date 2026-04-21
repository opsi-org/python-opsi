# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ._info import get_system, is_linux, is_macos, is_posix, is_unix, is_windows
from ._linux import (
	is_deb_based,
	is_pacman_based,
	is_rpm_based,
	linux_distro_id,
	linux_distro_id_like,
	linux_distro_id_like_contains,
	linux_distro_version,
	linux_distro_version_id,
)

__all__ = [
	"get_system",
	"is_deb_based",
	"is_linux",
	"is_macos",
	"is_pacman_based",
	"is_posix",
	"is_rpm_based",
	"is_unix",
	"is_windows",
	"linux_distro_id",
	"linux_distro_id_like",
	"linux_distro_id_like_contains",
	"linux_distro_version",
	"linux_distro_version_id",
]
