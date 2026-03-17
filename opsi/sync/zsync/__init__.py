# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pyzsync import SOURCE_REMOTE, create_zsync_file, get_patch_instructions, read_zsync_file

__all__ = ["SOURCE_REMOTE", "create_zsync_file", "get_patch_instructions", "read_zsync_file"]
