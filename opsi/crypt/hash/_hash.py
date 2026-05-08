# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations
from hashlib import md5
from pathlib import Path
from typing import Callable
import enum

from blake3 import blake3
from opsi.util.pattern import MappedStrEnum


class HashAlgorithm(MappedStrEnum):
	_NAME = enum.nonmember("hash algorithm")

	BLAKE3 = "blake3"
	MD5 = "md5"


def compute_file_hash(
	file_path: Path, algorithm: HashAlgorithm | str, *, progress_callback: Callable[[int, int], None] | None = None
) -> str:
	"""
	Compute the hash of a file using the specified algorithm.
	Returns the hexadecimal digest of the file.
	"""
	algorithm = HashAlgorithm(algorithm)

	file_size = file_path.stat().st_size
	buffer_size = 2**18
	hasher = blake3() if algorithm == HashAlgorithm.BLAKE3 else md5()
	buf = bytearray(buffer_size)
	view = memoryview(buf)
	position = 0
	if progress_callback:
		progress_callback(position, file_size)
	with open(file_path, "rb") as file_handle:
		while size := file_handle.readinto(buf):
			hasher.update(view[:size])
			position += size
			if progress_callback:
				progress_callback(position, file_size)
		return hasher.hexdigest()


def verify_file_hash(
	hash: str, file_path: Path, algorithm: HashAlgorithm | str, progress_callback: Callable[[int, int], None] | None = None
) -> bool:
	"""
	Verify the hash of a file using the specified algorithm.
	Returns True if the computed hash matches the provided hash, False otherwise.
	"""
	return hash == compute_file_hash(file_path, HashAlgorithm(algorithm), progress_callback=progress_callback)
