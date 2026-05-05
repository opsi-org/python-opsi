# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import os

from ._common import DisplaySession


def get_display_sessions(*, one_session_per_user: bool = True) -> list[DisplaySession]:
	return [DisplaySession(id="1", console=True, user=os.getenv("USER") or None)]
