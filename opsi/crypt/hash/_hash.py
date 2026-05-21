# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import binascii
import enum
import hashlib
import hmac
import os
from hashlib import md5
from pathlib import Path
from typing import Callable

import bcrypt
from argon2 import DEFAULT_HASH_LENGTH as ARGON2_DEFAULT_HASH_LENGTH
from argon2 import DEFAULT_MEMORY_COST as ARGON2_DEFAULT_MEMORY_COST
from argon2 import DEFAULT_PARALLELISM as ARGON2_DEFAULT_PARALLELISM
from argon2 import DEFAULT_RANDOM_SALT_LENGTH as ARGON2_DEFAULT_SALT_LENGTH
from argon2 import DEFAULT_TIME_COST as ARGON2_DEFAULT_TIME_COST
from argon2 import PasswordHasher
from argon2.low_level import Type as Argon2Type
from argon2.low_level import hash_secret as argon2_hash_secret
from blake3 import blake3

from opsi.system.info import is_linux
from opsi.util.pattern import MappedStrEnum

if is_linux():
	import crypt_r


class FileHashAlgorithm(MappedStrEnum):
	_NAME = enum.nonmember("file hash algorithm")

	BLAKE3 = "blake3"
	MD5 = "md5"


def hash_file(file_path: Path, algorithm: FileHashAlgorithm | str, *, progress_callback: Callable[[int, int], None] | None = None) -> str:
	"""
	Compute the hash of a file using the specified algorithm.
	Returns the hexadecimal digest of the file.
	"""
	algorithm = FileHashAlgorithm(algorithm)

	file_size = file_path.stat().st_size
	buffer_size = 2**18
	hasher = blake3() if algorithm == FileHashAlgorithm.BLAKE3 else md5()
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
	expected_hash: str, file_path: Path, algorithm: FileHashAlgorithm | str, progress_callback: Callable[[int, int], None] | None = None
) -> bool:
	"""
	Verify the hash of a file using the specified algorithm.
	Returns True if the computed hash matches the provided hash, False otherwise.
	"""
	return expected_hash == hash_file(file_path, FileHashAlgorithm(algorithm), progress_callback=progress_callback)


class PasswordHashFormat(MappedStrEnum):
	_NAME = enum.nonmember("password hash format")

	SHADOW = "SHADOW"
	GRUB = "GRUB"


class PasswordHashAlgorithm(MappedStrEnum):
	_NAME = enum.nonmember("password hash algorithm")
	_ALIASES = enum.nonmember({"PBKDF2-SHA512": "PBKDF2_SHA512"})

	SHA512 = "SHA512"
	BCRYPT = "BCRYPT"
	PBKDF2_SHA512 = "PBKDF2_SHA512"
	ARGON2ID = "ARGON2ID"

	def identifier(self) -> str:
		if self == PasswordHashAlgorithm.ARGON2ID:
			return "argon2id"
		if self == PasswordHashAlgorithm.SHA512:
			return "6"
		if self == PasswordHashAlgorithm.BCRYPT:
			return "2b"
		if self == PasswordHashAlgorithm.PBKDF2_SHA512:
			return "pbkdf2.sha512"
		raise ValueError(f"Unsupported hashing algorithm: {self!r}")

	@classmethod
	def from_identifier(cls, identifier: str) -> PasswordHashAlgorithm:
		if identifier == "argon2id":
			return PasswordHashAlgorithm.ARGON2ID
		if identifier == "6":
			return PasswordHashAlgorithm.SHA512
		if identifier in ("2a", "2b", "2y"):
			return PasswordHashAlgorithm.BCRYPT
		if identifier == "pbkdf2.sha512":
			return PasswordHashAlgorithm.PBKDF2_SHA512
		raise ValueError(f"Unsupported hashing algorithm {identifier!r}")


def get_password_hash_algorithm(password_hash: str) -> PasswordHashAlgorithm:
	"""
	Get the hashing algorithm used for a given hash string.
	"""
	if password_hash.startswith("grub.pbkdf2.sha512."):
		return PasswordHashAlgorithm.PBKDF2_SHA512

	if password_hash.count("$") < 3:
		raise ValueError("Invalid shadow hash format")

	identifier = password_hash.split("$", 2)[1]
	return PasswordHashAlgorithm.from_identifier(identifier)


def hash_password(
	password: str,
	*,
	algorithm: PasswordHashAlgorithm | str = PasswordHashAlgorithm.ARGON2ID,
	rounds: int | None = None,
	format: PasswordHashFormat = PasswordHashFormat.SHADOW,
	generate_salt: bool = True,
) -> str:
	"""
	Encode a password using the specified algorithm and return a hash string.
	"""
	encoded_password = password.encode("utf-8")
	if len(encoded_password) > 64:
		# Max for bcrypt is 72 bytes
		raise ValueError("Password cannot be longer than 64 bytes")
	if not isinstance(algorithm, PasswordHashAlgorithm):
		algorithm = PasswordHashAlgorithm(algorithm)
	if rounds is not None:
		rounds = int(rounds)
	if not isinstance(format, PasswordHashFormat):
		format = PasswordHashFormat(format)

	if algorithm == PasswordHashAlgorithm.ARGON2ID:
		if format != PasswordHashFormat.SHADOW:
			raise ValueError("ARGON2ID only supported with SHADOW format")
		return argon2_hash_secret(
			secret=password.encode("utf-8"),
			salt=os.urandom(ARGON2_DEFAULT_SALT_LENGTH) if generate_salt else b"................",
			time_cost=ARGON2_DEFAULT_TIME_COST,
			memory_cost=ARGON2_DEFAULT_MEMORY_COST,
			parallelism=ARGON2_DEFAULT_PARALLELISM,
			hash_len=ARGON2_DEFAULT_HASH_LENGTH,
			type=Argon2Type.ID,
		).decode("ascii")

	if algorithm == PasswordHashAlgorithm.SHA512:
		if not is_linux():
			raise ValueError("SHA512 hashing only supported on Linux")
		if format != PasswordHashFormat.SHADOW:
			raise ValueError("SHA512 only supported with SHADOW format")
		rounds = rounds or 5000
		salt = (
			crypt_r.mksalt(
				method=crypt_r.METHOD_SHA512,  # ty: ignore[unresolved-attribute]
				rounds=rounds,
			)
			if generate_salt
			else f"$6$rounds={rounds}$................$"
		)
		return crypt_r.crypt(password, salt=salt)

	if algorithm == PasswordHashAlgorithm.BCRYPT:
		if format != PasswordHashFormat.SHADOW:
			raise ValueError("BCRYPT only supported with SHADOW format")
		rounds = rounds or 12
		salt = bcrypt.gensalt(rounds=rounds) if generate_salt else f"$2b${rounds}$......................$".encode("utf-8")
		return bcrypt.hashpw(encoded_password, salt).decode("utf-8")

	if algorithm == PasswordHashAlgorithm.PBKDF2_SHA512:
		if format != PasswordHashFormat.GRUB:
			raise ValueError("PBKDF2_SHA512 only supported with GRUB format")

		salt = os.urandom(16) if generate_salt else b"................"
		rounds = rounds or 10_000
		hash_bytes = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, rounds)
		return f"grub.pbkdf2.sha512.{rounds}.{binascii.hexlify(salt).decode().upper()}.{binascii.hexlify(hash_bytes).decode().upper()}"

	raise ValueError(f"Only 'SHA512', 'BCRYPT' and 'PBKDF2_SHA512' methods are supported, not {algorithm!r}")


def verify_password(password: str, password_hash: str, algorithm: PasswordHashAlgorithm | str | None = None) -> bool:
	"""
	Verify a password against a given hash string.
	"""
	if not algorithm:
		algorithm = get_password_hash_algorithm(password_hash)
	elif not isinstance(algorithm, PasswordHashAlgorithm):
		algorithm = PasswordHashAlgorithm(algorithm)

	if algorithm == PasswordHashAlgorithm.ARGON2ID:
		hasher = PasswordHasher()
		try:
			return hasher.verify(password_hash, password)
		except Exception:
			return False

	if algorithm == PasswordHashAlgorithm.SHA512:
		if not is_linux():
			raise ValueError("SHA512 hashing only supported on Linux")
		return crypt_r.crypt(password, password_hash) == password_hash

	if algorithm == PasswordHashAlgorithm.BCRYPT:
		return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

	if algorithm == PasswordHashAlgorithm.PBKDF2_SHA512:
		try:
			grub, pbkdf2, sha512, rounds, salt, expected_hash = password_hash.split(".", 5)
			if (grub, pbkdf2, sha512) != ("grub", "pbkdf2", "sha512"):
				return False
			rounds_int = int(rounds)
			salt_bytes = binascii.unhexlify(salt)
			expected_hash_bytes = binascii.unhexlify(expected_hash)
		except (TypeError, ValueError, binascii.Error):
			return False

		computed_hash = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt_bytes, rounds_int)
		return hmac.compare_digest(computed_hash, expected_hash_bytes)

	raise ValueError("Only 'ARGON2ID', 'SHA512', 'BCRYPT' and 'PBKDF2_SHA512' methods are supported")
