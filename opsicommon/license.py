# -*- coding: utf-8 -*-

# Copyright (c) 2010-2021 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
"""
License handling
"""

import re
import json
import typing
import uuid
from datetime import date
import attr

OPSI_LICENSE_TYPES = ("core", "standard")
OPSI_LICENCE_ID_REGEX = re.compile(r"[a-zA-Z0-9\-_]{10,}")
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
	customer_id: str = attr.ib(
		validator=attr.validators.matches_re(r"[a-zA-Z0-9\-_]{5,}")
	)
	customer_name: str = attr.ib(
		validator=attr.validators.matches_re(r"\S.*\S")
	)
	customer_address: str = attr.ib(
		validator=attr.validators.matches_re(r"\S.*\S")
	)
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

	def str2date(value) -> date: # pylint: disable=no-self-argument
		if isinstance(value, str):
			return date.fromisoformat(value)
		return value
	issued_at: date = attr.ib(
		factory=date.today,
		converter=str2date,
		validator=attr.validators.instance_of(date)
	)
	# valid_from: 9999-12-31 = unlimited
	valid_from: date = attr.ib(
		factory=date.today,
		converter=str2date,
		validator=attr.validators.instance_of(date)
	)
	valid_until: date = attr.ib(
		converter=str2date,
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
	def hexstr2bytes(value) -> bytes: # pylint: disable=no-self-argument
		if isinstance(value, str):
			return bytes.fromhex(value)
		return value
	signature: bytes = attr.ib(
		default=None,
		converter=hexstr2bytes,
	)

	def to_json(self):
		res = attr.asdict(self)
		res["issued_at"] = str(res["issued_at"])
		res["valid_from"] = str(res["valid_from"])
		res["valid_until"] = str(res["valid_until"])
		if res["signature"]:
			res["signature"] = res["signature"].hex()
		return json.dumps(res)

def read_license_files(path: str) -> None:
	pass
