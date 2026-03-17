# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from dotenv import dotenv_values

ENCODING = "utf-8"


class KeyValueFile:
	"""
	Represents a simple key-value file (like .env) and provides methods to read
	and modify its contents."""

	def __init__(self, keyValue_file: str) -> None:
		self.filename = Path(keyValue_file)

		# Load existing data and get a real copy of it
		self._data = dict(dotenv_values(keyValue_file))

	def set_value(self, key: str, value: str) -> None:
		"""
		Set a key-value pair in the file. If the key already exists, it will be overwritten.

		:param key: The key to set.
		:param value: The value to associate with the key.
		"""
		self._data[key] = value

	def remove_key(self, key: str) -> None:
		"""
		Remove a key from the file. If the key does not exist, this method does nothing.

		:param key: The key to remove.
		"""
		if key in self._data:
			del self._data[key]

	def get_value(self, key: str, default: str = "") -> str:
		"""
		Get the value associated with a key. If the key does not exist, return the default value.

		:param key: The key to look up.
		:param default: The value to return if the key is not found.
		:return: The value associated with the key, or the default value if the key is not found.
		"""
		if key in self._data:
			return self._data[key] or ""
		return default

	def _update_file(self) -> None:
		# write back to file
		with self.filename.open("w") as f:
			for key, value in self._data.items():
				f.write(f"{key}={value}\n")


@contextmanager
def open(keyValue_file: str, /, *, encoding: str = ENCODING) -> Generator[KeyValueFile, None, None]:
	kv_file = KeyValueFile(keyValue_file)
	yield kv_file
	kv_file._update_file()


def get_value(
	keyValue_file: str,
	key: str,
	default: str = "",
) -> str:
	"""
	Get the value associated with a key. If the key does not exist, return the default value.
	This is a convenience function for KeyValueFile.get_value."""
	with open(keyValue_file) as kv_file:
		return kv_file.get_value(key, default)


def set_value(
	keyValue_file: str,
	key: str,
	value: str,
) -> None:
	"""
	Set a key-value pair in the file. If the key already exists, it will be overwritten.

	This is a convenience function for KeyValueFile.set_value."""
	with open(keyValue_file) as kv_file:
		kv_file.set_value(key, value)


def remove_key(
	keyValue_file: str,
	key: str,
) -> None:
	"""
	Remove a key from the file. If the key does not exist, this function does nothing.

	This is a convenience function for KeyValueFile.remove_key."""
	with open(keyValue_file) as kv_file:
		kv_file.remove_key(key)
