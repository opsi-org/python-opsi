# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import datetime
from dataclasses import asdict, dataclass
from typing import Any, Literal

import pytest

from opsi.serialization._common import (
	_msgspec_json_decode,
	_msgspec_json_encode,
	json_decode,
	json_encode,
	msgpack_decode,
	msgpack_encode,
)
from opsi.system.info import is_linux


@pytest.mark.parametrize("format", ["json", "msgpack"])
def test_encode_decode(format: Literal["json", "msgpack"]) -> None:
	if is_linux():
		assert _msgspec_json_encode
		assert _msgspec_json_decode

	encode = json_encode if format == "json" else msgpack_encode
	decode = json_decode if format == "json" else msgpack_decode

	now = datetime.datetime.now()
	data = {"test": "value", "list": [1, 2, 3], "now": now}
	encoded = json_encode(data)
	data["now"] = data["now"].isoformat()
	assert json_decode(encoded) == data

	@dataclass
	class TestClass:
		id: int | str
		result: Any
		jsonrpc: str = "2.0"

	data = TestClass(id=1, result={"key1": "value1", "key2": ["listvalue1", "listvalue2"]})
	encoded = encode(data)
	assert decode(encoded) == asdict(data)
