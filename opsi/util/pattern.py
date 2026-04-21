# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from typing import Any


class Singleton(type):
	__instances: dict[type, type] = {}

	def __call__(cls: Singleton, *args: Any, **kwargs: Any) -> type:
		if cls not in cls.__instances:
			cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls.__instances[cls]
