# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import random
import secrets
import string
from enum import StrEnum
from typing import Iterable

from opsi.logging import secret_filter


class SecretAlphabet(StrEnum):
	ascii_lowercase = "ascii_lowercase"
	ascii_uppercase = "ascii_uppercase"
	ascii_letters = "ascii_letters"
	digits = "digits"
	hexdigits = "hexdigits"
	octdigits = "octdigits"
	punctuation = "punctuation"
	printable = "printable"

def generate_secret(length: int = 32, alphabet: Iterable[SecretAlphabet|str] | SecretAlphabet | str | None = None, required_chars: str | list[str] | tuple[str] | None = None) -> str:
	"""Generates a random secret string of the specified length."""
	if required_chars is not None:
		if isinstance(required_chars, str):
			required_chars = list(required_chars)
		if len(required_chars) > length:
			raise ValueError("Length of required characters cannot be greater than the total length of the secret.")
		length -= len(required_chars)

	if not alphabet:
		alphabet = string.ascii_letters + string.digits
	elif isinstance(alphabet, SecretAlphabet):
		alphabet = getattr(string, alphabet.value)
	elif isinstance(alphabet, Iterable):
		alphabet = "".join(getattr(string, a.value) if isinstance(a, SecretAlphabet) else a for a in alphabet)
	else:
		alphabet = str(alphabet)

	secret_chars = [secrets.choice(alphabet) for _ in range(length)]
	if required_chars is not None:
		secret_chars += required_chars
		random.shuffle(secret_chars)
	secret = "".join(secret_chars)
	secret_filter.add_secrets(secret)
	return secret
