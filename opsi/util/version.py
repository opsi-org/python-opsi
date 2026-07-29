# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
General utility functions.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from typing import Literal

from packaging.version import InvalidVersion, Version

from opsi.logging import get_logger
from opsi.opsi.service.model.type._type import _PACKAGE_VERSION_REGEX, _PRODUCT_VERSION_REGEX

logger = get_logger("opsi")


def _legacy_cmpkey(version: str) -> tuple[str, ...]:
	_legacy_version_component_re = re.compile(r"(\d+ | [a-z]+ | \.| -)", re.VERBOSE)
	_legacy_version_replacement_map = {
		"pre": "c",
		"preview": "c",
		"-": "final-",
		"rc": "c",
		"dev": "@",
	}

	def _parse_version_parts(instring: str) -> Generator[str]:
		for part in _legacy_version_component_re.split(instring):
			part = _legacy_version_replacement_map.get(part, part)

			if not part or part == ".":
				continue

			if part[:1] in "0123456789":
				# pad for numeric comparison
				yield part.zfill(8)
			else:
				yield "*" + part

		# ensure that alpha/beta/candidate are before final
		yield "*final"

	parts: list[str] = []
	for part in _parse_version_parts(version.lower()):
		if part.startswith("*"):
			# remove "-" before a prerelease tag
			if part < "*final":
				while parts and parts[-1] == "*final-":
					parts.pop()

			# remove trailing zeros from each series of numeric parts
			while parts and parts[-1] == "00000000":
				parts.pop()

		parts.append(part)

	return tuple(parts)


# Inspired by packaging.version.LegacyVersion (deprecated)
class LegacyVersion(Version):
	def __init__(self, version: str):
		self._version = str(version)
		self._key = _legacy_cmpkey(self._version)  # type: ignore[invalid-assignment]

	def __str__(self) -> str:
		return str(self._version)


def compare_versions(version1: str, condition: Literal["==", "=", "<", "<=", ">", ">="], version2: str) -> bool:
	"""
	Compare the versions `v1` and `v2` with the given `condition`.

	`condition` may be one of `==`, `=`, `<`, `<=`, `>`, `>=`.

	:raises ValueError: If invalid value for version or condition if given.
	:rtype: bool
	:return: If the comparison matches this will return True.
	"""
	# Remove part after wave to not break old behaviour
	version1 = version1.split("~", 1)[0]
	version2 = version2.split("~", 1)[0]
	for version in (version1, version2):
		parts = version.split("-")
		if (
			not _PRODUCT_VERSION_REGEX.search(parts[0])
			or (len(parts) == 2 and not _PACKAGE_VERSION_REGEX.search(parts[1]))
			or len(parts) > 2
		):
			raise ValueError(f"Bad package version provided: '{version}'")

	try:
		# Don't use packaging.version.parse() here as packaging.version.Version cannot handle legacy formats
		first = LegacyVersion(version1)
		second = LegacyVersion(version2)
	except InvalidVersion as version_error:
		raise ValueError("Invalid version provided to compare_versions") from version_error

	if condition in ("==", "=") or not condition:
		result = first == second
	elif condition == "<":
		result = first < second
	elif condition == "<=":
		result = first <= second
	elif condition == ">":
		result = first > second
	elif condition == ">=":
		result = first >= second
	else:
		raise ValueError(f"Bad condition {condition} provided to compare_versions")

	logger.debug("%s condition: %s %s %s", "Fullfilled" if result else "Unfulfilled", version1, condition, version2)
	return result
