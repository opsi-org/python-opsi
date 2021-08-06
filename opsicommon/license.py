# -*- coding: utf-8 -*-

# Copyright (c) 2010-2021 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
"""
License handling
"""

import re
import os
import ast
import glob
import json
import uuid
import typing
import struct
import base64
import codecs
import configparser
from functools import lru_cache
from datetime import date
import attr
try:
	# pyright: reportMissingImports=false
	# python3-pycryptodome installs into Cryptodome
	from Cryptodome.Hash import MD5, SHA3_512
	from Cryptodome.PublicKey import RSA
	from Cryptodome.Util.number import bytes_to_long
	from Cryptodome.Signature import pkcs1_15
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Hash import MD5, SHA3_512
	from Crypto.PublicKey import RSA
	from Crypto.Util.number import bytes_to_long
	from Crypto.Signature import pkcs1_15

OPSI_LICENCE_ID_REGEX = re.compile(r"[a-zA-Z0-9\-_]{10,}")

OPSI_LICENSE_TYPE_CORE = "core"
OPSI_LICENSE_TYPE_STANDARD = "standard"

OPSI_LICENSE_STATE_VALID = "valid"
OPSI_LICENSE_STATE_INVALID_SIGNATURE = "invalid_signature"
OPSI_LICENSE_STATE_EXPIRED = "expired"
OPSI_LICENSE_STATE_NOT_YET_VALID = "not_yet_valid"


def _str2date(value) -> date:
	if isinstance(value, str):
		return date.fromisoformat(value)
	return value


def _hexstr2bytes(value) -> bytes:
	if isinstance(value, str):
		return bytes.fromhex(value)
	return value

@lru_cache
def get_signature_public_key():
	data = base64.decodebytes(
		b"AAAAB3NzaC1yc2EAAAADAQABAAABAQCAD/I79Jd0eKwwfuVwh5B2z+S8aV0C5suItJa18RrYip+d4P0ogzqoCfOoVWtDo"
		b"jY96FDYv+2d73LsoOckHCnuh55GA0mtuVMWdXNZIE8Avt/RzbEoYGo/H0weuga7I8PuQNC/nyS8w3W8TH4pt+ZCjZZoX8"
		b"S+IizWCYwfqYoYTMLgB0i+6TCAfJj3mNgCrDZkQ24+rOFS4a8RrjamEz/b81noWl9IntllK1hySkR+LbulfTGALHgHkDU"
		b"lk0OSu+zBPw/hcDSOMiDQvvHfmR4quGyLPbQ2FOVm1TzE0bQPR+Bhx4V8Eo2kNYstG2eJELrz7J1TJI0rCjpB+FQjYPsP"
	)

	# Key type can be found in 4:11.
	rest = data[11:]
	count = 0
	mp = []
	for _ in range(2):
		length = struct.unpack('>L', rest[count:count + 4])[0]
		mp.append(bytes_to_long(rest[count + 4:count + 4 + length]))
		count += 4 + length

	return RSA.construct((mp[1], mp[0]))

@attr.s(slots=True, auto_attribs=True, kw_only=True)
class OpsiLicense: # pylint: disable=too-few-public-methods,too-many-instance-attributes
	id: str = attr.ib( # pylint: disable=invalid-name
		factory=lambda: str(uuid.uuid4()),
		validator=attr.validators.matches_re(OPSI_LICENCE_ID_REGEX)
	)

	type: str = attr.ib(
		default=OPSI_LICENSE_TYPE_STANDARD,
		validator=attr.validators.in_((OPSI_LICENSE_TYPE_CORE, OPSI_LICENSE_TYPE_STANDARD))
	)

	schema_version: int = attr.ib(
		default=2,
		converter=int
	)
	@schema_version.validator
	def validate_schema_version(self, attribute, value): # pylint: disable=no-self-use
		if not isinstance(value, int) or value <= 0:
			raise ValueError(f"Invalid value for {attribute}", value)

	opsi_version: str = attr.ib(
		default="4.2",
		validator=attr.validators.matches_re(r"\d+\.\d+")
	)

	customer_id: str = attr.ib(
		default=None
	)
	@customer_id.validator
	def validate_customer_id(self, attribute, value):
		if self.schema_version > 1 and not re.match(r"[a-zA-Z0-9\-_]{5,}", value):
			raise ValueError(f"Invalid value for {attribute}", value)

	customer_name: str = attr.ib(
		validator=attr.validators.matches_re(r"\S.*\S")
	)

	customer_address: str = attr.ib(
		default=None
	)
	@customer_address.validator
	def validate_customer_address(self, attribute, value):
		if self.schema_version > 1 and not re.match(r"\S.*\S", value):
			raise ValueError(f"Invalid value for {attribute}", value)

	module_id: str = attr.ib(
		validator=attr.validators.matches_re(r"[a-z0-9\-_]+")
	)

	# client_number: 999999999 = unlimited
	client_number: int = attr.ib(
		converter=int,
		validator=attr.validators.instance_of(int)
	)
	@client_number.validator
	def validate_client_number(self, attribute, value): # pylint: disable=no-self-use
		if value <= 0:
			raise ValueError(f"Invalid value for {attribute}", value)

	issued_at: date = attr.ib(
		factory=date.today,
		converter=_str2date,
		validator=attr.validators.instance_of(date)
	)

	# valid_from: 9999-12-31 = unlimited
	valid_from: date = attr.ib(
		factory=date.today,
		converter=_str2date,
		validator=attr.validators.instance_of(date)
	)

	valid_until: date = attr.ib(
		converter=_str2date,
		validator=attr.validators.instance_of(date)
	)

	revoked_ids: typing.List[str] = attr.ib(
		default=[]
	)
	@revoked_ids.validator
	def validate_revoked_ids(self, attribute, value): # pylint: disable=no-self-use
		if not isinstance(value, list):
			raise ValueError(f"Invalid value for {attribute}", value)
		for val in value:
			if not OPSI_LICENCE_ID_REGEX.match(val):
				raise ValueError(f"Invalid value for {attribute}", val)

	note: str = attr.ib(
		default=None
	)

	signature: bytes = attr.ib(
		default=None,
		converter=_hexstr2bytes,
	)

	additional_data: str = attr.ib(
		default=None
	)

	def to_dict(self, serializable: bool = False) -> dict:
		res = attr.asdict(self)
		if serializable:
			res["issued_at"] = str(res["issued_at"])
			res["valid_from"] = str(res["valid_from"])
			res["valid_until"] = str(res["valid_until"])
			if res["signature"]:
				res["signature"] = res["signature"].hex()
		return res

	@classmethod
	def from_dict(cls, data_dict: dict) -> 'OpsiLicense':
		return OpsiLicense(**data_dict)

	def to_json(self) -> str:
		return json.dumps(self.to_dict(serializable=True))

	@classmethod
	def from_json(cls, json_data: str) -> 'OpsiLicense':
		return OpsiLicense.from_dict(json.loads(json_data))

	def get_hash(self, digest: bool = False, hex_digest: bool = False):
		_hash = None
		if self.schema_version == 1:
			_hash = MD5.new(self.additional_data.encode("utf-8"))
		else:
			_hash = SHA3_512.new(self.to_json().encode("utf-8"))

		if hex_digest:
			return _hash.hexdigest()
		if digest:
			return _hash.digest()
		return _hash

	def get_state(self):
		public_key = get_signature_public_key()
		_hash = self.get_hash()
		if self.schema_version == 1:
			h_int = int.from_bytes(_hash.digest(), "big")
			s_int = public_key._encrypt(int(self.signature.hex()))  # pylint: disable=protected-access
			if h_int != s_int:
				return OPSI_LICENSE_STATE_INVALID_SIGNATURE
		else:
			#s_bytes = int(modules['signature'].split("}", 1)[-1]).to_bytes(256, "big")
			pkcs1_15.new(public_key).verify(_hash, self.signature)

		if (date.today() - self.valid_from).days < 0:
			return OPSI_LICENSE_STATE_NOT_YET_VALID
		if (date.today() - self.valid_until).days < 0:
			return OPSI_LICENSE_STATE_EXPIRED
		return OPSI_LICENSE_STATE_VALID

class OpsiLicenseFile:
	def __init__(self, filename: str) -> None:
		self.filename: str = filename
		self._licenses: typing.Dict[str, OpsiLicense] = {}

	@property
	def licenses(self):
		return list(self._licenses.values())

	def add_license(self, opsi_license: OpsiLicense) -> None:
		self._licenses[opsi_license.id] = opsi_license

	def read(self):
		ini = configparser.ConfigParser()
		ini.read(self.filename, encoding="utf-8")
		for section in ini.sections():
			kwargs = dict(ini.items(section=section, raw=True))
			kwargs["revoked_ids"] = [x.strip() for x in kwargs.get("revoked_ids", "").split(",") if x]
			kwargs["note"] = ast.literal_eval(f'"{kwargs.get("note")}"') or None
			kwargs["id"] = section
			self.add_license(OpsiLicense(**kwargs))


def read_license_files(path: str) -> typing.List[OpsiLicense]:
	license_files = [path]
	if os.path.isdir(path):
		license_files = glob.glob(os.path.join(path, "*.opsilic"))

	licenses = []
	for license_file in license_files:
		olf = OpsiLicenseFile(license_file)
		olf.read()
		for lic in olf.licenses:
			licenses.append(lic)
	return licenses

class OpsiModulesFile:  # pylint: disable=too-few-public-methods
	def __init__(self, filename: str) -> None:
		self.filename: str = filename
		self._licenses: typing.Dict[str, OpsiLicense] = {}

	@property
	def licenses(self):
		return list(self._licenses.values())

	def add_license(self, opsi_license: OpsiLicense) -> None:
		self._licenses[opsi_license.id] = opsi_license

	def _read_raw_data(self):
		data = {}
		with codecs.open(self.filename, 'r', 'utf-8') as file:
			for line in file:
				line = line.strip()
				if '=' not in line:
					continue
				(attribute, value) = line.split('=', 1)
				attribute = attribute.strip().lower()
				value = value.strip()
				if attribute != "customer":
					value = value.lower()
				data[attribute] = value
		return data

	def read(self):
		data = self._read_raw_data()
		common_lic = {
			"type": OPSI_LICENSE_TYPE_STANDARD,
			"schema_version": 1,
			"opsi_version": "4.1",
			"additional_data": ""
		}
		modules = {}
		for attribute in sorted(data):
			value = data[attribute]
			if attribute != "signature":
				common_lic["additional_data"] += f"{attribute} = {value}\r\n"

			if attribute == "signature":
				common_lic["signature"] = value
			elif attribute == "customer":
				common_lic["customer_name"] = value
			elif attribute == "expires":
				if value == 'never':
					value = "2999-12-31"
				common_lic["valid_until"] = value
			else:
				module_id = attribute.lower()
				client_number = 0
				try:
					client_number = int(value)
				except ValueError:
					if value == "yes":
						client_number = 999999999
				if client_number > 0:
					modules[module_id] = client_number

		for module_id, client_number in modules.items():
			kwargs = dict(common_lic)
			kwargs["id"] = f"legacy-{module_id}"
			kwargs["module_id"] = module_id
			kwargs["client_number"] = client_number
			self.add_license(OpsiLicense(**kwargs))


def read_modules_file(filename: str) -> typing.List[OpsiLicense]:
	omf = OpsiModulesFile(filename)
	omf.read()
	return omf.licenses
