# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
This file is part of opsi - https://www.opsi.org
"""

import codecs
import json
import pathlib
from datetime import date, timedelta
from unittest import mock
import pytest

from opsicommon.license import (
	OPSI_MODULE_STATE_CLOSE_TO_LIMIT,
	OPSI_MODULE_STATE_OVER_LIMIT,
	generate_key_pair,
	OpsiLicense, OpsiModulesFile, OpsiLicensePool,
	OPSI_LICENSE_STATE_REPLACED_BY_NON_CORE,
	OPSI_LICENSE_STATE_VALID,
	OPSI_LICENSE_STATE_INVALID_SIGNATURE,
	OPSI_LICENSE_STATE_EXPIRED,
	OPSI_LICENSE_STATE_NOT_YET_VALID,
	OPSI_LICENSE_STATE_REVOKED,
	OPSI_LICENSE_TYPE_CORE,
	OPSI_LICENSE_TYPE_STANDARD,
	OPSI_MODULE_STATE_FREE,
	OPSI_MODULE_STATE_LICENSED,
	OPSI_MODULE_STATE_UNLICENSED,
	OPSI_MODULE_IDS,
	CLIENT_LIMIT_THRESHOLD_PERCENT,
	CLIENT_LIMIT_THRESHOLD_PERCENT_WARNING
)

LIC1 = {
	"id": "1bf8e14c-1faf-4288-a468-d92e1ee2dd8b",
	"type": "core",
	"schema_version": 2,
	"opsi_version": "4.2",
	"customer_id": "12345",
	"customer_name": "Test GmbH",
	"customer_address": "香港",
	"service_id": "opsi.test.gmbh",
	"module_id": "scalability1",
	"client_number": 1000,
	"issued_at": "2021-08-05",
	"valid_from": "2021-09-01",
	"valid_until": "2023-12-31",
	"revoked_ids": [
		"c6af25cf-62e4-4b90-8f4b-21c542d8b74b",
		"cc4e2986-d28d-4bef-807b-a74ba9a8df04"
	],
	"note": "Some notes",
	"additional_data": None,
	"signature": "0102030405060708090a0b0c0d0e"
}

def _read_modules_file(modules_file):
	modules = {}
	expires = None
	customer = None
	signature = None
	with codecs.open(modules_file, "r", "utf-8") as file:
		for line in file:
			key, val = line.lower().split("=", 1)
			key = key.strip()
			val = val.strip()
			if key == "expires":
				expires = date.fromisoformat(val)
			elif key == "customer":
				customer = val
			elif key == "signature":
				signature = val
			else:
				modules[key] = val
	return modules, expires, customer, signature


def test_generate_key_pair():
	private_key, public_key = generate_key_pair(return_pem=False)
	assert private_key.has_private()
	assert not public_key.has_private()

	private_key, public_key = generate_key_pair(return_pem=True)
	print(private_key)
	print(public_key)
	assert "-----BEGIN RSA PRIVATE KEY-----" in private_key
	assert "-----BEGIN PUBLIC KEY-----" in public_key


def test_sign_opsi_license():
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		lic = OpsiLicense(**LIC1)
		lic.valid_from = lic.valid_until = date.today()
		assert lic.get_state() == OPSI_LICENSE_STATE_INVALID_SIGNATURE
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID


def test_opsi_license_defaults():
	lic = OpsiLicense(
		customer_id="12345",
		customer_name="uib GmbH",
		customer_address="Mainz",
		module_id="scalability1",
		client_number=1000,
		valid_until="2099-12-31"
	)
	assert lic.id
	assert lic.type == "standard"
	assert lic.valid_from == date.today()
	assert lic.issued_at == date.today()


@pytest.mark.parametrize(
	"attribute,value,exception",
	(
		("id", "a62e8266-5df8-41b3-bce3-81da6f69a9d0", None),
		("id", "", ValueError),
		("type", "core", None),
		("type", "invalid", ValueError),
		("schema_version", 1, None),
		("schema_version", 0, ValueError),
		("opsi_version", "5.0", None),
		("opsi_version", "4", ValueError),
		("opsi_version", "4.1.2", ValueError),
		("customer_id", "XY12536", None),
		("customer_id", "", ValueError),
		("customer_name", "uib GmbH", None),
		("customer_name", "", ValueError),
		("customer_address", "üö", None),
		("customer_address", "", ValueError),
		("customer_address", " Mainz", ValueError),
		("module_id", "vpn", None),
		("module_id", "", ValueError),
		("client_number", 999999999, None),
		("client_number", -1, ValueError),
		("issued_at", "2021-01-01", None),
		("issued_at", "", ValueError),
		("valid_from", date.today(), None),
		("valid_from", None, TypeError),
		("valid_until", "9999-12-31", None),
		("valid_until", "0000-00-00", ValueError),
		("revoked_ids", ["a62e8266-5df8-41b3-bce3-6f69a81da9d0", "legacy_scalability1"], None),
		("revoked_ids", ["1", 2], ValueError),
		("signature", "----------------------------", ValueError),
		("signature", "0102030405060708090a0b0c0d0e", None),
		("signature", bytes.fromhex("0102030405060708090a0b0c0d0e"), None),
	),
)
def test_opsi_license_validation(attribute, value, exception):
	kwargs = {
		"customer_id": "12345",
		"customer_name": "uib GmbH",
		"customer_address": "Mainz",
		"module_id": "scalability1",
		"client_number": 1000,
		"valid_until": "2099-12-31"
	}
	kwargs[attribute] = value
	if exception:
		with pytest.raises(exception):
			OpsiLicense(**kwargs)
	else:
		OpsiLicense(**kwargs)


def test_opsi_license_to_from_json():
	lic = OpsiLicense(**LIC1)
	json_data = lic.to_json()
	assert LIC1 == json.loads(json_data)

	lic = OpsiLicense.from_json(json_data)
	json_data = lic.to_json()
	assert LIC1 == json.loads(json_data)

	data = json.loads(lic.to_json(with_state=True))
	assert data["_state"] == OPSI_LICENSE_STATE_INVALID_SIGNATURE


def test_opsi_license_hash():
	lic = OpsiLicense(**LIC1)
	assert lic.get_hash(hex_digest=True) == (
		"f61ffa3f740cf95a3794bc6e3987e81f8af590cc3d7aa26419d27849dab202b3"
		"9c7414d74c575c3721bb4b6e4b1964cd416a455c83e1d6699cc8ead5640eb4da"
	)


def test_load_opsi_license_pool():
	modules_file = "tests/testopsicommon/data/license/modules"
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license/test1.opsilic"
	)
	olp.load()

	assert len(olp.licenses) == 3
	assert "e7f707a7-c184-45e2-a477-27dbf5516b1c" in [lic.id for lic in olp.licenses]
	assert "707ef1b7-6139-4ec4-b60d-8480ce6dae34" in [lic.id for lic in olp.licenses]
	assert "c6af25cf-62e4-4b90-8f4b-21c542d8b74b" in [lic.id for lic in olp.licenses]

	olp.license_file_path = "tests/testopsicommon/data/license"
	olp.load()
	assert len(olp.licenses) == 4
	assert "e7f707a7-c184-45e2-a477-27dbf5516b1c" in [lic.id for lic in olp.licenses]
	assert "707ef1b7-6139-4ec4-b60d-8480ce6dae34" in [lic.id for lic in olp.licenses]
	assert "c6af25cf-62e4-4b90-8f4b-21c542d8b74b" in [lic.id for lic in olp.licenses]
	assert "7cf9ef7e-6e6f-43f5-8b52-7c4e582ff6f1" in [lic.id for lic in olp.licenses]

	olp.license_file_path = None
	olp.modules_file_path = modules_file
	olp.load()

	modules, _expires, _customer, _signature = _read_modules_file(modules_file)
	module_ids = [ m for m in modules if modules[m] != "no" ]
	assert len(module_ids) == len(olp.licenses)

	for lic in olp.licenses:
		assert lic.module_id in module_ids
		_prefix, module_id = lic.id.split("-", 1)
		assert _prefix == "legacy"
		assert module_id in module_ids


def test_opsi_license_pool_licenses_checksum():
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license"
	)
	olp.load()
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		for lic in olp.licenses:
			lic.sign(private_key)
		checksum = olp.get_licenses_checksum()
		assert checksum == "be541f8b"

def test_opsi_license_pool_relevant_dates():
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license"
	)
	olp.load()
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		for lic in olp.licenses:
			lic.sign(private_key)
		dates = olp.get_relevant_dates()
		assert len(dates) == 5

		for at_date in dates:
			modules = olp.get_modules(at_date=at_date)
			assert sorted(OPSI_MODULE_IDS) == sorted(modules)

			assert modules["treeview"]["available"]
			assert modules["treeview"]["state"] == OPSI_MODULE_STATE_FREE

			assert modules["vista"]["available"]
			assert modules["vista"]["state"] == OPSI_MODULE_STATE_FREE

			assert not modules["secureboot"]["available"]
			assert modules["secureboot"]["state"] == OPSI_MODULE_STATE_UNLICENSED

			if at_date >= date.fromisoformat("2019-08-01"):
				assert modules["vpn"]["available"]
				assert modules["vpn"]["state"] == OPSI_MODULE_STATE_LICENSED
			else:
				assert not modules["vpn"]["available"]
				assert modules["vpn"]["state"] == OPSI_MODULE_STATE_UNLICENSED

			if date.fromisoformat("2020-01-01") <= at_date <= date.fromisoformat("2031-12-31"):
				assert modules["scalability1"]["available"]
				assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_LICENSED
			else:
				assert not modules["scalability1"]["available"]
				assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_UNLICENSED


def test_license_state_client_number_thresholds():
	private_key, public_key = generate_key_pair(return_pem=False)
	client_numbers = {}

	def client_info():
		return client_numbers

	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		lic = dict(LIC1)
		del lic["id"]
		lic["module_id"] = "scalability1"
		lic["type"] = OPSI_LICENSE_TYPE_STANDARD
		lic["valid_from"] = "2000-01-01"
		lic["valid_until"] = "9999-12-31"

		lic1 = OpsiLicense(**lic)
		lic1.client_number = 90
		lic1.sign(private_key)

		lic2 = OpsiLicense(**lic)
		lic2.client_number = 10
		lic2.sign(private_key)

		lic3 = OpsiLicense(**lic)
		lic3.type = OPSI_LICENSE_TYPE_CORE
		lic3.client_number = 50
		lic3.sign(private_key)

		olp = OpsiLicensePool(client_info=client_info)
		olp.add_license(lic1, lic2, lic3)

		client_numbers = {
			"macos": 0,
			"linux": 0,
			"windows": 0
		}
		modules = olp.get_modules()
		assert modules["scalability1"]["available"]
		assert modules["scalability1"]["client_number"] == 100
		assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_LICENSED

		client_numbers = {
			"macos": 5,
			"linux": 10,
			"windows": 85 - CLIENT_LIMIT_THRESHOLD_PERCENT_WARNING
		}
		modules = olp.get_modules()
		assert modules["scalability1"]["available"]
		assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_LICENSED

		client_numbers = {
			"macos": 5,
			"linux": 10,
			"windows": 85 - CLIENT_LIMIT_THRESHOLD_PERCENT_WARNING + 1
		}
		modules = olp.get_modules()
		assert modules["scalability1"]["available"]
		assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_CLOSE_TO_LIMIT

		client_numbers = {
			"macos": 5,
			"linux": 10,
			"windows": 85 + CLIENT_LIMIT_THRESHOLD_PERCENT
		}
		modules = olp.get_modules()
		assert modules["scalability1"]["available"]
		assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_OVER_LIMIT

		client_numbers = {
			"macos": 5,
			"linux": 10,
			"windows": 85 + CLIENT_LIMIT_THRESHOLD_PERCENT + 1
		}
		modules = olp.get_modules()
		assert not modules["scalability1"]["available"]
		assert modules["scalability1"]["state"] == OPSI_MODULE_STATE_OVER_LIMIT


def test_license_state():
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		lic = OpsiLicense(**LIC1)
		lic.sign(private_key)

		lic.valid_from = date.today() - timedelta(days=10)
		lic.valid_until = date.today() - timedelta(days=1)
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_EXPIRED

		lic.valid_until = date.today()
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID

		lic.valid_until = date.today() + timedelta(days=1)
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID

		lic.valid_from = date.today() + timedelta(days=1)
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_NOT_YET_VALID

		lic.valid_from = date.today()
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID

		lic.valid_from = date.today() - timedelta(days=1)
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID

		lic.valid_from = date.today()
		lic.valid_until = date.today()
		lic.sign(private_key)
		assert lic.get_state() == OPSI_LICENSE_STATE_VALID
		assert lic.get_state(at_date=date.today() + timedelta(days=1)) == OPSI_LICENSE_STATE_EXPIRED
		assert lic.get_state(at_date=date.today() - timedelta(days=1)) == OPSI_LICENSE_STATE_NOT_YET_VALID

		lic.client_number = 1234567
		assert lic.get_state() == OPSI_LICENSE_STATE_INVALID_SIGNATURE


def test_license_state_modules(tmp_path):
	modules = pathlib.Path("tests/testopsicommon/data/license/modules").read_text()
	modules_file = tmp_path / "modules"
	modules_file.write_text(modules)

	omf = OpsiModulesFile(str(modules_file))
	omf.read()
	lic = omf.licenses[0]

	lic.valid_from = date.today() - timedelta(days=10)

	lic.valid_until = date.today() - timedelta(days=1)
	assert lic.get_state() == OPSI_LICENSE_STATE_EXPIRED

	lic.valid_until = date.today()
	assert lic.get_state() == OPSI_LICENSE_STATE_VALID

	lic.valid_until = date.today() + timedelta(days=1)
	assert lic.get_state() == OPSI_LICENSE_STATE_VALID

	lic.valid_from = date.today() + timedelta(days=1)
	assert lic.get_state() == OPSI_LICENSE_STATE_NOT_YET_VALID

	lic.valid_from = date.today()
	assert lic.get_state() == OPSI_LICENSE_STATE_VALID

	lic.valid_from = date.today() - timedelta(days=1)
	assert lic.get_state() == OPSI_LICENSE_STATE_VALID

	lic.valid_from = date.today()
	lic.valid_until = date.today()
	assert lic.get_state() == OPSI_LICENSE_STATE_VALID
	assert lic.get_state(at_date=date.today() + timedelta(days=1)) == OPSI_LICENSE_STATE_EXPIRED
	assert lic.get_state(at_date=date.today() - timedelta(days=1)) == OPSI_LICENSE_STATE_NOT_YET_VALID

	modules = modules.replace("secureboot = 50", "secureboot = 100")
	modules_file.write_text(modules)
	omf.read()
	lic = omf.licenses[0]

	assert lic.get_state() == OPSI_LICENSE_STATE_INVALID_SIGNATURE


def test_license_state_replaced_by_non_core():
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license"
	)
	olp.load()
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		for lic in olp.licenses:
			lic.sign(private_key)
		for lic in olp.licenses:
			if lic.id == "7cf9ef7e-6e6f-43f5-8b52-7c4e582ff6f1":
				assert lic.get_state() == OPSI_LICENSE_STATE_REPLACED_BY_NON_CORE


def test_license_state_revoked():
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license"
	)
	olp.load()
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		for lic in olp.licenses:
			lic.sign(private_key)
		for lic in olp.licenses:
			if lic.id == "c6af25cf-62e4-4b90-8f4b-21c542d8b74b":
				assert lic.get_state() == OPSI_LICENSE_STATE_REVOKED


def test_opsi_modules_file():
	modules_file = "tests/testopsicommon/data/license/modules"
	raw_data = pathlib.Path(modules_file).read_text()
	modules, expires, customer, signature = _read_modules_file(modules_file)
	omf = OpsiModulesFile(modules_file)
	omf.read()
	assert len(modules) == len(omf.licenses)
	for lic in omf.licenses:
		assert lic.module_id in modules
		assert lic.valid_until == expires
		client_number = 999999999
		if modules[lic.module_id] not in ("yes", "no"):
			client_number = int(modules[lic.module_id])
		assert lic.client_number == client_number
		assert lic.signature.hex() == signature
		assert \
			sorted([x for x in raw_data.replace("\r","").split("\n") if x and not x.startswith("signature")]) == \
			sorted([x for x in lic.additional_data.replace("\r","").split("\n") if x])
