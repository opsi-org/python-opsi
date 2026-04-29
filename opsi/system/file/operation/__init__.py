# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.system.file.operation._delete import delete
from opsi.system.file.operation._link import get_link_target, link

__all__ = ["delete", "link", "get_link_target"]
