# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
This file is part of opsi - https://www.opsi.org
"""

import json
from datetime import date
import pytest

from opsicommon.license import OpsiLicense, read_license_files

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

def test_opsi_license_to_json():
	kwargs = {
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
		"signature": "0102030405060708090a0b0c0d0e"
	}
	lic = OpsiLicense(**kwargs)
	assert kwargs == json.loads(lic.to_json())

def test_read_license_files():
	pass
