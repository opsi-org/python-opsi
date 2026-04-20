# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from Crypto.Cipher import Blowfish

BLOWFISH_IV = b"OPSI1234"


class BlowfishError(Exception):
	pass


def blowfish_encrypt(key: str, cleartext: str | bytes, *, iv: bytes = BLOWFISH_IV) -> str:
	"""
	Takes `cleartext` string, returns hex-encoded,
	blowfish-encrypted string.
	`key` must a string of hexadecimal numbers.
	"""
	if not key:
		raise ValueError("Missing key")

	bkey = bytes.fromhex(key)
	if isinstance(cleartext, str):
		cleartext = cleartext.encode("utf-8")
	while len(cleartext) % 8 != 0:
		# Fill up with \0 until length is a mutiple of 8
		cleartext += b"\x00"

	blowfish = Blowfish.new(bkey, Blowfish.MODE_CBC, iv)
	return blowfish.encrypt(cleartext).hex()


def blowfish_decrypt(key: str, crypt: str, *, iv: bytes = BLOWFISH_IV) -> str:
	"""
	Takes hex-encoded, blowfish-encrypted string, returns cleartext string.
	"""
	if not key:
		raise ValueError("Missing key")

	bkey = bytes.fromhex(key)
	bcrypt = bytes.fromhex(crypt)
	blowfish = Blowfish.new(bkey, Blowfish.MODE_CBC, iv)
	# Remove possible \0-chars
	return blowfish.decrypt(bcrypt).rstrip(b"\0").decode("utf-8")
