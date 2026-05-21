# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from pathlib import Path

import pytest

from opsi.crypt.hash import (
	FileHashAlgorithm,
	PasswordHashAlgorithm,
	PasswordHashFormat,
	hash_file,
	hash_password,
	verify_file_hash,
	verify_password,
)
from opsi.crypt.hash._hash import get_password_hash_algorithm
from opsi.system.info import is_linux


@pytest.mark.parametrize("algorithm", ("md5", FileHashAlgorithm.BLAKE3))
@pytest.mark.parametrize("progress", (True, False))
def test_file_hash(tmp_path: Path, algorithm: str | FileHashAlgorithm, progress: bool) -> None:
	progress_values = []

	def progress_callback(position: int, total: int) -> None:
		nonlocal progress_values
		progress_values.append((position, total))

	file_path = tmp_path / "testfile.bin"
	data = b"Test data for hashing.\n" * 1000
	data_size = len(data)
	file_path.write_bytes(data)

	assert hash_file(file_path, algorithm, progress_callback=progress_callback if progress else None) == (
		"1ec7769251775e55268a584de164f320" if algorithm == "md5" else "20294ccbccc9eb04e6c8245213920d3be812de6ed1fb7e727526de4189acc5a9"
	)
	if progress:
		assert len(progress_values) > 1
		assert progress_values[0] == (0, data_size)
		assert progress_values[-1] == (data_size, data_size)
	else:
		assert len(progress_values) == 0

	assert verify_file_hash(
		"1ec7769251775e55268a584de164f320" if algorithm == "md5" else "20294ccbccc9eb04e6c8245213920d3be812de6ed1fb7e727526de4189acc5a9",
		file_path,
		algorithm,
		progress_callback=progress_callback if progress else None,
	)

	assert not verify_file_hash(
		"04e6c8245213920d3be812de6ed1fb7e", file_path, algorithm, progress_callback=progress_callback if progress else None
	)

	with pytest.raises(ValueError, match="Invalid value 'sha256' for file hash algorithm, supported values are: 'blake3', 'md5'"):
		hash_file(file_path, "sha256")
		verify_file_hash("somehash", file_path, "sha256")


def test_PasswordHashAlgorithm_identifier_and_from_identifier() -> None:
	for alg in PasswordHashAlgorithm:
		identifier = alg.identifier()
		assert PasswordHashAlgorithm.from_identifier(identifier) == alg
	with pytest.raises(ValueError, match="Unsupported hashing algorithm 'invalid'"):
		PasswordHashAlgorithm.from_identifier("invalid")


@pytest.mark.parametrize("generate_salt", (True, False))
@pytest.mark.parametrize(
	"password, algorithm, rounds, format, expected_exception, expected_exception_message",
	(
		(r"?z!W!@pmvU;7-|`}P7rb]Xz@VZ", "BCRYPT", 13, "SHADOW", None, None),
		(r"7ERlz[I|12by1ycIqe?ES6t`2r<F,y", "BCRYPT", None, None, None, None),
		(r'Eg$l5;]g\&yW)lC9)*WI"0dOI]XV', "BCRYPT", None, None, None, None),
		("x" * 65, "BCRYPT", None, "SHADOW", ValueError, "Password cannot be longer than 64 bytes"),
		(r"o~'UaGQ,negIb_nf7_}(SrFC)\"", "SHA512", 5000, "SHADOW", None, None),
		(r"5&|F{#(OO+y?z`Zg];AL&TIJ;", "SHA512", None, "SHADOW", None, None),
		(r"c5e9b99b0e4a4d3f8a6722b2e91a8cd4d274a923e56d43f4d2b1187b9b09f6a3", "SHA512", None, "SHADOW", None, None),
		("x" * 65, "SHA512", None, "SHADOW", ValueError, "Password cannot be longer than 64 bytes"),
		("secret", "pbkdf2-sha512", None, "GRUB", None, None),
		("secret", "PBKDF2_SHA512", None, "SHADOW", ValueError, "PBKDF2_SHA512 only supported with GRUB format"),
		("secret", "BCRYPT", None, "GRUB", ValueError, "BCRYPT only supported with SHADOW format"),
		("secret", "SHA512", None, "GRUB", ValueError, "SHA512 only supported with SHADOW format"),
		("secret", "MD5", None, None, ValueError, "Invalid value 'MD5' for password hash algorithm"),
		("secret", "ARGON2ID", 4, "SHADOW", None, None),
		(r"7ERlz[I|12by1ycIqe?ES6t`2r<F,y", "ARGON2ID", None, None, None, None),
		("secret", "ARGON2ID", 4, "GRUB", ValueError, "ARGON2ID only supported with SHADOW format"),
	),
)
def test_password_hash(
	generate_salt: bool,
	password: str,
	algorithm: str,
	rounds: int | None,
	format: str | None,
	expected_exception: type[Exception] | None,
	expected_exception_message: str | None,
) -> None:
	if algorithm == "SHA512" and not is_linux():
		pytest.skip("SHA512 hashing only supported on Linux")

	kwargs = {"password": password, "algorithm": algorithm, "rounds": rounds, "generate_salt": generate_salt}
	if format:
		kwargs["format"] = PasswordHashFormat(format)

	if expected_exception:
		with pytest.raises(expected_exception, match=expected_exception_message):
			hash_password(**kwargs)  # ty: ignore[invalid-argument-type]
		return

	password_hash = hash_password(**kwargs)  # ty: ignore[invalid-argument-type]
	password_hash2 = hash_password(**kwargs)  # ty: ignore[invalid-argument-type]
	if generate_salt:
		assert password_hash != password_hash2
	else:
		assert password_hash == password_hash2
	if PasswordHashAlgorithm(algorithm) == PasswordHashAlgorithm.PBKDF2_SHA512:
		assert password_hash.startswith("grub.pbkdf2.sha512")
		assert get_password_hash_algorithm(password_hash) == PasswordHashAlgorithm.PBKDF2_SHA512
		assert verify_password(password, password_hash)
		assert verify_password(password, password_hash, algorithm=algorithm)
		assert not verify_password("wrong_password", password_hash)
		return

	assert len(password_hash) <= 128
	assert password_hash.startswith("$")
	parts = password_hash.split("$")
	if PasswordHashAlgorithm(algorithm) == PasswordHashAlgorithm.BCRYPT:
		assert parts[1] == "2b"
		assert parts[2] == str(rounds or 12)
	elif PasswordHashAlgorithm(algorithm) == PasswordHashAlgorithm.SHA512:
		assert parts[1] == "6"
		if rounds:
			assert parts[2] == f"rounds={rounds}"

	alg = get_password_hash_algorithm(password_hash)
	assert alg.name == algorithm
	assert verify_password(password, password_hash)
	assert verify_password(password, password_hash, algorithm=alg)
	assert not verify_password("wrong_password", password_hash)


@pytest.mark.parametrize(
	"password_hash",
	(
		"grub.pbkdf2.sha512.10000.INVALID.0123",
		"grub.pbkdf2.sha512.10000.0123.INVALID",
		"grub.pbkdf2.sha256.10000.0123.0123",
	),
)
def test_verify_password_returns_false_for_invalid_pbkdf2_hash(password_hash: str) -> None:
	assert not verify_password("secret", password_hash, algorithm="PBKDF2_SHA512")
