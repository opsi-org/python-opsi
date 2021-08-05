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
import typing
import uuid
import hashlib
import configparser
from datetime import date
import attr

OPSI_LICENSE_TYPES = ("core", "standard")
OPSI_LICENCE_ID_REGEX = re.compile(r"[a-zA-Z0-9\-_]{10,}")


def _str2date(value) -> date:
	if isinstance(value, str):
		return date.fromisoformat(value)
	return value


def _hexstr2bytes(value) -> bytes:
	if isinstance(value, str):
		return bytes.fromhex(value)
	return value

@attr.s(slots=True, auto_attribs=True, kw_only=True)
class OpsiLicense: # pylint: disable=too-few-public-methods,too-many-instance-attributes
	id: str = attr.ib( # pylint: disable=invalid-name
		factory=lambda: str(uuid.uuid4()),
		validator=attr.validators.matches_re(OPSI_LICENCE_ID_REGEX)
	)

	type: str = attr.ib(
		default="standard",
		validator=attr.validators.in_(OPSI_LICENSE_TYPES)
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

	customer_id: str = attr.ib()
	@customer_id.validator
	def validate_customer_id(self, attribute, value):
		if self.schema_version > 1 and not re.match(r"[a-zA-Z0-9\-_]{5,}", value):
			raise ValueError(f"Invalid value for {attribute}", value)

	customer_name: str = attr.ib(
		validator=attr.validators.matches_re(r"\S.*\S")
	)

	customer_address: str = attr.ib()
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

	def to_json(self):
		res = attr.asdict(self)
		res["issued_at"] = str(res["issued_at"])
		res["valid_from"] = str(res["valid_from"])
		res["valid_until"] = str(res["valid_until"])
		if res["signature"]:
			res["signature"] = res["signature"].hex()
		return json.dumps(res)

	def get_hash(self):
		return hashlib.sha512(self.to_json().encode("utf-8")).hexdigest()

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


def read_license_files(path: str) -> None:
	license_files = [path]
	if os.path.isdir(path):
		license_files = glob.glob(os.path.join(path, "*.opsilic"))
	for license_file in license_files:
		olf = OpsiLicenseFile(license_file)
		olf.read()
		for lic in olf.licenses:
			yield lic
