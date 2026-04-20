# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import string
from collections.abc import Iterator
from typing import Any, cast

import pytest

import opsi.crypt.secret._secret as secret_module
from opsi.crypt.secret import SecretAlphabet, generate_secret


def test_generate_secret_uses_default_alphabet_and_registers_secret(monkeypatch: pytest.MonkeyPatch) -> None:
	registered_secrets: list[str] = []
	used_alphabets: list[str] = []

	def add_secrets(*secrets_to_add: str) -> None:
		registered_secrets.extend(secrets_to_add)

	def choice(alphabet: str) -> str:
		used_alphabets.append(alphabet)
		return alphabet[0]

	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", add_secrets)
	monkeypatch.setattr(secret_module.secrets, "choice", choice)

	secret = generate_secret(length=4)

	assert secret == "aaaa"
	assert used_alphabets == [string.ascii_letters + string.digits] * 4
	assert registered_secrets == [secret]


def test_generate_secret_uses_secret_alphabet_enum(monkeypatch: pytest.MonkeyPatch) -> None:
	used_alphabets: list[str] = []

	def choice(alphabet: str) -> str:
		used_alphabets.append(alphabet)
		return alphabet[-1]

	monkeypatch.setattr(secret_module.secrets, "choice", choice)
	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", lambda *_args: None)

	secret = generate_secret(length=3, alphabet=SecretAlphabet.DIGITS)

	assert secret == "999"
	assert used_alphabets == [string.digits] * 3


def test_generate_secret_combines_iterable_alphabets(monkeypatch: pytest.MonkeyPatch) -> None:
	combined_alphabet = string.ascii_lowercase + "._" + string.digits
	used_alphabets: list[str] = []

	def choice(alphabet: str) -> str:
		used_alphabets.append(alphabet)
		return alphabet[1]

	monkeypatch.setattr(secret_module.secrets, "choice", choice)
	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", lambda *_args: None)

	secret = generate_secret(length=3, alphabet=cast(Any, (SecretAlphabet.ASCII_LOWERCASE, "._", SecretAlphabet.DIGITS)))

	assert secret == "bbb"
	assert used_alphabets == [combined_alphabet] * 3


@pytest.mark.parametrize(
	("required_chars", "expected_secret"),
	[
		("ab", "zzab"),
		(["a", "b"], "zzab"),
		(("a", "b"), "zzab"),
	],
)
def test_generate_secret_supports_required_chars_collections(
	monkeypatch: pytest.MonkeyPatch,
	required_chars: str | list[str] | tuple[str, ...],
	expected_secret: str,
) -> None:
	def choice(_alphabet: str) -> str:
		return "z"

	def shuffle(_secret_chars: list[str]) -> None:
		return None

	monkeypatch.setattr(secret_module.secrets, "choice", choice)
	monkeypatch.setattr(secret_module.random, "shuffle", shuffle)
	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", lambda *_args: None)

	secret = generate_secret(length=4, alphabet="xyz", required_chars=cast(Any, required_chars))

	assert secret == expected_secret


def test_generate_secret_shuffles_required_chars_into_result(monkeypatch: pytest.MonkeyPatch) -> None:
	registered_secrets: list[str] = []
	shuffle_input: list[str] = []
	generated_chars: Iterator[str] = iter(["x", "y"])

	def choice(_alphabet: str) -> str:
		return next(generated_chars)

	def shuffle(secret_chars: list[str]) -> None:
		shuffle_input.extend(secret_chars)
		secret_chars.reverse()

	def add_secrets(*secrets_to_add: str) -> None:
		registered_secrets.extend(secrets_to_add)

	monkeypatch.setattr(secret_module.secrets, "choice", choice)
	monkeypatch.setattr(secret_module.random, "shuffle", shuffle)
	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", add_secrets)

	secret = generate_secret(length=4, alphabet="xyz", required_chars="AB")

	assert shuffle_input == ["x", "y", "A", "B"]
	assert secret == "BAyx"
	assert sorted(secret) == ["A", "B", "x", "y"]
	assert registered_secrets == [secret]


def test_generate_secret_skips_random_generation_when_required_chars_fill_length(monkeypatch: pytest.MonkeyPatch) -> None:
	def choice(_alphabet: str) -> str:
		raise AssertionError("secrets.choice must not be called")

	def shuffle(_secret_chars: list[str]) -> None:
		return None

	monkeypatch.setattr(secret_module.secrets, "choice", choice)
	monkeypatch.setattr(secret_module.random, "shuffle", shuffle)
	monkeypatch.setattr(secret_module.secret_filter, "add_secrets", lambda *_args: None)

	secret = generate_secret(length=2, required_chars=cast(Any, ("a", "b")))

	assert secret == "ab"


def test_generate_secret_raises_if_required_chars_exceed_length() -> None:
	with pytest.raises(ValueError, match="Length of required characters cannot be greater than the total length of the secret"):
		generate_secret(length=1, required_chars="ab")
