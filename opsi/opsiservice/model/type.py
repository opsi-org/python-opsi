# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
Type conversion features.

This module contains valueious methods to convert objects to specific types.
"""

from __future__ import annotations

import datetime
import ipaddress
import os
import re
import time
import types
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID

from opsi.logging import get_logger

if os.name != "nt":
	WindowsError = RuntimeError

if TYPE_CHECKING:
	from opsi.opsiservice.model.object import BaseObjectT

__all__ = (
	"to_action_progress",
	"to_action_request",
	"to_action_request_list",
	"to_action_result",
	"to_architecture",
	"to_architecture_list",
	"to_audit_state",
	"to_bool",
	"to_bool_list",
	"to_config_id",
	"to_dict",
	"to_dict_list",
	"to_domain",
	"to_email_address",
	"to_filename",
	"to_float",
	"to_fqdn",
	"to_group_id",
	"to_group_id_list",
	"to_group_type",
	"to_group_type_list",
	"to_hardware_address",
	"to_hardware_device_id",
	"to_hardware_vendor_id",
	"to_host_address",
	"to_host_id",
	"to_host_id_list",
	"to_hostname",
	"to_ip_address",
	"to_installation_status",
	"to_int",
	"to_int_list",
	"to_language_code",
	"to_language_code_list",
	"to_license_contract_id",
	"to_license_contract_id_list",
	"to_license_pool_id",
	"to_license_pool_id_list",
	"to_list",
	"to_netmask",
	"to_network_address",
	"to_object_class",
	"to_object_class_list",
	"to_object_id",
	"to_object_id_list",
	"to_oct",
	"to_opsi_host_key",
	"to_opsi_timestamp",
	"to_package_custom_name",
	"to_package_version",
	"to_package_version_list",
	"to_product_id",
	"to_product_id_list",
	"to_product_priority",
	"to_product_property_id",
	"to_product_property_type",
	"to_product_target_configuration",
	"to_product_type",
	"to_product_version",
	"to_product_version_list",
	"to_requirement_type",
	"to_software_license_id",
	"to_software_license_id_list",
	"to_time",
	"to_unicode",
	"to_unicode_list",
	"to_unicode_lower",
	"to_unicode_lower_list",
	"to_unicode_upper",
	"to_unique_list",
	"to_unsigned_int",
	"to_url",
)

logger = get_logger("opsi")

get_object_type: Callable | None = None
from_json: Callable | None = None

_HARDWARE_ID_REGEX = re.compile(r"^[a-fA-F0-9]{4}$")
_OPSI_TIMESTAMP_REGEX = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})\s?(\d{2}):?(\d{2}):?(\d{2})\.?\d*$")
_OPSI_DATE_REGEX = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})$")
_FQDN_REGEX = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}\.((\w+\-+)|(\w+\.))*\w{1,63}\.\w{2,16}\.?$")
_USERNAME_REGEX = re.compile(r"^[a-z0-9\-_\.@\\]{1,64}$")
_HARDWARE_ADDRESS_REGEX = re.compile(
	r"^([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})[:-]?([0-9a-f]{2})$"
)
_NETMASK_REGEX = re.compile(
	r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
	r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)
_URL_REGEX = re.compile(r"^[a-z0-9]+:\/\/[/a-zA-Z0-9@:%._\+~#?&=\[\]]+")
_OPSI_HOST_KEY_REGEX = re.compile(r"^[0-9a-f]{32}$")
_PRODUCT_VERSION_REGEX = re.compile(r"^[a-zA-Z0-9.]{1,32}$")
_PACKAGE_VERSION_REGEX = re.compile(r"^[a-zA-Z0-9.]{1,16}$")
_PRODUCT_ID_REGEX = re.compile(r"^[a-z0-9-_\.]{1,128}$")
_PACKAGE_CUSTOM_NAME_REGEX = re.compile(r"^[a-zA-Z0-9]+$")
_PRODUCT_PROPERTY_ID_REGEX = re.compile(r"^\S+$")
_CONFIG_ID_REGEX = re.compile(r"^\S+$")
_GROUP_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_. ]*$")
_OBJECT_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_. ]*$")
_EMAIL_REGEX = re.compile(r"^(([A-Za-z0-9]+_+)|([A-Za-z0-9]+\-+)|([A-Za-z0-9]+\.+)|([A-Za-z0-9]+\++))*[A-Za-z0-9]+@((\w+\-+)|(\w+\.))*\w*")
_DOMAIN_REGEX = re.compile(r"^((\w+\-+)|(\w+\.))*\w{1,63}\.\w{2,16}\.?$")
_HOSTNAME_REGEX = re.compile(r"^[a-z0-9][a-z0-9\-]*$")
_LICENSE_CONTRACT_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_. :]*$")
_SOFTWARE_LICENSE_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_. :]*$")
_LICENSE_POOL_ID_REGEX = re.compile(r"^[a-z0-9][a-z0-9-_. :]*$")
_LANGUAGE_CODE_REGEX = re.compile(r"^([a-z]{2,3})[-_]?([a-z]{4})?[-_]?([a-z]{2})?$")
_ARCHITECTURE_REGEX = re.compile(r"^(x86|x64|arm64|all)$")


class OperatingSystem(StrEnum):
	WINDOWS = "windows"
	MACOS = "macos"
	LINUX = "linux"
	OPSI_LOCAL_IMAGE = "opsi-local-image"

	@classmethod
	def _missing_(cls, value: object) -> OperatingSystem:
		value = str(value).lower()
		for member in cls:
			if member.value == value:
				return member
		raise ValueError(f"{value!r} is not a valid {cls.__name__}")


class Architecture(StrEnum):
	X86 = "x86"
	X64 = "x64"
	IA64 = "ia64"
	ARM = "arm"
	ARM64 = "arm64"
	ALL = "all"

	@classmethod
	def _missing_(cls, value: object) -> Architecture:
		value = str(value).lower()
		if value in ("x86_64", "amd64"):
			value = "x64"
		for member in cls:
			if member.value == value:
				return member
		raise ValueError(f"{value!r} is not a valid {cls.__name__}")

	@property
	def inf_value(self) -> str:
		if self == Architecture.X64:
			return "amd64"
		return self.value


class FirmwareType(StrEnum):
	BIOS = "BIOS"
	UEFI = "UEFI"

	@classmethod
	def _missing_(cls, value: object) -> FirmwareType:
		value = str(value).upper()
		for member in cls:
			if member.value == value:
				return member
		raise ValueError(f"{value!r} is not a valid {cls.__name__}")


def to_list(value: Any) -> list[Any]:
	if not isinstance(value, (set, list, tuple, types.GeneratorType)):
		return [value]

	return list(value)


def to_string(value: Any) -> str:
	if isinstance(value, str):
		return value
	if os.name == "nt" and isinstance(value, WindowsError):
		try:
			return f"[Error {value.args[0]}] {value.args[1]}"
		except Exception:
			return str(value)
	try:
		if isinstance(value, bytes):
			return value.decode()
	except Exception:
		pass

	try:
		value = repr(value)
		if isinstance(value, str):
			return value
		return str(value, "utf-8", "replace")
	except Exception:
		pass

	return str(value)


to_unicode = to_string


def to_string_lower(value: Any) -> str:
	return to_string(value).lower()


to_unicode_lower = to_string_lower


def to_string_upper(value: Any) -> str:
	return to_string(value).upper()


to_unicode_upper = to_string_upper


def to_string_list(value: Any) -> list[str]:
	return [to_string(element) for element in to_list(value)]


to_unicode_list = to_string_list


def to_dict_list(value: Any) -> list[dict]:
	return [to_dict(element) for element in to_list(value)]


def to_string_list_lower(value: Any) -> list[str]:
	return [to_string_lower(element) for element in to_list(value)]


to_unicode_lower_list = to_string_list_lower


def to_uuid(value: Any) -> UUID:
	if isinstance(value, UUID):
		return value
	return UUID(to_string(value))


def to_uuid_string(value: Any) -> str:
	return str(to_uuid(value))


def to_bool(value: Any) -> bool:
	if isinstance(value, bool):
		return value
	if isinstance(value, str):
		if len(value) <= 5:  # longest word is 5 characters ("false")
			low_value = value.lower()
			if low_value in ("true", "yes", "on", "1"):
				return True
			if low_value in ("false", "no", "off", "0"):
				return False

	return bool(value)


def to_bool_list(value: Any) -> list[bool]:
	return [to_bool(element) for element in to_list(value)]


def to_int(value: Any) -> int:
	if isinstance(value, int):
		return value
	try:
		return int(value)
	except Exception as err:
		raise ValueError(f"Bad int value '{value}': {err}") from err


def to_int_list(value: Any) -> list[int]:
	return [to_int(element) for element in to_list(value)]


def to_unsigned_int(value: Any) -> int:
	value = to_int(value)
	if value < 0:
		value = -1 * value
	return value


def to_oct(value: Any) -> int:
	if isinstance(value, int):
		return value

	try:
		oct_value = ""
		for idx, val_str in enumerate(to_string(value)):
			val = to_int(val_str)
			if val > 7:
				raise ValueError(f"{val} is too big")
			if idx == 0 and val != "0":
				oct_value += "0"
			oct_value += str(val)

		oct_value_int = int(oct_value, 8)
		return oct_value_int
	except Exception as err:
		raise ValueError(f"Bad oct value {value}: {err}") from err


def to_float(value: Any) -> float:
	if isinstance(value, float):
		return value

	try:
		return float(value)
	except Exception as err:
		raise ValueError(f"Bad float value '{value}': {err}") from err


def to_dict(value: Any) -> dict:
	if value is None:
		return {}
	if isinstance(value, dict):
		return value
	raise ValueError(f"Not a dict '{value}'")


def to_time(value: Any) -> time.struct_time | datetime.datetime:
	"""
	Convert `value` to a time.struct_time.

	If no conversion is possible a `ValueError` will be raised.
	"""
	if isinstance(value, time.struct_time):
		return value
	if isinstance(value, datetime.datetime):
		value = time.mktime(value.timetuple()) + value.microsecond / 1e6

	if isinstance(value, (int, float)):
		return time.localtime(value)

	raise ValueError(f"Not a time {value}")


def to_hardware_vendor_id(value: Any) -> str:
	value = to_string_upper(value)
	if not re.search(_HARDWARE_ID_REGEX, value):
		raise ValueError(f"Bad hardware vendor id '{value}'")
	return value


def to_hardware_device_id(value: Any) -> str:
	value = to_string_upper(value)
	if not re.search(_HARDWARE_ID_REGEX, value):
		raise ValueError(f"Bad hardware device id '{value}'")
	return value


def to_opsi_timestamp(value: Any) -> str:
	"""
	Make `value` an opsi-compatible timestamp.

	This is a string with the format "YYYY-MM-DD HH:MM:SS".

	If a conversion is not possible a `ValueError` will be raised.
	"""
	if not value:
		return "0000-00-00 00:00:00"
	if isinstance(value, datetime.datetime):
		return to_string(value.strftime("%Y-%m-%d %H:%M:%S"))

	value = to_string(value)
	match = re.search(_OPSI_TIMESTAMP_REGEX, value)
	if not match:
		match = re.search(_OPSI_DATE_REGEX, value)
		if not match:
			raise ValueError(f"Bad OPSI timestamp: {value}")
		return f"{match.group(1)}-{match.group(2)}-{match.group(3)} 00:00:00"
	return f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}:{match.group(6)}"


def to_username(value: Any) -> str:
	value = to_string_lower(value)
	if not _USERNAME_REGEX.search(value):
		raise ValueError(f"Bad username: {value!r}")
	return value


to_user_id = to_username


def to_fqdn(value: Any) -> str:
	value = to_string_lower(value)
	if not _FQDN_REGEX.search(value):
		raise ValueError(f"Bad fqdn: '{value}'")
	if value.endswith("."):
		value = value[:-1]
	return value


to_host_id = to_fqdn


def to_host_id_list(value: Any) -> list[str]:
	return [to_host_id(element) for element in to_list(value)]


def to_hardware_address(value: Any) -> str:
	value = to_string_lower(value)
	if not value:
		return value

	match = re.search(_HARDWARE_ADDRESS_REGEX, value)
	if not match:
		raise ValueError(f"Invalid hardware address: {value}")

	return (f"{match.group(1)}:{match.group(2)}:{match.group(3)}:{match.group(4)}:{match.group(5)}:{match.group(6)}").lower()


def to_ip_address(value: Any) -> str:
	if not isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address, str)):
		raise ValueError(f"Invalid ip address: '{value}'")
	value = ipaddress.ip_address(value)
	if isinstance(value, ipaddress.IPv6Address) and value.ipv4_mapped:
		return value.ipv4_mapped.compressed
	return value.compressed


def to_host_address(value: Any) -> str:
	value = to_string_lower(value)
	try:
		try:
			try:
				value = to_ip_address(value)
			except Exception:
				value = to_fqdn(value)
		except Exception:
			value = to_hostname(value)
	except Exception as err:
		raise ValueError(f"Invalid host address: '{value}'") from err
	return value


def to_netmask(value: Any) -> str:
	value = to_string_lower(value)
	if not re.search(_NETMASK_REGEX, value):
		raise ValueError(f"Invalid netmask: '{value}'")
	return value


def to_network_address(value: Any) -> str:
	if not isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network, str)):
		raise ValueError(f"Invalid network address: '{value}'")
	return ipaddress.ip_network(value).compressed


def to_url(value: Any) -> str:
	"""
	Convert ``value`` to a valid URL.

	:rtype: str
	"""
	value = to_unicode(value)
	if not _URL_REGEX.search(value):
		raise ValueError(f"Bad url: '{value}'")
	return value


def to_opsi_host_key(value: Any) -> str:
	value = to_string_lower(value)
	if not re.search(_OPSI_HOST_KEY_REGEX, value):
		raise ValueError(f"Bad OPSI host key: {value}")
	return value


def to_product_version(value: Any) -> str:
	value = to_unicode(value)
	if not _PRODUCT_VERSION_REGEX.search(value):
		raise ValueError(f"Bad product version: '{value}'")
	return value


def to_product_version_list(value: Any) -> list[str]:
	return [to_product_version(element) for element in to_list(value)]


def to_package_version(value: Any) -> str:
	value = to_unicode(value)
	if not _PACKAGE_VERSION_REGEX.search(value):
		raise ValueError(f"Bad package version: '{value}'")
	return value


def to_package_version_list(value: Any) -> list[str]:
	return [to_package_version(element) for element in to_list(value)]


def to_product_id(value: Any) -> str:
	value = to_object_id(value)
	if not _PRODUCT_ID_REGEX.search(value):
		raise ValueError(f"Bad product id: '{value}'")
	return value


def to_product_id_list(value: Any) -> list[str]:
	return [to_product_id(element) for element in to_list(value)]


def to_package_custom_name(value: Any) -> str:
	value = to_string_lower(value)
	if not _PACKAGE_CUSTOM_NAME_REGEX.search(value):
		raise ValueError(f"Bad package custom name: '{value}'")
	return value


def to_product_type(value: Any) -> str:
	lower_value = to_string_lower(value)
	if lower_value in ("localboot", "localbootproduct"):
		return "LocalbootProduct"
	if lower_value in ("netboot", "netbootproduct"):
		return "NetbootProduct"
	raise ValueError(f"Unknown product type: '{value}'")


def to_product_property_id(value: Any) -> str:
	value = to_string_lower(value)
	if not _PRODUCT_PROPERTY_ID_REGEX.search(value):
		raise ValueError(f"Bad product property id: '{value}'")
	return value


def to_config_id(value: Any) -> str:
	value = to_string_lower(value)
	if not _CONFIG_ID_REGEX.search(value):
		raise ValueError(f"Bad config id: '{value}'")
	return value


def to_product_property_type(value: Any) -> str:
	value = to_string_lower(value)
	if value in ("unicode", "unicodeproductproperty"):
		return "UnicodeProductProperty"
	if value in ("bool", "boolproductproperty"):
		return "BoolProductProperty"
	raise ValueError(f"Unknown product property type: '{value}'")


def to_product_priority(value: Any) -> int:
	value = to_int(value)
	if value < -100:
		return -100
	if value > 100:
		return 100
	return value


def to_filename(value: Any) -> str:
	return to_unicode(value)


def to_product_target_configuration(value: Any) -> str:
	value = to_string_lower(value)
	if value and value not in ("installed", "always", "forbidden", "undefined"):
		raise ValueError(f"Bad product target configuration: '{value}'")
	return value


def to_installation_status(value: Any) -> str:
	value = to_string_lower(value)
	if value and value not in ("installed", "not_installed", "unknown"):
		raise ValueError(f"Bad installation status: '{value}'")
	return value


def to_action_request(value: Any) -> str | None:
	value = to_string_lower(value)
	if value:
		if value == "undefined":
			return None
		elif value not in ("setup", "uninstall", "update", "always", "once", "custom", "none"):
			raise ValueError(f"Bad action request: '{value}'")
	return value


def to_action_request_list(value: Any) -> list[str | None]:
	return [to_action_request(element) for element in to_list(value)]


def to_action_progress(value: Any) -> str:
	return to_unicode(value)


def to_action_result(value: Any) -> str | None:
	value = to_string_lower(value)
	if not value:
		return None
	if value not in ("failed", "successful", "none"):
		raise ValueError(f"Bad action result: '{value}'")
	return value


def to_requirement_type(value: Any) -> str | None:
	value = to_string_lower(value)
	if not value:
		return None
	if value not in ("before", "after"):
		raise ValueError(f"Bad requirement type: '{value}'")
	return value


def to_object_class(value: Any, objectClass: type[BaseObjectT]) -> BaseObjectT:
	global get_object_type
	global from_json

	if isinstance(value, objectClass):
		return value

	if isinstance(value, str) and value.startswith("{"):
		if not from_json:
			from opsi.opsiservice.model.object import from_json

		try:
			return from_json(value)
		except Exception as err:
			raise ValueError(f"{value!r} is not a {objectClass}: {err}") from err

	if isinstance(value, dict):
		if not get_object_type:
			from opsi.opsiservice.model.object import get_object_type
		try:
			_class = objectClass
			if "type" in value:
				try:
					_class = get_object_type(value["type"])
				except KeyError as err:
					raise ValueError(f"Invalid object type: {value['type']}") from err
				if not issubclass(_class, objectClass):
					raise ValueError(type(_class))
			return _class.fromHash(value)
		except Exception as err:
			raise ValueError(f"{value!r} is not a {objectClass}: {err}") from err

	raise ValueError(f"{value!r} is not a {objectClass}")


def to_object_class_list(value: Any, objectClass: type[BaseObjectT]) -> list[BaseObjectT]:
	return [to_object_class(element, objectClass) for element in to_list(value)]


def to_group_id(value: Any) -> str:
	value = to_object_id(value)
	if not _GROUP_ID_REGEX.search(value):
		raise ValueError(f"Bad group id: '{value}'")
	return value


def to_group_type(value: Any) -> str:
	lower_value = to_string_lower(value)

	if lower_value == "hostgroup":
		return "HostGroup"
	if lower_value == "productgroup":
		return "ProductGroup"
	raise ValueError(f"Unknown group type: '{value}'")


def to_group_type_list(value: Any) -> list[str]:
	return [to_group_type(element) for element in to_list(value)]


def to_group_id_list(value: Any) -> list[str]:
	return [to_group_id(element) for element in to_list(value)]


def to_object_id(value: Any) -> str:
	value = to_string_lower(value).strip()
	if not _OBJECT_ID_REGEX.search(value):
		raise ValueError(f"Bad object id: '{value}'")
	return value


def to_object_id_list(value: Any) -> list[str]:
	return [to_object_id(element) for element in to_list(value)]


def to_email_address(value: Any) -> str:
	value = to_string_lower(value)
	if not _EMAIL_REGEX.search(value):
		raise ValueError(f"Bad email address: '{value}'")
	return value


def to_domain(value: Any) -> str:
	value = to_string_lower(value)
	if not _DOMAIN_REGEX.search(value):
		raise ValueError(f"Bad domain: '{value}'")
	return value


def to_hostname(value: Any) -> str:
	value = to_string_lower(value)
	if not _HOSTNAME_REGEX.search(value):
		raise ValueError(f"Bad hostname: '{value}'")
	return value


def to_license_contract_id(value: Any) -> str:
	value = to_string_lower(value)
	if not _LICENSE_CONTRACT_ID_REGEX.search(value):
		raise ValueError(f"Bad license contract id: '{value}'")
	return value


def to_license_contract_id_list(value: Any) -> list[str]:
	return [to_license_contract_id(element) for element in to_list(value)]


def to_software_license_id(value: Any) -> str:
	value = to_string_lower(value)
	if not _SOFTWARE_LICENSE_ID_REGEX.search(value):
		raise ValueError(f"Bad software license id: '{value}'")
	return value


def to_software_license_id_list(value: Any) -> list[str]:
	return [to_software_license_id(element) for element in to_list(value)]


def to_license_pool_id(value: Any) -> str:
	value = to_string_lower(value)
	if not _LICENSE_POOL_ID_REGEX.search(value):
		raise ValueError(f"Bad license pool id: '{value}'")
	return value


def to_license_pool_id_list(value: Any) -> list[str]:
	return [to_license_pool_id(element) for element in to_list(value)]


def to_audit_state(value: Any) -> int:
	value = to_int(value)
	if value not in (0, 1):
		raise ValueError(f"Bad audit state value: {value}")
	return value


def to_language_code(value: Any) -> str:
	value = to_string_lower(value)
	match = _LANGUAGE_CODE_REGEX.search(value)
	if not match:
		raise ValueError(f"Bad language code: '{value}'")
	value = match.group(1)
	if match.group(2):
		value = f"{value}-{match.group(2).capitalize()}"
	if match.group(3):
		value = f"{value}-{match.group(3).upper()}"
	return value


def to_language_code_list(value: Any) -> list[str]:
	return [to_language_code(element) for element in to_list(value)]


def to_architecture(value: Any) -> str:
	value = to_string_lower(value)
	if not _ARCHITECTURE_REGEX.search(value):
		raise ValueError(f"Bad architecture: '{value}'")
	return value


def to_architecture_list(value: Any) -> list[str]:
	return [to_architecture(element) for element in to_list(value)]


def to_unique_list(_list: list[Any]) -> list[Any]:
	# Keep list order!
	return sorted(set(_list), key=_list.index)
