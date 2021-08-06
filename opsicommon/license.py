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
	from Cryptodome.Signature import pss
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Hash import MD5, SHA3_512
	from Crypto.PublicKey import RSA
	from Crypto.Util.number import bytes_to_long
	from Crypto.Signature import pss


OPSI_LICENCE_ID_REGEX = re.compile(r"[a-zA-Z0-9\-_]{10,}")

OPSI_LICENSE_TYPE_CORE = "core"
OPSI_LICENSE_TYPE_STANDARD = "standard"

OPSI_LICENSE_STATE_VALID = "valid"
OPSI_LICENSE_STATE_INVALID_SIGNATURE = "invalid_signature"
OPSI_LICENSE_STATE_EXPIRED = "expired"
OPSI_LICENSE_STATE_NOT_YET_VALID = "not_yet_valid"
OPSI_LICENSE_STATE_REVOKED = "revoked"
OPSI_LICENSE_STATE_REPLACED_BY_NON_CORE = "replaced_by_non_core"

OPSI_LICENSE_DATE_UNLIMITED = date.fromisoformat("9999-12-31")
OPSI_LICENSE_CLIENT_NUMBER_UNLIMITED = 999999999

def _str2date(value) -> date:
	if isinstance(value, str):
		return date.fromisoformat(value)
	return value


def _hexstr2bytes(value) -> bytes:
	if isinstance(value, str):
		return bytes.fromhex(value)
	return value


def generate_key_pair(bits: int = 2048, return_pem: int = False) -> typing.List[str]:
	key = RSA.generate(bits=bits)
	if not return_pem:
		return key, key.publickey()

	private_key = key.export_key()
	public_key = key.publickey().export_key()
	return private_key.decode(), public_key.decode()


@lru_cache
def get_signature_public_key(schema_version: int):
	if schema_version < 2:
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

	return RSA.import_key(
		"-----BEGIN PUBLIC KEY-----\n"
		"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAr6FLWzpAyZP43Y6VeDKu\n"
		"vmxg3OWCXxG0sAV9dXQ/o6cSq5xQyIv+aFbivtYmNjcH370bYjK7+sQ69fPH3x9t\n"
		"73t6c5ntpxQoIDDhgcnjp22TfNYEJDhH9YPXdJDdPJUjUBML+9vWq7YTgx7gCK3f\n"
		"EBjGC3UsZ4oDWdkoO65JO2cqBRDz8gvfpQuqne7XU3FwUfVTh5hrADbf7lZ/VMQU\n"
		"UQnqE2RwMvL43jSGZvZiIMfDua/l0oXLrpxqOLS9qS33zhwmx9sVt5dkbZQH/cRV\n"
		"yqkdwMLbYmg9jMaYrF7/UWUG757c/fZyaY2yCESUXN3obiCXza6DNEOSqa49Hb9A\n"
		"DQIDAQAB\n"
		"-----END PUBLIC KEY-----\n"
	)

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

	_license_pool: 'OpsiLicensePool' = attr.ib(
		default=None
	)

	def set_license_pool(self, license_pool: 'OpsiLicensePool'):
		self._license_pool = license_pool

	def to_dict(self, serializable: bool = False, with_state: bool = False) -> dict:
		res = attr.asdict(self)
		del res["_license_pool"]
		if with_state:
			res["_state"] = self.get_state()
		if serializable:
			res["issued_at"] = str(res["issued_at"])
			res["valid_from"] = str(res["valid_from"])
			res["valid_until"] = str(res["valid_until"])
			if res["signature"]:
				res["signature"] = res["signature"].hex()
		return res

	@classmethod
	def from_dict(cls, data_dict: dict) -> 'OpsiLicense':
		data_dict = dict(data_dict)
		for attribute in list(data_dict):
			if attribute.startswith("_"):
				del data_dict[attribute]
		return OpsiLicense(**data_dict)

	def to_json(self, with_state: bool = False) -> str:
		return json.dumps(self.to_dict(serializable=True, with_state=with_state))

	@classmethod
	def from_json(cls, json_data: str) -> 'OpsiLicense':
		return OpsiLicense.from_dict(json.loads(json_data))

	def get_hash(self, digest: bool = False, hex_digest: bool = False):
		_hash = None
		if self.schema_version == 1:
			_hash = MD5.new(self.additional_data.encode("utf-8"))
		else:
			string = ""
			data = self.to_dict(serializable=True, with_state=False)
			for attribute in sorted(data):
				if attribute == "signature" or attribute.startswith("_"):
					continue
				value = data[attribute]
				if isinstance(value, list):
					value = ",".join(sorted(value))
				string += f"{attribute}={json.dumps(value)}\n"
			_hash = SHA3_512.new(string.encode("utf-8"))

		if hex_digest:
			return _hash.hexdigest()
		if digest:
			return _hash.digest()
		return _hash

	def get_state(self, test_revoked: bool = True, at_date: date = None) -> str:  # pylint: disable=too-many-return-statements
		if not at_date:
			at_date = date.today()
		_hash = self.get_hash()
		public_key = get_signature_public_key(self.schema_version)
		if self.schema_version == 1:
			h_int = int.from_bytes(_hash.digest(), "big")
			s_int = public_key._encrypt(int(self.signature.hex()))  # pylint: disable=protected-access
			if h_int != s_int:
				return OPSI_LICENSE_STATE_INVALID_SIGNATURE
		else:
			try:
				pss.new(public_key).verify(_hash, self.signature)
			except (ValueError, TypeError):
				return OPSI_LICENSE_STATE_INVALID_SIGNATURE

		if self.type == OPSI_LICENSE_TYPE_CORE and self._license_pool:
			for lic in self._license_pool.get_licenses(exclude_ids=[self.id], valid_only=True, test_revoked=False):
				if lic.type != OPSI_LICENSE_TYPE_CORE and lic.module_id == self.module_id:
					return OPSI_LICENSE_STATE_REPLACED_BY_NON_CORE
		if test_revoked and self._license_pool and self.id in self._license_pool.get_revoked_license_ids():
			return OPSI_LICENSE_STATE_REVOKED
		if (self.valid_from - at_date).days > 0:
			return OPSI_LICENSE_STATE_NOT_YET_VALID
		if (self.valid_until - at_date).days < 0:
			return OPSI_LICENSE_STATE_EXPIRED
		return OPSI_LICENSE_STATE_VALID

	def sign(self, private_key: typing.Union[RSA.RsaKey, str]):
		if self.schema_version < 2:
			raise NotImplementedError("Signing for schema_version < 2 not implemented")
		if isinstance(private_key, str):
			private_key = RSA.import_key(str.encode("ascii"))
		self.signature = pss.new(private_key).sign(self.get_hash())

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
						client_number = OPSI_LICENSE_CLIENT_NUMBER_UNLIMITED
				if client_number > 0:
					modules[module_id] = client_number

		for module_id, client_number in modules.items():
			kwargs = dict(common_lic)
			kwargs["id"] = f"legacy-{module_id}"
			kwargs["module_id"] = module_id
			kwargs["client_number"] = client_number
			self.add_license(OpsiLicense(**kwargs))

class OpsiLicensePool:
	def __init__(self, license_file_path: str = None, modules_file_path: str = None) -> None:
		self.license_file_path: str = license_file_path
		self.modules_file_path: str = modules_file_path
		self._licenses: typing.Dict[str, OpsiLicense] = {}

	@property
	def licenses(self):
		return list(self.get_licenses())

	def get_licenses(self, exclude_ids: typing.List[str] = None, valid_only: bool = False, test_revoked: bool = True):
		for lic in self._licenses.values():
			if exclude_ids and lic.id in exclude_ids:
				continue
			if valid_only and lic.get_state(test_revoked=test_revoked) != OPSI_LICENSE_STATE_VALID:
				continue
			yield lic

	def add_license(self, *opsi_license: OpsiLicense) -> None:
		for lic in opsi_license:
			lic.set_license_pool(self)
			self._licenses[lic.id] = lic

	def get_revoked_license_ids(self) -> typing.Set[str]:
		revoked_ids = set()
		for lic in self._licenses.values():
			if lic.get_state(test_revoked=False) == OPSI_LICENSE_STATE_VALID:
				for revoked_id in lic.revoked_ids:
					revoked_ids.add(revoked_id)
		return revoked_ids

	def get_dates(self) -> typing.Set[date]:
		dates = set()
		for lic in self.get_licenses():
			if lic.get_state() != OPSI_LICENSE_STATE_INVALID_SIGNATURE:
				if lic.valid_from != OPSI_LICENSE_DATE_UNLIMITED:
					dates.add(lic.valid_from)
				if lic.valid_until != OPSI_LICENSE_DATE_UNLIMITED:
					dates.add(lic.valid_until)
		return sorted(dates)

	def _read_license_files(self) -> None:
		license_files = [self.license_file_path]
		if os.path.isdir(self.license_file_path):
			license_files = glob.glob(os.path.join(self.license_file_path, "*.opsilic"))

		for license_file in license_files:
			olf = OpsiLicenseFile(license_file)
			olf.read()
			self.add_license(*olf.licenses)

	def _read_modules_file(self) -> None:
		omf = OpsiModulesFile(self.modules_file_path)
		omf.read()
		self.add_license(*omf.licenses)

	def load(self):
		self._licenses = {}
		if self.license_file_path:
			self._read_license_files()
		if self.modules_file_path:
			self._read_modules_file()


default_opsi_license_pool = OpsiLicensePool()
