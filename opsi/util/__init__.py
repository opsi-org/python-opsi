# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.util._pattern import Singleton
from opsi.util._version import LegacyVersion, compare_versions

__all__ = ["Singleton", "compare_versions", "LegacyVersion"]
