# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

_msgspec_msgpack_encode: Callable | None = None
_msgspec_msgpack_decode: Callable | None = None
try:
	from msgspec.msgpack import decode as _msgspec_msgpack_decode
	from msgspec.msgpack import encode as _msgspec_msgpack_encode
except ImportError:
	from msgpack import packb as _msgpack_msgpack_encode  # ty: ignore[unresolved-import]
	from msgpack import unpackb as _msgpack_msgpack_decode  # ty: ignore[unresolved-import]


def _msgpack_encode_handler(obj: Any) -> Any:
	if isinstance(obj, datetime):
		return obj.isoformat()
	raise TypeError(f"TypeError: can not serialize '{type(obj)}' object")


def msgpack_encode(obj: Any) -> bytes:
	if _msgspec_msgpack_encode:
		return _msgspec_msgpack_encode(obj)
	if is_dataclass(obj) and not isinstance(obj, type):
		return _msgpack_msgpack_encode(asdict(obj), default=_msgpack_encode_handler)
	return _msgpack_msgpack_encode(obj, default=_msgpack_encode_handler)


def msgpack_decode(data: bytes) -> Any:
	if _msgspec_msgpack_decode:
		return _msgspec_msgpack_decode(data)
	return _msgpack_msgpack_decode(data)
