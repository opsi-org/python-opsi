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
from datetime import date, timedelta
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

OPSI_MODULE_STATE_FREE = "free"
OPSI_MODULE_STATE_LICENSED = "licensed"
OPSI_MODULE_STATE_UNLICENSED = "unlicensed"
OPSI_MODULE_STATE_OVER_LIMIT = "over_limit"
OPSI_MODULE_STATE_CLOSE_TO_LIMIT = "close_to_limit"

CLIENT_LIMIT_THRESHOLD_PERCENT = 5
CLIENT_LIMIT_THRESHOLD_PERCENT_WARNING = 5

OPSI_MODULE_IDS = (
	"directory-connector",
	"dynamic_depot",
	"install_by_shutdown",
	"license_management",
	"linux_agent",
	"local_imaging",
	"macos_agent",
	"monitoring",
	"mysql_backend",
	"os_install_by_wlan",
	"roaming_profiles",
	"scalability1",
	"secureboot",
	"swondemand",
	"treeview",
	"uefi",
	"userroles",
	"vista",
	"wim-capture",
	"win-vhd",
	"vpn"
)


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


@lru_cache(maxsize=None)
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
		"MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAqTWmFj6m6O3gO676GStL\n"
		"Kk388kPxRRvQ7uoieSyafmwmsxxGiRQ6ifM+I2m8o3Gk5wEVBI+UU2jIZONTvNOP\n"
		"RbSmm96NEfHMUbnwwNwn5J5j8a9NpT6/sthEzptevgm6inCIpGlnhD03/Qaqx5qn\n"
		"81kczHMIcfYjpzgIRK7xBdG7XEpgVzsdwVI5EgBoX651n6TgJ5nHIYlOwhmF6L3W\n"
		"y/LEF4vQ5amESMTQ5eOR9xEfZoUgeyt15JLl9TUBQqoSx8nkS+O2o+qYF9wiFaFm\n"
		"ZqmPuNFbk1fM1BrsqrBMFVrzx6mRFdDfAdpqtxfFaOWTLwGGFaOEi2k39EVgnc6Z\n"
		"8QIDAQAB\n"
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
		if (
			self.schema_version > 1 and
			self.type != OPSI_LICENSE_TYPE_CORE and
			not re.match(r"[a-zA-Z0-9\-_]{5,}", value)
		):
			raise ValueError(f"Invalid value for {attribute}", value)

	customer_name: str = attr.ib()
	@customer_name.validator
	def validate_customer_name(self, attribute, value):
		if (
			self.type != OPSI_LICENSE_TYPE_CORE and
			not re.match(r"\S.*\S", value)
		):
			raise ValueError(f"Invalid value for {attribute}", value)

	customer_address: str = attr.ib(
		default=None
	)
	@customer_address.validator
	def validate_customer_address(self, attribute, value):
		if (
			self.schema_version > 1 and
			self.type != OPSI_LICENSE_TYPE_CORE and
			not re.match(r"\S.*\S", value)
		):
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
			for lic in self._license_pool.get_licenses(
				exclude_ids=[self.id],
				valid_only=True,
				test_revoked=False,
				at_date=at_date
			):
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
					value = OPSI_LICENSE_DATE_UNLIMITED
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
	def __init__(
		self,
		license_file_path: str = None,
		modules_file_path: str = None,
		client_info: typing.Union[dict, typing.Callable] = None
	) -> None:
		self.license_file_path: str = license_file_path
		self.modules_file_path: str = modules_file_path
		self._client_info: typing.Union[dict, typing.Callable] = client_info
		self._licenses: typing.Dict[str, OpsiLicense] = {}

	@property
	def licenses(self):
		return list(self.get_licenses())

	@property
	def client_numbers(self):
		client_numbers = {}
		if callable(self._client_info):
			client_numbers = self._client_info()
		elif self._client_info:
			client_numbers = dict(self._client_info)
		client_numbers["all"] = 0
		for client_type in ("windows", "linux", "macos"):
			if not client_type in client_numbers:
				client_numbers[client_type] = 0
			client_numbers["all"] += client_numbers[client_type]
		return client_numbers

	def get_licenses(
		self,
		exclude_ids: typing.List[str] = None,
		valid_only: bool = False,
		test_revoked: bool = True,
		at_date: date = None
	):
		if not at_date:
			at_date = date.today()

		for lic in self._licenses.values():
			if exclude_ids and lic.id in exclude_ids:
				continue
			if (
				valid_only and
				lic.get_state(test_revoked=test_revoked, at_date=at_date) != OPSI_LICENSE_STATE_VALID
			):
				continue
			yield lic

	def add_license(self, *opsi_license: OpsiLicense) -> None:
		for lic in opsi_license:
			lic.set_license_pool(self)
			self._licenses[lic.id] = lic

	def get_revoked_license_ids(self, at_date: date = None) -> typing.Set[str]:
		if not at_date:
			at_date = date.today()
		revoked_ids = set()
		for lic in self._licenses.values():
			if lic.get_state(test_revoked=False, at_date=at_date) == OPSI_LICENSE_STATE_VALID:
				for revoked_id in lic.revoked_ids:
					revoked_ids.add(revoked_id)
		return revoked_ids

	def get_relevant_dates(self) -> typing.Set[date]:
		dates = set()
		for lic in self.get_licenses():
			if lic.get_state() != OPSI_LICENSE_STATE_INVALID_SIGNATURE:
				if lic.valid_from != OPSI_LICENSE_DATE_UNLIMITED:
					dates.add(lic.valid_from)
				if lic.valid_until != OPSI_LICENSE_DATE_UNLIMITED:
					dates.add(lic.valid_until + timedelta(days=1))
		return sorted(dates)

	def get_modules(self, at_date: date = None):
		if not at_date:
			at_date = date.today()

		client_numbers = self.client_numbers
		modules = {}
		for module_id in OPSI_MODULE_IDS:
			if module_id in ("treeview", "vista"):
				modules[module_id] = {
					"available": True,
					"state": OPSI_MODULE_STATE_FREE,
					"license_ids": [],
					"client_number": 999999999
				}
			else:
				modules[module_id] = {
					"available": False,
					"state": OPSI_MODULE_STATE_UNLICENSED,
					"license_ids": [],
					"client_number": 0
				}

		for lic in self.get_licenses(valid_only=True, at_date=at_date):
			if lic.module_id not in modules:
				modules[lic.module_id] = {
					"client_number": 0,
					"license_ids": []
				}
			modules[lic.module_id]["available"] = True
			modules[lic.module_id]["state"] = OPSI_MODULE_STATE_LICENSED
			modules[lic.module_id]["license_ids"].append(lic.id)
			modules[lic.module_id]["license_ids"].sort()
			modules[lic.module_id]["client_number"] += lic.client_number
			modules[lic.module_id]["client_number"] = min(
				modules[lic.module_id]["client_number"],
				OPSI_LICENSE_CLIENT_NUMBER_UNLIMITED
			)

		for module_id, info in modules.items():
			if info["state"] != OPSI_MODULE_STATE_LICENSED:
				continue

			client_number = client_numbers["all"]
			if module_id == "linux_agent":
				client_number = client_numbers["linux"]
			elif module_id == "macos_agent":
				client_number = client_numbers["macos"]
			#elif module_id == "vpn":
			#	client_number = client_numbers["vpn"]

			usage_percent = client_number * 100 / info["client_number"]
			if usage_percent > 100 + CLIENT_LIMIT_THRESHOLD_PERCENT:
				info["state"] = OPSI_MODULE_STATE_OVER_LIMIT
				info["available"] = False
			elif usage_percent > 100:
				info["state"] = OPSI_MODULE_STATE_OVER_LIMIT
			elif usage_percent > 100 - CLIENT_LIMIT_THRESHOLD_PERCENT_WARNING:
				info["state"] = OPSI_MODULE_STATE_CLOSE_TO_LIMIT

		return modules

	def get_legacy_modules(self):
		for lic in self.get_licenses():
			if lic.schema_version == 1:
				modules = {
					"signature": lic.signature.hex()
				}
				for line in lic.additional_data.split("\r\n"):
					if line.strip():
						attribute, value = line.split('=', 1)
						attribute = attribute.strip()
						value = value.strip()
						if attribute != "customer":
							try:
								value = int(value)
							except ValueError:
								pass
						modules[attribute] = value
				return modules
		return None

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


default_opsi_license_pool = None  # pylint: disable=invalid-name
def get_default_opsi_license_pool(
	license_file_path: str = None,
	modules_file_path: str = None,
	client_info: typing.Union[dict, typing.Callable] = None
):
	global default_opsi_license_pool  # pylint: disable=invalid-name,global-statement
	if not default_opsi_license_pool:
		default_opsi_license_pool = OpsiLicensePool(
			license_file_path=license_file_path,
			modules_file_path=modules_file_path,
			client_info=client_info
		)
		default_opsi_license_pool.load()
	return default_opsi_license_pool
