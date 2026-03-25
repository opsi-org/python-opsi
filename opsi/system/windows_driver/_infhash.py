# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

_MASK_64 = 0xFFFFFFFFFFFFFFFF
_HASH_BASE = 39


def calc_hash(data: bytes) -> int:
	int_hash = 0
	for char in data:
		int_hash = (int_hash * _HASH_BASE + char) & _MASK_64
	return int.from_bytes(int_hash.to_bytes(8, byteorder="little"), byteorder="big", signed=False)
