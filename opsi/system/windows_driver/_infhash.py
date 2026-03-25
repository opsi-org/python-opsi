# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

def calc_hash(data: bytes) -> int:
	dataarray = bytearray(data)
	dataarray.reverse()
	int_hash = 0
	for idx, char in enumerate(dataarray):
		pwr = 39**idx
		int_hash += (pwr & 0xFFFFFFFFFFFFFFFF) * char
		int_hash &= 0xFFFFFFFFFFFFFFFF
	return int.from_bytes(int_hash.to_bytes(8, byteorder="little"), byteorder="big", signed=False)
