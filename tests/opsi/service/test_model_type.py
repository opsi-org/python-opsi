# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import datetime
import time
from collections.abc import Generator
from contextlib import nullcontext
from typing import Any
from uuid import UUID

import pytest

from opsi.opsi.service.model.object import Host, OpsiClient, ProductOnClient
from opsi.opsi.service.model.type import (
	Architecture,
	FirmwareType,
	OperatingSystem,
	to_action_progress,
	to_action_request,
	to_action_request_list,
	to_action_result,
	to_architecture,
	to_audit_state,
	to_bool,
	to_bool_list,
	to_config_id,
	to_dict,
	to_dict_list,
	to_email_address,
	to_filename,
	to_float,
	to_fqdn,
	to_group_type,
	to_hardware_address,
	to_hardware_device_id,
	to_hardware_vendor_id,
	to_host_address,
	to_host_id,
	to_host_id_list,
	to_installation_status,
	to_int,
	to_int_list,
	to_ip_address,
	to_language_code,
	to_license_contract_id,
	to_license_contract_id_list,
	to_license_pool_id,
	to_license_pool_id_list,
	to_list,
	to_netmask,
	to_network_address,
	to_object_class,
	to_oct,
	to_opsi_host_key,
	to_opsi_timestamp,
	to_package_custom_name,
	to_package_version,
	to_package_version_list,
	to_product_id,
	to_product_id_list,
	to_product_priority,
	to_product_property_id,
	to_product_property_type,
	to_product_target_configuration,
	to_product_type,
	to_product_version,
	to_product_version_list,
	to_requirement_type,
	to_software_license_id,
	to_software_license_id_list,
	to_string,
	to_string_list,
	to_string_list_lower,
	to_time,
	to_unique_list,
	to_unsigned_int,
	to_url,
	to_username,
	to_uuid,
	to_uuid_string,
)


@pytest.fixture
def opsi_client() -> OpsiClient:
	return OpsiClient(
		id="test1.test.invalid",
		description="Test client 1",
		notes="Notes ...",
		hardwareAddress="00:01:02:03:04:05",
		ipAddress="192.168.1.100",
		lastSeen="2009-01-01 00:00:00",
		opsiHostKey="45656789789012789012345612340123",
	)


@pytest.mark.parametrize("cls", [Host, OpsiClient])
def test_to_object_class_to_host_from_json(opsi_client: OpsiClient, cls: type[Host | OpsiClient]) -> None:
	assert isinstance(to_object_class(opsi_client.toJson(), cls), cls)


def test_forcing_object_class_from_product_on_client_json() -> None:
	json = {
		"clientId": "dolly.janus.vater",
		"action_request": "setup",
		"productType": "LocalbootProduct",
		"type": "ProductOnClient",
		"productId": "hoer_auf_deinen_vater",
	}

	poc = to_object_class(json, ProductOnClient)

	assert isinstance(poc, ProductOnClient)


def test_forcing_object_class_from_json_has_good_error_description() -> None:
	incomplete_json = {"clientId": "Nellie*", "action_request": "setup", "productType": "LocalbootProduct", "type": "ProductOnClient"}

	with pytest.raises(ValueError, match="missing 1 required positional argument: 'productId'"):
		to_object_class(incomplete_json, ProductOnClient)

	incomplete_json["type"] = "NotValid"
	with pytest.raises(ValueError, match="Invalid object type: NotValid"):
		to_object_class(incomplete_json, ProductOnClient)


def test_forcing_object_class_from_invalid_json() -> None:
	with pytest.raises(ValueError):
		to_object_class('{"id":"x"', ProductOnClient)


@pytest.mark.parametrize("cls", [Host, OpsiClient])
def test_to_object_class_from_hash(opsi_client: OpsiClient, cls: type[Host | OpsiClient]) -> None:
	assert isinstance(to_object_class(opsi_client.toHash(), cls), cls)


def funky_generator() -> Generator[str]:
	yield "y"
	yield "u"
	yield "so"
	yield "funky"


@pytest.mark.parametrize(
	"inp,expected",
	[
		("x", ["x"]),
		("xy", ["xy"]),
		(None, [None]),
		((0, 1), [0, 1]),
		(("x", "a"), ["x", "a"]),
		(["x", "a"], ["x", "a"]),
		(funky_generator(), ["y", "u", "so", "funky"]),
	],
)
def test_to_list(inp: Any, expected: Any) -> None:
	result = to_list(inp)
	assert isinstance(result, list)
	assert expected == result


def test_force_list_converting_set() -> None:
	inputset = set("abc")
	result_list = to_list(inputset)

	assert len(inputset) == len(result_list)

	for element in inputset:
		assert element in result_list


@pytest.mark.parametrize("value, expected", [("x", "x"), (b"bff69c0d457adb884dafbe8b55a56258", "bff69c0d457adb884dafbe8b55a56258")])
def test_to_string_results_in_unicode(value: Any, expected: Any) -> None:
	result = to_string(value)
	assert isinstance(result, str)
	assert result == expected


def test_to_string_list_results_in_list_of_unicode() -> None:
	returned = to_string_list([None, 1, "x", "y"])
	assert isinstance(returned, list)

	for i in returned:
		assert isinstance(i, str)


def test_to_unicode_lower_list_results_in_lowercase() -> None:
	assert to_string_list_lower(["X", "YES"]) == ["x", "yes"]


def test_to_unicode_lower_list_results_in_unicode() -> None:
	for i in to_string_list_lower([None, 1, "X", "y"]):
		assert isinstance(i, str)


@pytest.mark.parametrize("value", ("on", "oN", "YeS", 1, "1", "x", True, "true", "TRUE"))
def test_to_bool_with_true_values(value: Any) -> None:
	assert to_bool(value) is True


@pytest.mark.parametrize("value", ("off", "oFF", "no", 0, "0", False, "false", "FALSE"))
def test_to_bool_with_falsy_values(value: Any) -> None:
	assert to_bool(value) is False


def test_to_bool_list_with_positive_list() -> None:
	for i in to_bool_list([1, "yes", "on", "1", True]):
		assert i is True


def test_to_bool_list_with_negative_list() -> None:
	for i in to_bool_list([None, "no", "false", "0", False]):
		assert i is False


@pytest.mark.parametrize("value, expected", (("100", 100), ("-100", -100), (1000000000000000, 1000000000000000)))
def test_to_int(value: Any, expected: Any) -> None:
	assert expected == to_int(value)


@pytest.mark.parametrize("value, expected", (("100", 100), ("-100", 100)))
def test_to_unsigned_int(value: Any, expected: Any) -> None:
	assert expected == to_unsigned_int(value)


@pytest.mark.parametrize("value", ("abc",))
def test_to_int_raises_value_error_if_no_conversion_possible(value: Any) -> None:
	with pytest.raises(ValueError):
		to_int(value)


def test_to_int_list() -> None:
	assert [100, 1, 2] == to_int_list(["100", 1, "2"])


@pytest.mark.parametrize(
	"value, expected",
	(
		(0o750, 0o750),
		(0o666, 0o666),
		("666", 0o666),
		("0666", 0o666),
	),
)
def test_to_oct(value: Any, expected: Any) -> None:
	assert expected == to_oct(value)


@pytest.mark.parametrize("value", ("abc", "8"))
def test_to_oct_raising_errors_on_invalid_value(value: Any) -> None:
	with pytest.raises(ValueError):
		to_oct(value)


@pytest.mark.parametrize(
	"value, expected",
	(
		("20000202111213", "2000-02-02 11:12:13"),
		(None, "0000-00-00 00:00:00"),
		(0, "0000-00-00 00:00:00"),
		("", "0000-00-00 00:00:00"),
		("2020-01-01", "2020-01-01 00:00:00"),
		(datetime.datetime(2013, 9, 11, 10, 54, 23), "2013-09-11 10:54:23"),
		(datetime.datetime(2013, 9, 11, 10, 54, 23, 123123), "2013-09-11 10:54:23"),
	),
)
def test_to_opsi_timestamp(value: Any, expected: Any) -> None:
	result = to_opsi_timestamp(value)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("value", ("abc", "8"))
def test_to_opsi_timestamp_raises_errors_on_wrong_input(value: Any) -> None:
	with pytest.raises(ValueError):
		to_opsi_timestamp(value)


@pytest.mark.parametrize(
	"host_id, expected", (("client.test.invalid", "client.test.invalid"), ("CLIENT.test.invalid", "client.test.invalid"))
)
def test_to_host_id(host_id: str, expected: str) -> None:
	assert expected == to_host_id(host_id)


def test_to_host_id_list() -> None:
	assert to_host_id_list("CLIENT.test.invalid") == ["client.test.invalid"]


@pytest.mark.parametrize("host_id", ("abc", "8", "abc.def", ".test.invalid", "abc.uib.x"))
def test_to_host_id_raises_exception_if_invalid(host_id: str) -> None:
	with pytest.raises(ValueError):
		to_host_id(host_id)


@pytest.mark.parametrize(
	"address, expected",
	(
		("12345678ABCD", "12:34:56:78:ab:cd"),
		("12:34:56:78:ab:cd", "12:34:56:78:ab:cd"),
		("12-34-56-78-Ab-cD", "12:34:56:78:ab:cd"),
		("12-34-56:78AB-CD", "12:34:56:78:ab:cd"),
		("", ""),
	),
)
def test_to_hardware_address(address: str, expected: str) -> None:
	result = to_hardware_address(address)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize(
	"address",
	(
		"12345678abc",
		"12345678abcdef",
		"1-2-3-4-5-6-7",
		None,
		True,
	),
)
def test_to_hardware_address_raises_exceptions_on_invalid_addresses(address: Any) -> None:
	with pytest.raises(ValueError):
		to_hardware_address(address)


@pytest.mark.parametrize(
	"inp, expected",
	[
		("1.1.1.1", "1.1.1.1"),
		("192.168.101.1", "192.168.101.1"),
		("192.168.101.1", "192.168.101.1"),
		("2001:0db8:85a3::8a2e:0370:7334", "2001:db8:85a3::8a2e:370:7334"),
		("2001:db8:85a3:0000:0000:8a2e:0370:7334", "2001:db8:85a3::8a2e:370:7334"),
		("::FFFF:129.144.52.38", "129.144.52.38"),
	],
)
def test_to_ip_address(inp: str, expected: str) -> None:
	output = to_ip_address(inp)
	assert expected == output
	assert isinstance(output, str)


@pytest.mark.parametrize(
	"malformed_input",
	[
		"1922.1.1.1",
		None,
		True,
		"1.1.1.1.",
		"2.2.2.2.2",
		"a.2.3.4",
	],
)
def test_to_ip_address_raises_errors_on_invalid_input(malformed_input: Any) -> None:
	with pytest.raises(ValueError):
		to_ip_address(malformed_input)


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("2001:db8:85a3::8a2e:0370:7334", "2001:db8:85a3::8a2e:370:7334", None),
		("192.168.1.1", "192.168.1.1", None),
		("host.DOM.tld", "host.dom.tld", None),
		("hostName", "hostname", None),
		("192.168.1.1.2", None, ValueError),
	),
)
def test_to_host_address(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_host_address(value)
	else:
		assert to_host_address(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("255.255.255.0", "255.255.255.0", None),
		("255.255.255.256", None, ValueError),
		("24", None, ValueError),
	),
)
def test_to_netmask(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_netmask(value)
	else:
		assert to_netmask(value) == expected


@pytest.mark.parametrize(
	"address, expected",
	(
		("192.168.0.0/16", "192.168.0.0/16"),
		("10.10.10.10/32", "10.10.10.10/32"),
	),
)
def test_to_network_address(address: str, expected: str) -> None:
	result = to_network_address(address)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize(
	"address",
	(
		"192.168.101",
		"192.1.1.1/40",
		None,
		True,
		"10.10.1/24",
		"a.2.3.4/0",
	),
)
def test_to_network_address_raises_exceptions_on_invalid_addresses(address: Any) -> None:
	with pytest.raises(ValueError):
		to_network_address(address)


@pytest.mark.parametrize(
	"url, expected",
	(
		("file:///", "file:///"),
		("file:///path/to/file", "file:///path/to/file"),
		("smb://server/path", "smb://server/path"),
		("https://x:y@server.domain.tld:4447/resource", "https://x:y@server.domain.tld:4447/resource"),
	),
)
def test_to_url(url: str, expected: str) -> None:
	result = to_url(url)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize(
	"url, expected",
	(
		("https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource", "https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource"),
		("https://X:Y@server.domain.tld:4447/resource", "https://X:Y@server.domain.tld:4447/resource"),
	),
)
def test_to_url_does_not_force_lowercase(url: str, expected: str) -> None:
	"""
	Complete URLs must not be forced to lowercase because they could \
	include an username / password combination for an proxy.
	"""
	assert expected == to_url(url)


@pytest.mark.parametrize(
	"url",
	(
		"abc",
		"/abc",
		"http//server",
		1,
		True,
		None,
	),
)
def test_to_url_with_invalid_urls_raises_exceptions(url: Any) -> None:
	with pytest.raises(ValueError):
		to_url(url)


@pytest.mark.parametrize("host_key", ("abcdef78901234567890123456789012",))
def test_to_opsi_host_key(host_key: str) -> None:
	result = to_opsi_host_key(host_key)
	assert host_key.lower() == result
	assert isinstance(result, str)


@pytest.mark.parametrize(
	"host_key",
	(
		"abCdeF7890123456789012345678901",  # too short
		"abCdeF78901234567890123456789012b",  # too long
		"GbCdeF78901234567890123456789012",
	),
)
def test_to_opsi_host_key_with_invalid_host_keys_raises_exceptions(host_key: str) -> None:
	with pytest.raises(ValueError):
		to_opsi_host_key(host_key)


@pytest.mark.parametrize(
	"version, expected, exc",
	(
		("1.0", "1.0", None),
		("2 3 4", None, ValueError),
	),
)
def test_to_product_version(version: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_version(version)
	else:
		result = to_product_version(version)
		assert expected == result
		assert isinstance(result, str)


@pytest.mark.parametrize(
	"version, expected, exc", ((["2.0", "2.1"], ["2.0", "2.1"], None), ("3.1k", ["3.1k"], None), (["1 1 1"], None, ValueError))
)
def test_to_product_version_list(version: list[str] | str, expected: list[str], exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_version_list(version)
	else:
		assert to_product_version_list(version) == expected


@pytest.mark.parametrize(
	"version, expected, exc",
	(
		(1, "1", None),
		(8, "8", None),
		("x_3_f", None, ValueError),
	),
)
def test_to_package_version(version: int | str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_package_version(version)
	else:
		result = to_package_version(version)
		assert expected == result
		assert isinstance(result, str)


@pytest.mark.parametrize("version, expected, exc", (([2, "2.1"], ["2", "2.1"], None), ("ver1", ["ver1"], None), ("___", None, ValueError)))
def test_to_package_version_list(version: Any, expected: Any, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_package_version_list(version)
	else:
		assert to_package_version_list(version) == expected


@pytest.mark.parametrize("product_id, expected_product_id", (("testProduct1", "testproduct1"),))
def test_to_product_id(product_id: str, expected_product_id: str) -> None:
	result = to_product_id(product_id)
	assert expected_product_id == result
	assert isinstance(result, str)


@pytest.mark.parametrize("product_id", ("äöü", "product test"))
def test_to_product_id_with_invalid_product_id_raises_exceptions(product_id: str) -> None:
	with pytest.raises(ValueError):
		to_product_id(product_id)


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("testProduct1", ["testproduct1"], None),
		(["testproduct1", "testproduct2"], ["testproduct1", "testproduct2"], None),
		("ööö", None, ValueError),
	),
)
def test_to_product_id_list(value: Any, expected: Any, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_id_list(value)
	else:
		assert to_product_id_list(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("cust", "cust", None),
		("xy-", None, ValueError),
	),
)
def test_to_package_custom_name(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_package_custom_name(value)
	else:
		assert to_package_custom_name(value) == expected


@pytest.mark.parametrize("path, expected", (("c:\\tmp\\test.txt", "c:\\tmp\\test.txt"),))
def test_to_filename(path: str, expected: str) -> None:
	result = to_filename(path)
	assert expected == result
	assert isinstance(expected, str)


@pytest.mark.parametrize("status", ("installed", "not_installed", "unknown"))
def test_to_installation_status(status: str) -> None:
	result = to_installation_status(status)
	assert result == status
	assert isinstance(result, str)


@pytest.mark.parametrize("status", ("none", "abc"))
def test_to_installation_status_with_invalid_value_raises_exceptions(status: str) -> None:
	with pytest.raises(ValueError):
		to_installation_status(status)


def test_to_action_request_with_invalid_value_raises_exceptions() -> None:
	with pytest.raises(ValueError):
		to_action_request("installed")


@pytest.mark.parametrize("action_request", ("setup", "uninstall", "update", "once", "always", "none", None))
def test_to_action_request(action_request: str) -> None:
	returned = to_action_request(action_request)
	assert returned == str(action_request).lower()
	assert isinstance(returned, str)


def test_to_action_request_returns_none_on_undefined() -> None:
	assert to_action_request("undefined") is None


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("setup", ["setup"], None),
		(["setup", "Always"], ["setup", "always"], None),
		(["invalid"], None, ValueError),
		("INVALID", None, ValueError),
	),
)
def test_to_action_request_list(value: list[str] | str, expected: list[str] | str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_action_request_list(value)
	else:
		assert to_action_request_list(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("failed", "failed", None),
		("successful", "successful", None),
		("none", "none", None),
		(None, "none", None),
		("", None, None),
		("x", None, ValueError),
		("-", None, ValueError),
	),
)
def test_to_action_result(value: str | None, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_action_result(value)
	else:
		assert to_action_result(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc", (("Before", "before", None), ("after", "after", None), ("", None, None), ("-", None, ValueError))
)
def test_to_requirement_type(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_requirement_type(value)
	else:
		assert to_requirement_type(value) == expected


def test_to_action_progress() -> None:
	returned = to_action_progress("installing 50%")
	assert returned == "installing 50%"
	assert isinstance(returned, str)


@pytest.mark.parametrize(
	"code, expected",
	(
		("xx-xxxx-xx", "xx-Xxxx-XX"),
		("yy_yy", "yy-YY"),
		("zz_ZZZZ", "zz-Zzzz"),
	),
)
def test_to_language_code_normalises_casing(code: str, expected: str) -> None:
	assert expected == to_language_code(code)


@pytest.mark.parametrize("code, expected", (("dE", "de"), ("en-us", "en-US")))
def test_to_language_code(code: str, expected: str) -> None:
	assert to_language_code(code) == expected


def test_to_language_code_raises_exception_on_invalid_code() -> None:
	with pytest.raises(ValueError):
		to_language_code("de-DEU")


@pytest.mark.parametrize(
	"architecture, expected",
	(
		("X86", "x86"),
		("X64", "x64"),
	),
)
def test_to_architecture_lowercase(architecture: str, expected: str) -> None:
	assert expected == to_architecture(architecture)


def test_architecture() -> None:
	assert Architecture("amd64") == Architecture.X64
	assert Architecture("x64") == Architecture.X64
	assert Architecture("x86_64") == Architecture.X64
	assert Architecture("x86") == Architecture.X86
	assert Architecture("arm64").inf_value == "arm64"
	assert Architecture("amd64").inf_value == "amd64"
	assert Architecture("x64").inf_value == "amd64"
	with pytest.raises(ValueError):
		Architecture("other")


def test_firmware_type() -> None:
	assert FirmwareType("UEFI") == FirmwareType.UEFI
	assert FirmwareType("BIOS") == FirmwareType.BIOS
	assert FirmwareType("bios") == FirmwareType.BIOS
	with pytest.raises(ValueError):
		FirmwareType("other")


def test_operating_system() -> None:
	assert OperatingSystem("Windows") == OperatingSystem.WINDOWS
	assert OperatingSystem("Linux") == OperatingSystem.LINUX
	assert OperatingSystem("MacOS") == OperatingSystem.MACOS
	with pytest.raises(ValueError):
		OperatingSystem("other")


def test_to_time_fails_if_no_time_given() -> None:
	with pytest.raises(ValueError):
		to_time("Hello World!")


@pytest.mark.parametrize(
	"time_info",
	(
		time.time(),
		time.localtime(),
		datetime.datetime.now(),
	),
)
def test_to_time_returns_time_struct(time_info: Any) -> None:
	assert isinstance(to_time(time_info), time.struct_time)


@pytest.mark.parametrize(
	"value, expected, exc", (("0adf", "0ADF", None), ("012F", "012F", None), ("invalid", None, ValueError), ("INVA", None, ValueError))
)
def test_to_hardware_vendor_id(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_hardware_vendor_id(value)
	else:
		assert to_hardware_vendor_id(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc", (("0adE", "0ADE", None), ("01aa", "01AA", None), ("----", None, ValueError), ("", None, ValueError))
)
def test_to_hardware_device_id(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_hardware_device_id(value)
	else:
		assert to_hardware_device_id(value) == expected


@pytest.mark.parametrize("invalid_mail_address", ("infouib.de",))
def test_to_email_address_raises_an_exception_on_invalid_mail_address(invalid_mail_address: tuple[str]) -> None:
	with pytest.raises(ValueError):
		to_email_address(invalid_mail_address)


@pytest.mark.parametrize(
	"address, expected",
	(
		("info@uib.de", "info@uib.de"),
		("webmaster@somelongname.passenger-association.aero", "webmaster@somelongname.passenger-association.aero"),
		("bla@name.posts-and-telecommunications.museum", "bla@name.posts-and-telecommunications.museum"),
		("webmaster@bike.equipment", "webmaster@bike.equipment"),
		("some.name@company.travelersinsurance", "some.name@company.travelersinsurance"),
	),
)
# A large list of TLDs can be found at https://publicsuffix.org/
def test_to_email_address(address: str, expected: str) -> None:
	assert expected == to_email_address(address)


@pytest.mark.parametrize("invalid_type", ("TrolololoProduct", None))
def test_to_product_type_raises_exception_on_unknown_type(invalid_type: str | None) -> None:
	with pytest.raises(ValueError):
		to_product_type(invalid_type)


@pytest.mark.parametrize("inp", ("LocalBootProduct", "LOCALBOOT"))
def test_to_product_type_to_localboot_product(inp: str) -> None:
	assert "LocalbootProduct" == to_product_type(inp)


@pytest.mark.parametrize("inp", ("NetbOOtProduct", "nETbOOT"))
def test_to_product_type_to_netboot_product(inp: str) -> None:
	assert "NetbootProduct" == to_product_type(inp)


@pytest.mark.parametrize("value, expected, exc", (("prop1", "prop1", None), ("PROP2", "prop2", None), ("inv alid", None, ValueError)))
def test_to_product_property_id(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_property_id(value)
	else:
		assert to_product_property_id(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc", (("config.name", "config.name", None), ("CONF.NAme", "conf.name", None), ("not valid", None, ValueError))
)
def test_to_config_id(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_config_id(value)
	else:
		assert to_config_id(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("UnicodeProductProperty", "UnicodeProductProperty", None),
		("Unicodeproductproperty", "UnicodeProductProperty", None),
		("BoolProductProperty", "BoolProductProperty", None),
		("ProductProperty", None, ValueError),
	),
)
def test_to_product_property_type(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_property_type(value)
	else:
		assert to_product_property_type(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc", (("100", 100, None), (-101, -100, None), (1000, 100, None), (0.0, 0, None), ("high", None, ValueError))
)
def test_to_product_priority(value: float | str, expected: int | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_priority(value)
	else:
		assert to_product_priority(value) == expected


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("Installed", "installed", None),
		("always", "always", None),
		("forbidden", "forbidden", None),
		("undefineD", "undefined", None),
		("other", None, ValueError),
	),
)
def test_to_product_target_configuration(value: str, expected: str | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_product_target_configuration(value)
	else:
		assert to_product_target_configuration(value) == expected


@pytest.mark.parametrize(
	"inp, expected",
	[
		(None, {}),
		({"a": 1}, {"a": 1}),
	],
)
def test_to_dict_returns_dict(inp: dict | None, expected: dict) -> None:
	assert to_dict(inp) == expected


@pytest.mark.parametrize("inp", ["asdg", ["asdfg", "asd"]])
def test_to_dict_fails_if_conversion_impossible(inp: str | list[str]) -> None:
	with pytest.raises(ValueError):
		to_dict(inp)


def test_to_dict_list() -> None:
	assert to_dict_list({"a": 1}) == [{"a": 1}]


@pytest.mark.parametrize(
	"expected, before",
	(
		([1], [1, 1]),
		([1, 2, 3], (1, 2, 2, 3)),
	),
)
def test_after_forcing_items_in_list_are_unique(before: list[int], expected: list[int] | tuple[int, ...]) -> None:
	assert expected == to_unique_list(before)


def test_to_unique_list_does_not_change_order() -> None:
	assert [2, 1, 3, 5, 4] == to_unique_list([2, 2, 1, 3, 5, 4, 1])


def test_to_fqdn_removes_trailing_dot() -> None:
	assert "abc.example.local" == to_fqdn("abc.example.local.")


@pytest.mark.parametrize(
	"hostname",
	[
		"hostname.rootzone.tld",  # complete hostname
		pytest.param("host_name.rootzone.tld", marks=pytest.mark.xfail),  # underscore
		pytest.param("hostname.tld", marks=pytest.mark.xfail),  # only domain
	],
)
def test_to_fqdn_requires_hostname_root_zone_and_top_level_domain(hostname: str) -> None:
	to_fqdn(hostname)


@pytest.mark.parametrize("domain", ["BLA.domain.invalid", "bla.doMAIN.invalid", "bla.domain.iNVAlid"])
def test_to_fqdn_always_returns_lowercase(domain: str) -> None:
	assert "bla.domain.invalid" == to_fqdn(domain)


@pytest.mark.parametrize("inp", ["asdf", None])
def test_to_group_type_fails_on_invalid_input(inp: str | None) -> None:
	with pytest.raises(ValueError):
		to_group_type(inp)


@pytest.mark.parametrize(
	"inp, expected",
	[
		("hostGROUP", "HostGroup"),
		("HostgROUp", "HostGroup"),
		("PrOdUcTgRoUp", "ProductGroup"),
	],
)
def test_fto_group_type_standardises_case(inp: str, expected: str) -> None:
	assert to_group_type(inp) == expected


@pytest.mark.parametrize(
	"inp, expected",
	[
		(1, 1.0),
		(1.3, 1.3),
		("1", 1.0),
		("1.3", 1.3),
		("	1.4   ", 1.4),
	],
)
def test_to_float(inp: str | float, expected: float) -> None:
	assert expected == to_float(inp)


@pytest.mark.parametrize(
	"invalid_input",
	[
		{"abc": 123},
		["a", "b"],
		"No float",
		"text",
	],
)
def test_to_float_fails_with_invalid_input(invalid_input: Any) -> None:
	with pytest.raises(ValueError):
		to_float(invalid_input)


@pytest.mark.parametrize(
	"value, expected_value, exception",
	(
		("cff3f1dc-c135-4e51-8094-5b4589f66ddc", UUID("cff3f1dc-c135-4e51-8094-5b4589f66ddc"), None),
		("cff3f1dc-c135-4e51-8094-5b4589f66", None, ValueError),
		(b"cff3f1dc-c135-4e51-8094-5b4589f66ddc", UUID("cff3f1dc-c135-4e51-8094-5b4589f66ddc"), None),
		(UUID("cff3f1dc-c135-4e51-8094-5b4589f66ddc"), UUID("cff3f1dc-c135-4e51-8094-5b4589f66ddc"), None),
		(None, None, ValueError),
		(123, None, ValueError),
	),
)
def test_to_uuid(value: Any, expected_value: UUID | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		value = to_uuid(value)
	if not exception:
		assert value == expected_value

	with pytest.raises(exception) if exception else nullcontext():
		value = to_uuid_string(value)
	if not exception:
		assert value == str(expected_value)


@pytest.mark.parametrize(
	"value, expected, exception",
	(
		("User.Name-1_Test@example", "user.name-1_test@example", None),
		(r"DOMAIN\\User", r"domain\\user", None),
		("a" * 64, "a" * 64, None),
		("", None, ValueError),
		("user name", None, ValueError),
		("user!", None, ValueError),
		("a" * 65, None, ValueError),
	),
)
def test_to_username(value: Any, expected: str | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		result = to_username(value)
	if not exception:
		assert result == expected
		assert isinstance(result, str)


@pytest.mark.parametrize(
	"value, expected, exception",
	(
		("Contract-1: Main", "contract-1: main", None),
		("1contract", "1contract", None),
		("", None, ValueError),
		(" contract", None, ValueError),
		("contract!", None, ValueError),
	),
)
def test_to_license_contract_id(value: Any, expected: str | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		result = to_license_contract_id(value)
	if not exception:
		assert result == expected
		assert isinstance(result, str)


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("Contract-1: Main", ["contract-1: main"], None),
		(["First", "Second: 2"], ["first", "second: 2"], None),
		(["valid", "not!valid"], None, ValueError),
		("", None, ValueError),
	),
)
def test_to_license_contract_id_list(value: Any, expected: list[str] | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_license_contract_id_list(value)
	else:
		assert to_license_contract_id_list(value) == expected


@pytest.mark.parametrize(
	"value, expected, exception",
	(
		("Software-License_1", "software-license_1", None),
		("1license pool", "1license pool", None),
		("", None, ValueError),
		(" license", None, ValueError),
		("license/1", None, ValueError),
	),
)
def test_to_software_license_id(value: Any, expected: str | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		result = to_software_license_id(value)
	if not exception:
		assert result == expected
		assert isinstance(result, str)


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("Software-License_1", ["software-license_1"], None),
		(["Alpha", "Beta: 2"], ["alpha", "beta: 2"], None),
		(["valid", "bad/value"], None, ValueError),
		("", None, ValueError),
	),
)
def test_to_software_license_id_list(value: Any, expected: list[str] | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_software_license_id_list(value)
	else:
		assert to_software_license_id_list(value) == expected


@pytest.mark.parametrize(
	"value, expected, exception",
	(
		("Pool-1: Main", "pool-1: main", None),
		("9pool_name", "9pool_name", None),
		("", None, ValueError),
		(" pool", None, ValueError),
		("pool/1", None, ValueError),
	),
)
def test_to_license_pool_id(value: Any, expected: str | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		result = to_license_pool_id(value)
	if not exception:
		assert result == expected
		assert isinstance(result, str)


@pytest.mark.parametrize(
	"value, expected, exc",
	(
		("Pool-1: Main", ["pool-1: main"], None),
		(["PoolOne", "Pool Two: 2"], ["poolone", "pool two: 2"], None),
		(["valid", "bad/value"], None, ValueError),
		("", None, ValueError),
	),
)
def test_to_license_pool_id_list(value: Any, expected: list[str] | None, exc: type[Exception] | None) -> None:
	if exc:
		with pytest.raises(exc):
			to_license_pool_id_list(value)
	else:
		assert to_license_pool_id_list(value) == expected


@pytest.mark.parametrize(
	"value, expected, exception",
	(
		(0, 0, None),
		("1", 1, None),
		(2, None, ValueError),
		(-1, None, ValueError),
		("invalid", None, ValueError),
	),
)
def test_to_audit_state(value: Any, expected: int | None, exception: type[Exception] | None) -> None:
	with pytest.raises(exception) if exception else nullcontext():
		result = to_audit_state(value)
	if not exception:
		assert result == expected
		assert isinstance(result, int)
