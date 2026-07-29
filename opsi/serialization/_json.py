# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from pydantic_core import from_json as _pydantic_json_decode
from pydantic_core import to_json as _pydantic_json_encode

_msgspec_json_encode: Callable | None = None
_msgspec_json_decode: Callable | None = None

try:
	from msgspec.json import decode as _msgspec_json_decode
	from msgspec.json import encode as _msgspec_json_encode
except ImportError:
	pass


def json_encode(obj: Any) -> bytes:
	if _msgspec_json_encode:
		return _msgspec_json_encode(obj)
	if is_dataclass(obj) and not isinstance(obj, type):
		return _pydantic_json_encode(asdict(obj))
	return _pydantic_json_encode(obj)


def json_decode(data: bytes) -> Any:
	if _msgspec_json_decode:
		return _msgspec_json_decode(data)
	return _pydantic_json_decode(data)


def _msgpack_encode_handler(obj: Any) -> Any:
	if isinstance(obj, datetime):
		return obj.isoformat()
	raise TypeError(f"TypeError: can not serialize '{type(obj)}' object")
