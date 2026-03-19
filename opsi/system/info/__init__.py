# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from ._info import get_system, is_linux, is_macos, is_posix, is_unix, is_windows

__all__ = ["is_linux", "is_windows", "is_macos", "is_unix", "is_posix", "get_system"]
