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
	generate_key_pair,
	OpsiLicense, OpsiModulesFile, OpsiLicensePool,
	OPSI_LICENSE_STATE_REPLACED_BY_NON_CORE,
	OPSI_LICENSE_STATE_VALID,
	OPSI_LICENSE_STATE_INVALID_SIGNATURE,
	OPSI_LICENSE_STATE_EXPIRED,
	OPSI_LICENSE_STATE_NOT_YET_VALID,
	OPSI_LICENSE_STATE_REVOKED,
	OPSI_LICENSE_TYPE_CORE
)

LIC1 = {
	"id": "1bf8e14c-1faf-4288-a468-d92e1ee2dd8b",
	"type": "core",
	"schema_version": 2,
	"opsi_version": "4.2",
	"customer_id": "12345",
	"customer_name": "uib GmbH",
	"customer_address": "Mainz",
	"module_id": "scalibility1",
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
	with codecs.open(modules_file, "r", "utf-8") as file:
		for line in file:
			key, val = line.lower().split("=", 1)
			key = key.strip()
			val = val.strip()
			if key == "expires":
				expires = date.fromisoformat(val)
			elif key not in ("signature", "customer") and val != "no":
				modules[key] = val
	return modules, expires


def test_generate_key_pair():
	private_key, public_key = generate_key_pair(return_pem=False)
	assert private_key.has_private()
	assert not public_key.has_private()

	private_key, public_key = generate_key_pair(return_pem=True)
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
		module_id="scalibility1",
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
		"module_id": "scalibility1",
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
		"0fcaaf45f961fedded227d9776bc597e253cb07640e1de9300f9c1c7d981c80e"
		"9685cd32e86fb7aabbb35334dfda6d01787056cec5114a13a7c8fb2ea9b87f78"
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

	modules, _expires = _read_modules_file(modules_file)
	module_ids = [ m for m in modules if modules[m] != "no" ]
	assert len(module_ids) == len(olp.licenses)

	for lic in olp.licenses:
		assert lic.module_id in module_ids
		_prefix, module_id = lic.id.split("-", 1)
		assert _prefix == "legacy"
		assert module_id in module_ids


def test_opsi_license_pool_dates():
	olp = OpsiLicensePool(
		license_file_path="tests/testopsicommon/data/license"
	)
	olp.load()
	private_key, public_key = generate_key_pair(return_pem=False)
	with mock.patch('opsicommon.license.get_signature_public_key', lambda x: public_key):
		for lic in olp.licenses:
			lic.sign(private_key)
		dates = olp.get_dates()
		print(dates)

def test_license_state(tmp_path):
	modules = pathlib.Path("tests/testopsicommon/data/license/modules").read_text()
	########lic = OpsiLicense(**LIC1)
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
			if lic.type == OPSI_LICENSE_TYPE_CORE:
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
			if lic.id == "c6af25cf-62e4-4b90-8f4b-21c542d8b74b":
				assert lic.get_state() == OPSI_LICENSE_STATE_REVOKED


def test_opsi_modules_file():
	modules_file = "tests/testopsicommon/data/license/modules"

	modules, expires = _read_modules_file(modules_file)
	omf = OpsiModulesFile(modules_file)
	omf.read()
	assert len(modules) == len(omf.licenses)
	for lic in omf.licenses:
		assert lic.module_id in modules
		assert lic.valid_until == expires
		client_number = 999999999
		if modules[lic.module_id] != "yes":
			client_number = int(modules[lic.module_id])
		assert lic.client_number == client_number
