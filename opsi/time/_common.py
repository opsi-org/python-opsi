# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2026-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from datetime import datetime, timezone

_now = datetime.now
_utc = timezone.utc


def unix_timestamp(*, millis: bool = False, add_seconds: float = 0.0) -> float:
	"""
	Returns the current unix timestamp (UTC).
	If `millis` is True, the timestamp is in milliseconds.
	`add_seconds` can be used to add or subtract seconds from the current time.
	"""
	# Do not use time.time() as the behaviour can be platform and timezone dependent
	unix_ts = _now(tz=_utc).timestamp() + add_seconds
	if millis:
		return unix_ts * 1000
	return unix_ts
