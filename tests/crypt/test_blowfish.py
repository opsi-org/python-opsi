# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

from opsi.crypt.blowfish import blowfish_decrypt, blowfish_encrypt
from opsi.crypt.secret import SecretAlphabet, generate_secret


def test_blowfish_encrypt_decrypt() -> None:
	key = generate_secret(length=16, alphabet=SecretAlphabet.HEXDIGITS)
	cleartext = "This is a test string."
	encrypted = blowfish_encrypt(key, cleartext)
	decrypted = blowfish_decrypt(key, encrypted)
	assert decrypted == cleartext


def test_blowfish_encrypt_decrypt_with_iv() -> None:
	key = generate_secret(length=16, alphabet=SecretAlphabet.HEXDIGITS)
	cleartext = "This is a test string with IV."
	iv = bytes.fromhex(generate_secret(length=16, alphabet=SecretAlphabet.HEXDIGITS))
	encrypted = blowfish_encrypt(key, cleartext, iv=iv)
	decrypted = blowfish_decrypt(key, encrypted, iv=iv)
	assert decrypted == cleartext
