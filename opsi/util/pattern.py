# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from typing import Any, Self
from enum import StrEnum, nonmember


class Singleton(type):
	_instances: dict[type, type] = {}

	def __call__(cls: Singleton, *args: Any, **kwargs: Any) -> type:
		if cls not in cls._instances:
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]


class MappedStrEnum(StrEnum):
	_NAME = nonmember("")
	_ALIASES = nonmember({})

	def __init_subclass__(cls, **kwargs: Any) -> None:
		super().__init_subclass__(**kwargs)
		cls._NAME = str(cls._NAME) or cls.__name__
		if not isinstance(cls._ALIASES, dict):
			raise ValueError(f"Invalid value {cls._ALIASES!r} for _ALIASES, must be a dict mapping alias to value")

	@classmethod
	def _missing_(cls, value: object) -> Self:
		value = str(value)
		if value in cls._ALIASES:
			value = str(cls._ALIASES[value])

		value = value.lower()
		if value in cls._ALIASES:
			value = str(cls._ALIASES[value])

		for member in cls:
			if member.value.lower() == value:
				return member

		valid_values = ", ".join(repr(member.value) for member in cls)
		raise ValueError(f"Invalid value {value!r} for {cls._NAME or cls.__name__}, supported values are: {valid_values}")
