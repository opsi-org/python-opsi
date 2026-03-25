# opsi.system is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2021-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
This file is part of opsi - https://www.opsi.org
"""

from __future__ import annotations

import re
from collections.abc import MutableMapping
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Generator
from uuid import UUID

from opsi.opsi.service.model.type import Architecture

from ._infhash import calc_hash

RE_SECTION = re.compile(r"\[\s*([^\]]+)\s*\]")
RE_PLACEHOLDER = re.compile(r"%([^%]+)%")
RE_COMMENT = re.compile(r"(\".*?\"|\'.*?\')|([;][^\r\n]*$)", re.MULTILINE | re.DOTALL)

FLG_ADDREG_BINVALUETYPE = 0x00000001  # The given value is "raw" data. (This value is identical to the FLG_ADDREG_TYPE_BINARY.)
FLG_ADDREG_NOCLOBBER = 0x00000002  # Prevent a given value from replacing the value of an existing value entry.
FLG_ADDREG_DELVAL = (
	0x00000004  # Delete the given subkey from the registry, or delete the specified value-entry-name from the specified registry subkey.
)
FLG_ADDREG_APPEND = 0x00000008  # Append a given value to that of an existing named value entry. This flag is valid only if FLG_ADDREG_TYPE_MULTI_SZ is also set. The specified string value is not appended if it already exists.
FLG_ADDREG_KEYONLY = 0x00000010  # Create the given subkey, but ignore any supplied value-entry-name and/or value.
FLG_ADDREG_OVERWRITEONLY = (
	0x00000020  # Reset to the supplied value only if the specified value-entry-name already exists in the given subkey.
)
FLG_ADDREG_64BITKEY = 0x00001000  # (Windows XP and later versions of Windows.) Make the specified change in the 64-bit registry. If not specified, the change is made to the native registry.
FLG_ADDREG_KEYONLY_COMMON = 0x00002000  # (Windows XP and later versions of Windows.) This is the same as FLG_ADDREG_KEYONLY but also works in a del-registry-section of an INF DelReg directive.
FLG_ADDREG_32BITKEY = 0x00004000  # (Windows XP and later versions of Windows.) Make the specified change in the 32-bit registry. If not specified, the change is made to the native registry.
FLG_ADDREG_TYPE_MASK = 0xFFFF0001  # Mask for the type of the registry value entry.
FLG_ADDREG_TYPE_BINARY = 0x00000001  # The given value is "raw" data.
FLG_ADDREG_TYPE_SZ = 0x00000000  # The given value entry and/or value is of type REG_SZ. Note  This value is the default type for a specified value entry, so the flags value can be omitted from any reg-root= line in an add-registry-section that operates on a value entry of this type.
FLG_ADDREG_TYPE_MULTI_SZ = 0x00010000  # The given value entry and/or value is of the registry type REG_MULTI_SZ. The value field that follows can be a list of strings separated by commas. This specification does not require any NULL terminator for a given string value.
FLG_ADDREG_TYPE_EXPAND_SZ = 0x00020000  # The given value-entry-name and/or value is of the registry type REG_EXPAND_SZ.
FLG_ADDREG_TYPE_DWORD = 0x00010001  # The given value-entry-name and/or value is of the registry type REG_DWORD.
FLG_ADDREG_TYPE_NONE = 0x00020001  # The given value-entry-name and/or value is of the registry type REG_NONE.


def reg_dword(value: int) -> str:
	return f"dword:{value:08x}"


def reg_hex(value: bytes | str, null_terminated: bool = True) -> str:
	if isinstance(value, str):
		value = value.encode("utf-16le")
	if null_terminated:
		value += b"\x00\x00"
	return ",".join([f"{v:02x}" for v in value])


def reg_multi_sz(value: bytes | str | list[bytes | str]) -> str:
	if not isinstance(value, list):
		value = [value]
	if not value:
		raise ValueError("No values given")
	return "hex(7):" + ",".join([reg_hex(v) for v in value]) + ",00,00"


def reg_expand_sz(value: bytes | str) -> str:
	return f"hex(2):{reg_hex(value)}"


def current_timestamp() -> float:
	return datetime.now().timestamp()


class CaseInsensitiveDict(MutableMapping):  # TODO: why is this here?
	"""CaseInsensitiveDict from requests.structures"""

	def __init__(self, data: dict | None = None, **kwargs: Any) -> None:
		self._store: dict[str, Any] = {}
		if data is None:
			data = {}
		self.update(data, **kwargs)

	def __setitem__(self, key: str, value: Any) -> None:
		# Use the lowercased key for lookups, but store the actual
		# key alongside the value.
		self._store[key.lower()] = (key, value)

	def __getitem__(self, key: str) -> Any:
		return self._store[key.lower()][1]

	def __delitem__(self, key: str) -> None:
		del self._store[key.lower()]

	def __iter__(self) -> Generator[Any, None, None]:
		return (cased_key for cased_key, _ in self._store.values())

	def __len__(self) -> int:
		return len(self._store)

	def __repr__(self) -> str:
		return str(dict(self.items()))


class INFSectionType(StrEnum):
	STRINGS = "strings"
	VERSION = "version"
	MANUFACTURER = "manufacturer"
	DD_INSTALL = "DDInstall"
	DD_INSTALL_HW = "DDInstall.HW"
	SERVICE_INSTALL = "service-install-section"
	EVENT_LOG_INSTALL = "event-log-install"
	ADD_REGISTRY_SECTION = "add-registry-section"
	ADD_INTERFACE_SECTION = "add-interface-section"


@dataclass(kw_only=True)
class INFSection:
	name: str
	type: INFSectionType | None = None
	lines: list[str] = field(default_factory=list)
	ref_section: INFSection | None = None

	def __post_init__(self) -> None:
		self.name = self.name.strip().lower()
		if not self.type:
			if self.name == "strings":
				self.type = INFSectionType.STRINGS
			elif self.name == "version":
				self.type = INFSectionType.VERSION
			elif self.name.endswith(".hw"):
				self.type = INFSectionType.DD_INSTALL_HW
			elif self.name.endswith(".services"):
				self.type = INFSectionType.SERVICE_INSTALL


@dataclass(kw_only=True)
class INFDriverVer:
	date: datetime
	version: tuple[int, int, int, int]


@dataclass(kw_only=True)
class INFVersion:
	# https://learn.microsoft.com/en-us/windows-hardware/drivers/install/system-defined-device-setup-classes-available-to-vendors
	Class: str
	ClassGUID: str
	Provider: str
	DriverVer: INFDriverVer


@dataclass(kw_only=True)
class INFTargetOSVersion:
	Architecture: Architecture
	OSMajorVersion: int | None = None
	OSMinorVersion: int | None = None
	# VER_NT_xxxx flags defined in Winnt.h
	ProductType: int | None = None
	SuiteMask: int | None = None
	BuildNumber: int | None = None
	# NT[Architecture][.[OSMajorVersion][.[OSMinorVersion][.[ProductType][.SuiteMask]]]]
	# Starting with Windows 10, version 1607 (Build 14310 and later), the format of the TargetOSVersion decoration is as follows:
	# NT[Architecture][.[OSMajorVersion][.[OSMinorVersion][.[ProductType][.[SuiteMask][.[BuildNumber]]]]]

	@classmethod
	def from_string(cls, value: str) -> INFTargetOSVersion:
		value_lower = value.lower()
		if not value_lower.startswith("nt"):
			raise ValueError(f"Invalid TargetOSVersion: {value}")
		parts = value_lower.removeprefix("nt").split(".")
		version = INFTargetOSVersion(Architecture=Architecture(parts[0]))
		if len(parts) > 1:
			version.OSMajorVersion = _to_int(parts[1]) if parts[1] else None
		if len(parts) > 2:
			version.OSMinorVersion = _to_int(parts[2]) if parts[2] else None
		if len(parts) > 3:
			version.ProductType = _to_int(parts[3]) if parts[3] else None
		if len(parts) > 4:
			version.SuiteMask = _to_int(parts[4]) if parts[4] else None
		if len(parts) > 5:
			version.BuildNumber = _to_int(parts[5]) if parts[5] else None
		return version

	def to_string(self) -> str:
		value = (
			f"NT{self.Architecture.inf_value}"
			f".{'' if self.OSMajorVersion is None else self.OSMajorVersion}"
			f".{'' if self.OSMinorVersion is None else self.OSMinorVersion}"
			f".{'' if self.ProductType is None else self.ProductType}"
			f".{'' if self.SuiteMask is None else self.SuiteMask}"
			f".{'' if self.BuildNumber is None else self.BuildNumber}"
		)
		return value.rstrip(".")

	def __str__(self) -> str:
		return f"INFTargetOSVersion({self.to_string()})"

	def compare_version(self, other: INFTargetOSVersion) -> int:
		"""
		Compare two versions.
		Returns 1 if self > other, -1 if self < other, 0 if self == other
		"""
		if (self.OSMajorVersion or 0) > (other.OSMajorVersion or 0):
			return 1
		if (self.OSMajorVersion or 0) < (other.OSMajorVersion or 0):
			return -1
		if (self.OSMinorVersion or 0) > (other.OSMinorVersion or 0):
			return 1
		if (self.OSMinorVersion or 0) < (other.OSMinorVersion or 0):
			return -1
		if (self.BuildNumber or 0) > (other.BuildNumber or 0):
			return 1
		if (self.BuildNumber or 0) < (other.BuildNumber or 0):
			return -1
		return 0

	def matches_platform(self, other: INFTargetOSVersion) -> bool:
		if self.Architecture != other.Architecture:
			return False
		if other.ProductType is not None and self.ProductType != other.ProductType:
			return False
		if other.SuiteMask is not None and self.SuiteMask != other.SuiteMask:
			return False
		return True


@dataclass(kw_only=True)
class INFManufacturer:
	name: str
	models_section_name: str
	target_os_version: list[INFTargetOSVersion] = field(default_factory=list)


class DeviceType(StrEnum):
	ROOT = "ROOT"
	PCI = "PCI"
	USB = "USB"
	HDAUDIO = "HDAUDIO"
	INTELAUDIO = "INTELAUDIO"
	ACPI = "ACPI"
	MONITOR = "Monitor"
	MULTI = "*"


@dataclass(kw_only=True)
class INFHardwareID:
	"""
	device_type: ROOT / PCI / USB / HDAUDIO / ACPI / *
	vendor_id: four-character vendor id
	device_id: four-character device id
	subsystem_vendor_id: four-character subsystem vendor id
	subsystem_device_id: four-character subsystem device id
	revison: two-character revision number
	base_class_code: two-character base class code from the configuration space
	subclass_code: two-character subclass code
	programming_interface_code: two-character Programming Interface code
	"""

	device_type: str
	vendor_id: str | None = None
	device_id: str | None = None
	subsystem_vendor_id: str | None = None
	subsystem_device_id: str | None = None
	revision: str | None = None
	base_class_code: str | None = None
	subclass_code: str | None = None
	programming_interface_code: str | None = None
	custom_id: str | None = None
	hdaudio_function_group_type: str | None = None

	def __post_init__(self) -> None:
		self.vendor_id = self.vendor_id.upper() if self.vendor_id else None
		self.device_id = self.device_id.upper() if self.device_id else None
		self.subsystem_vendor_id = self.subsystem_vendor_id.upper() if self.subsystem_vendor_id else None
		self.subsystem_device_id = self.subsystem_device_id.upper() if self.subsystem_device_id else None

	@property
	def product_id(self) -> str | None:
		return self.device_id

	@property
	def subsystem_id(self) -> str | None:
		if self.subsystem_vendor_id or self.subsystem_device_id:
			return f"{self.subsystem_device_id or '0000'}{self.subsystem_vendor_id or '0000'}"
		return None

	@classmethod
	def from_string(cls, value: str) -> INFHardwareID:
		# https://learn.microsoft.com/de-de/windows-hardware/drivers/install/identifiers-for-pci-devices
		# https://learn.microsoft.com/de-de/windows-hardware/drivers/install/identifiers-for-hdaudio-devices
		# https://learn.microsoft.com/en-us/windows-hardware/drivers/bringup/device-management-namespace-objects
		if value.startswith("*"):
			str_device_type = "*"
			dev_ids = value[1:]
		elif "\\" in value:
			str_device_type, dev_ids = value.split("\\", 1)
		else:
			str_device_type = value
			dev_ids = ""

		try:
			device_type = DeviceType(str_device_type)
		except ValueError:
			device_type = None

		ids = {}
		if device_type in (None, DeviceType.MONITOR):
			ids["CUSTOM"] = dev_ids
		else:
			for dev_id in dev_ids.split("&"):
				dev_id = dev_id.upper()
				if "_" in dev_id:
					id_type, id_val = dev_id.split("_", 1)
					ids[id_type] = id_val
				else:
					# ACPI\vvv[v]dddd
					dev_idx = 3 if len(dev_id) < 8 else 4
					ids["VEN"] = dev_id[:dev_idx]
					ids["DEV"] = dev_id[dev_idx:]

		v_prefix = "VID" if str_device_type == DeviceType.USB else "VEN"
		d_prefix = "PID" if str_device_type == DeviceType.USB else "DEV"
		cc_code = ids.get("CC", "")
		return INFHardwareID(
			device_type=str_device_type,
			vendor_id=ids.get(v_prefix),
			device_id=ids.get(d_prefix),
			subsystem_vendor_id=None if ids.get("SUBSYS") is None else ids["SUBSYS"][4:],
			subsystem_device_id=None if ids.get("SUBSYS") is None else ids["SUBSYS"][:4],
			revision=ids.get("REV"),
			base_class_code=cc_code[0:2] if len(cc_code) > 0 else None,
			subclass_code=cc_code[2:4] if len(cc_code) > 2 else None,
			programming_interface_code=cc_code[4:6] if len(cc_code) > 4 else None,
			hdaudio_function_group_type=ids.get("FUNC"),
			custom_id=ids.get("CUSTOM"),
		)

	def to_string(self) -> str:
		if self.custom_id:
			return f"{self.device_type}\\{self.custom_id}"
		v_prefix = "VID" if self.device_type == DeviceType.USB else "VEN"
		d_prefix = "PID" if self.device_type == DeviceType.USB else "DEV"
		ids = []
		if self.hdaudio_function_group_type:
			ids.append(f"FUNC_{self.hdaudio_function_group_type}")
		if self.vendor_id:
			if self.device_type == DeviceType.ACPI and not self.subsystem_id and not self.revision:
				ids.append(self.vendor_id)
			else:
				ids.append(f"{v_prefix}_{self.vendor_id}")
		if self.device_id:
			if self.device_type == DeviceType.ACPI and not self.subsystem_id and not self.revision:
				ids[0] += self.device_id
			else:
				ids.append(f"{d_prefix}_{self.device_id}")
		if self.subsystem_id:
			ids.append(f"SUBSYS_{self.subsystem_id}")
		if self.revision:
			ids.append(f"REV_{self.revision}")
		if self.base_class_code:
			cc_code = self.base_class_code
			if self.subclass_code:
				cc_code += self.subclass_code
				if self.programming_interface_code:
					cc_code += self.programming_interface_code
			ids.append(f"CC_{cc_code}")

		if ids:
			return f"{self.device_type}\\{'&'.join(ids)}"
		return self.device_type

	def __str__(self) -> str:
		return f"INFHardwareID({self.to_string()})"


@dataclass(kw_only=True)
class INFDevice:
	description: str
	manufacturer: str
	configuration: str
	hardware_id: INFHardwareID | None = None
	compatible_ids: list[INFHardwareID] = field(default_factory=list)
	target_os_version: INFTargetOSVersion | None = None
	install_directives: list[INFInstallDirective] = field(default_factory=list)

	@property
	def hardware_ids(self) -> list[INFHardwareID]:
		hardware_ids = self.compatible_ids.copy()
		if self.hardware_id:
			hardware_ids.insert(0, self.hardware_id)
		return hardware_ids


@dataclass(kw_only=True)
class INFInstallDirective:
	section: INFSection


@dataclass(kw_only=True)
class INFAddRegDirective(INFInstallDirective):
	reg_root: str
	subkey: str | None = None
	value_entry_name: str | None = None
	flags: int | None = None
	values: list[str] = field(default_factory=list)
	security_descriptor_string: str | None = None


@dataclass(kw_only=True)
class INFDelRegDirective(INFInstallDirective):
	reg_root: str
	subkey: str
	value_entry_name: str | None = None
	flags: int | None = None


@dataclass(kw_only=True)
class INFBitRegDirective(INFInstallDirective):
	reg_root: str
	subkey: str
	value_entry_name: str | None = None
	flags: int | None = None
	byte_mask: int
	byte_to_modify: int


@dataclass(kw_only=True)
class INFRebootDirective(INFInstallDirective):
	pass


# https://learn.microsoft.com/en-us/windows-hardware/drivers/install/inf-addservice-directive
@dataclass(kw_only=True)
class INFServiceFailureActionsInstall:
	ResetPeriod: int
	NonCrashFailures: int
	Action: str


@dataclass(kw_only=True)
class INFServiceTriggerInstall:
	TriggerType: int
	Action: str
	SubType: int
	DataItem: str | None = None
	FailureActions: INFServiceFailureActionsInstall | None = None


@dataclass(kw_only=True)
class INFServiceInstallDirective(INFInstallDirective):
	ServiceName: str
	flags: int | None = None
	DisplayName: str | None = None
	Description: str | None = None
	ServiceType: int | None = None
	StartType: int | None = None
	ErrorControl: int | None = None
	ServiceBinary: str | None = None
	StartName: str | None = None
	LoadOrderGroup: str | None = None
	Dependencies: list[str] = field(default_factory=list)
	Security: str | None = None
	RequiredPrivileges: list[str] = field(default_factory=list)
	ServiceSidType: str | None = None
	DelayedAutoStart: int | None = None
	AddTrigger: list[INFServiceTriggerInstall] = field(default_factory=list)
	BootFlags: int | None = None
	AddReg: list[INFAddRegDirective] = field(default_factory=list)
	DelReg: list[INFDelRegDirective] = field(default_factory=list)
	BitReg: list[INFBitRegDirective] = field(default_factory=list)


def _to_int(value: int | str | None, base: int | None = None) -> int:
	if not value:
		return 0
	if isinstance(value, int):
		return value
	if base is not None:
		return int(value, base)
	try:
		return int(value, 0)
	except ValueError:
		return int(value, 16)


# https://docs.microsoft.com/de-de/windows-hardware/drivers/install
class INFFile:
	def __init__(self, path: str | Path, inf_name: str | None = None) -> None:
		self._file_path = Path(path).absolute()
		self._inf_name = inf_name or self._file_path.name.lower()
		self._encoding = "utf-16"
		self._hash: int | None = None
		self._sections: dict[str, INFSection] = {}
		self._strings: dict[str, str] = {}
		self._manufacturers: list[INFManufacturer] = []
		self._devices: list[INFDevice] = []
		self._parsed = False
		self.version: INFVersion | None = None
		if not self._file_path.exists():
			raise FileNotFoundError(f"INF file not found: '{self._file_path}'")

	@property
	def hash(self) -> int:
		if not self._hash:
			self._calc_hash()
		assert self._hash
		return self._hash

	@property
	def inf_name(self) -> str:
		return self._inf_name

	def _calc_hash(self) -> None:
		self._hash = calc_hash(self._file_path.read_bytes())

	@staticmethod
	def _remove_comments(line: str) -> str:
		def _replacer(match: re.Match) -> str:
			if match.group(2) is not None:
				return ""
			return match.group(1)

		return RE_COMMENT.sub(_replacer, line)

	def _get_string_placeholder(self, translation: str) -> str | None:
		for name, value in self._strings.items():
			if value == translation:
				return f"%{name}%"
		return None

	def _get_strings_section(self) -> INFSection:
		for section in self._sections.values():
			if section.type == INFSectionType.STRINGS:
				return section

		if "strings" in self._sections:
			self._sections["strings"].type = INFSectionType.STRINGS
			return self._sections["strings"]

		# Workaround for files with wrong section name
		placeholder_names = set()
		for section in self._sections.values():
			for line in section.lines:
				for match in RE_PLACEHOLDER.finditer(line):
					placeholder_names.add(match.group(1))

		for section in self._sections.values():
			matches = 0
			for line in section.lines:
				if "=" not in line:
					break
				if line.split("=", 1)[0].strip() in placeholder_names:
					matches += 1
			if matches > 1 and matches > len(section.lines) - 1:
				# Found strings section
				self._sections[section.name].type = INFSectionType.STRINGS
				return self._sections[section.name]

		raise RuntimeError(f"INF file '{self._file_path}' has no strings section")

	def _load_sections(self) -> None:
		self._sections = {}
		data = ""
		for encoding in ("utf-16", "utf-8", "windows-1258", "iso-8859-1"):
			try:
				with open(self._file_path, mode="r", encoding=encoding) as file:
					data = file.read()
					self._encoding = encoding
					break
			except UnicodeError:
				pass
		if not data:
			raise RuntimeError(f"Failed to parse inf file '{self._file_path}'")

		current_section: INFSection | None = None
		append_next = False
		for line in data.split("\n"):
			append = append_next
			append_next = line.strip().endswith("\\")
			line = self._remove_comments(line).strip()
			if not line:
				continue
			match = RE_SECTION.search(line)
			if match:
				current_section = INFSection(name=match.group(1).strip().lower())
				self._sections[current_section.name] = current_section
				continue
			if not current_section:
				continue
			if append:
				current_section.lines[-1] += line
			else:
				current_section.lines.append(line)

		# Get strings
		self._strings = {}
		for line in self._get_strings_section().lines:
			if "=" not in line:
				continue
			name, value = line.split("=", 1)
			self._strings[name.strip()] = value.strip().strip('"')

		# Replace placeholders
		placeholders = self._strings.copy()
		# DIRIDs
		# https://learn.microsoft.com/de-de/windows-hardware/drivers/install/using-dirids
		placeholders["11"] = "system32"
		placeholders["12"] = "system32\\drivers"
		for section in self._sections.values():
			for idx, line in enumerate(section.lines):
				for match in RE_PLACEHOLDER.finditer(line):
					if match.group(1) in placeholders:
						line = line.replace(match.group(0), placeholders[match.group(1)])
				section.lines[idx] = line.replace("%%", "%")

	def _load_version(self) -> None:
		# By convention, the Version section appears first in INF files. Every INF file must have this section.
		version_section = self._sections.get("version")
		if not version_section:
			raise RuntimeError(f"INF file '{self._file_path}' has no version section")

		field_names = [f.name for f in fields(INFVersion)]
		kwargs: dict[str, str | INFDriverVer] = {}
		for line in version_section.lines:
			if "=" not in line:
				continue
			val: str | INFDriverVer
			attr, val = line.split("=", 1)
			try:
				field_name = [f for f in field_names if f.lower() == attr.strip().lower()][0]
			except IndexError:
				continue

			val = val.strip()
			if field_name == "ClassGUID":
				val = val.strip("{}").upper()
			elif field_name == "DriverVer":
				date_str, version_str = [v.strip() for v in val.split(",", 1)]
				ver = [int(val) for val in version_str.split(".", 3)]
				while len(ver) < 4:
					ver.append(0)
				month, day, year = (int(val) for val in date_str.split("/"))
				date = datetime(year, month, day, tzinfo=timezone.utc)
				val = INFDriverVer(date=date, version=(ver[0], ver[1], ver[2], ver[3]))
			kwargs[field_name] = val
		self.version = INFVersion(**kwargs)  # type: ignore[arg-type]

	def _load_manufacturer(self) -> None:
		# The INF must also contain a corresponding INF Models section of the same name.
		self._manufacturers = []
		manufacturer_section = self._sections.get("manufacturer")
		if manufacturer_section:
			for line in manufacturer_section.lines:
				manufacturer_name, tmp1 = [v.strip() for v in line.split("=", 1)]
				tmp2 = [v.strip() for v in tmp1.split(",") if v != "NT"]
				models_section_name = tmp2[0]
				target_os_versions = []
				if len(tmp2) > 1:
					target_os_versions = [INFTargetOSVersion.from_string(v) for v in tmp2[1:] if v]
				self._manufacturers.append(
					INFManufacturer(name=manufacturer_name, models_section_name=models_section_name, target_os_version=target_os_versions)
				)
		else:
			default_install_sections = [s for s in self._sections if s.startswith("defaultinstall.") and s.count(".") == 1]
			if not default_install_sections:
				raise RuntimeError(f"INF file '{self._file_path}' has no manufacturer section and no defaultinstall section")
			target_os_versions = [INFTargetOSVersion.from_string(s.split(".")[-1]) for s in default_install_sections]
			self._manufacturers.append(
				INFManufacturer(
					name=self.version.Provider if self.version else "", models_section_name="", target_os_version=target_os_versions
				)
			)

	def _process_add_service_directive(self, section: INFSection, data: str) -> list[INFInstallDirective]:
		# https://learn.microsoft.com/en-us/windows-hardware/drivers/install/inf-addservice-directive
		# AddService=ServiceName,[flags],service-install-section[,event-log-install-section[,[EventLogType][,EventName]]]
		directives: list[INFInstallDirective] = []
		values = [v.strip() for v in data.split(",")]
		install = INFServiceInstallDirective(section=section, ServiceName=values[0], flags=_to_int(values[1]) if values[1] else None)
		if len(values) > 2 and values[2]:
			service_install_section = self._sections.get(values[2].lower())
			if service_install_section:
				service_install_section.type = INFSectionType.SERVICE_INSTALL
				service_install_section.ref_section = section
				for line in service_install_section.lines:
					directive_name, value = [val.strip() for val in line.split("=", 1)]
					if directive_name in ("AddReg", "DelReg", "BitReg"):
						value = self._process_directive(service_install_section, directive_name, value)
					elif directive_name in ("ServiceType", "StartType", "ErrorControl"):
						value = _to_int(value)
					setattr(install, directive_name, value)

		directives.insert(0, install)

		# TODO
		# if len(values) > 3:
		# 	event_log_install_section = values[3].lower()

		return directives

	def _process_add_reg_directive(self, section: INFSection, data: str) -> list[INFInstallDirective]:
		# https://learn.microsoft.com/en-us/windows-hardware/drivers/install/inf-addreg-directive
		# AddReg=add-registry-section[,add-registry-section] ...
		directives: list[INFInstallDirective] = []
		for add_registry_section_name in [v.strip().lower() for v in data.split(",")]:
			if not add_registry_section_name:
				continue

			add_registry_section = self._sections.get(add_registry_section_name)
			if not add_registry_section:
				raise RuntimeError(
					f"AddReg section {add_registry_section_name!r} not found in INF file '{self._file_path}' (sections={list(self._sections)})"
				)
			add_registry_section.type = INFSectionType.ADD_REGISTRY_SECTION
			add_registry_section.ref_section = section
			for line in add_registry_section.lines:
				tmp = [val.strip() for val in line.split(",")]
				directive = INFAddRegDirective(section=add_registry_section, reg_root=tmp[0])
				if len(tmp) > 1:
					directive.subkey = tmp[1].strip('"')
				if len(tmp) > 2:
					directive.value_entry_name = tmp[2].strip('"')
				if len(tmp) > 3:
					str_flags = tmp[3].strip('"')
					str_flags = self._strings.get(str_flags, str_flags)
					str_flags = str_flags.strip("\\")
					directive.flags = _to_int(str_flags, 16)
				if len(tmp) > 4:
					directive.values = tmp[4:]
				directives.append(directive)
		return directives

	def _process_directive(self, section: INFSection, directive_name: str, data: str | None) -> list[INFInstallDirective]:
		if directive_name == "AddService":
			assert data
			return self._process_add_service_directive(section, data)
		if directive_name == "AddReg":
			assert data
			return self._process_add_reg_directive(section, data)
		if directive_name == "Reboot":
			return [INFRebootDirective(section=section)]
		return []

	def _process_install_section(self, section_name: str) -> list[INFInstallDirective]:
		directives: list[INFInstallDirective] = []
		section = self._sections.get(section_name.lower())
		if not section:
			return directives
		for line in section.lines:
			line = line.replace(",\\", ", ")
			tmp = [val.strip() for val in line.split("=", 1)]
			directive_name = tmp[0]
			data = tmp[1] if len(tmp) > 1 else None
			directives.extend(self._process_directive(section, directive_name, data))
		return directives

	def _load_models(self) -> None:
		self._devices = []
		for manufacturer in self._manufacturers:
			models: list[tuple[str, INFTargetOSVersion | None]] = [(manufacturer.models_section_name, None)] + [
				(f"{manufacturer.models_section_name}.{v.to_string()}", v) for v in manufacturer.target_os_version
			]
			for models_section_name, target_os_version in models:
				section = self._sections.get(models_section_name.lower())
				if not section:
					continue
				for mod_line in section.lines:
					device_description, tmp1 = [val.strip() for val in mod_line.split("=", 1)]
					tmp2 = [val.strip() for val in tmp1.split(",")]
					install_section_name = tmp2[0].lower()
					hardware_id = INFHardwareID.from_string(tmp2[1]) if len(tmp2) > 1 else None
					compatible_ids = [INFHardwareID.from_string(v) for v in tmp2[2:]] if len(tmp2) > 2 else []

					check_section_names = [f"{install_section_name}.nt", install_section_name]
					if target_os_version:
						check_section_names.insert(0, f"{install_section_name}.nt{target_os_version.Architecture.inf_value}")

					section_names = [s for s in check_section_names if s.lower() in self._sections]
					# if len(section_names) > 1:
					# raise RuntimeError(f"Multiple install sections found: {section_names}")
					if not section_names:
						raise RuntimeError(f"Install section {install_section_name!r} not found in INF file '{self._file_path}'")

					for section_name in section_names:
						self._sections[section_name].type = INFSectionType.DD_INSTALL
						configuration = section_name  # s[0]
						device = INFDevice(
							description=device_description,
							manufacturer=manufacturer.name,
							configuration=configuration,
							hardware_id=hardware_id,
							compatible_ids=compatible_ids,
							target_os_version=target_os_version,
						)

						device.install_directives = self._process_install_section(configuration)
						for ext in ("Services", "HW"):
							ext_section = f"{configuration}.{ext}".lower()
							if ext_section in self._sections:
								device.install_directives.extend(self._process_install_section(ext_section))

						self._devices.append(device)

	def parse(self) -> None:
		"""
		Parse the inf file.
		"""
		self._parsed = False
		self._load_sections()
		self._load_version()
		self._load_manufacturer()
		self._load_models()
		self._parsed = True

	def _ensure_parsed(self) -> None:
		if not self._parsed:
			self.parse()

	def get_devices(
		self, target_os_version: INFTargetOSVersion, *, manufacturer: str | None = None, hardware_id: INFHardwareID | None = None
	) -> list[INFDevice]:
		self._ensure_parsed()
		devices: dict[str, INFDevice] = {}
		for device in self._devices:
			if manufacturer and device.manufacturer.lower() != manufacturer.lower():
				continue

			if hardware_id:
				device_hardware_ids = device.hardware_ids
				if not device_hardware_ids:
					continue

				match = False
				for device_hardware_id in device_hardware_ids:
					if hardware_id.device_type and hardware_id.device_type != device_hardware_id.device_type:
						continue
					if hardware_id.device_id and device_hardware_id.device_id and hardware_id.device_id != device_hardware_id.device_id:
						continue
					if hardware_id.vendor_id and device_hardware_id.vendor_id and hardware_id.vendor_id != device_hardware_id.vendor_id:
						continue
					if (
						hardware_id.subsystem_id
						and device_hardware_id.subsystem_id
						and hardware_id.subsystem_id != device_hardware_id.subsystem_id
					):
						continue
					if hardware_id.revision and device_hardware_id.revision and hardware_id.revision != device_hardware_id.revision:
						continue
					match = True
					break

				if not match:
					continue

			if device.target_os_version is not None:
				if not device.target_os_version.matches_platform(target_os_version):
					continue
				if device.target_os_version.OSMajorVersion is not None and target_os_version.OSMajorVersion is not None:
					if device.target_os_version.OSMajorVersion > target_os_version.OSMajorVersion:
						continue
					if (
						device.target_os_version.OSMajorVersion == target_os_version.OSMajorVersion
						and device.target_os_version.OSMinorVersion is not None
						and target_os_version.OSMinorVersion is not None
					):
						if device.target_os_version.OSMinorVersion > target_os_version.OSMinorVersion:
							continue
						if (
							device.target_os_version.OSMinorVersion == target_os_version.OSMinorVersion
							and device.target_os_version.BuildNumber is not None
							and target_os_version.BuildNumber is not None
						):
							if device.target_os_version.BuildNumber > target_os_version.BuildNumber:
								continue

			# Check if already added device is closer to the target_os_version
			hardware_id_str = device.hardware_id.to_string() if device.hardware_id else ""
			added_device = devices.get(hardware_id_str)
			if added_device:
				if not device.target_os_version:
					continue
				if added_device.target_os_version and added_device.target_os_version.compare_version(device.target_os_version) >= 0:
					continue
			devices[hardware_id_str] = device

		return list(devices.values())

	@staticmethod
	def _add_reg_to_reg(ref_key: str, add_reg: list[INFAddRegDirective]) -> dict[str, list[str]]:
		reg: dict[str, list[str]] = {}
		for add_r in add_reg:
			key = ""
			if add_r.reg_root == "HKR":
				key = ref_key
			elif add_r.reg_root == "HKCR":
				key = "HKEY_CLASSES_ROOT"
			elif add_r.reg_root == "HKCU":
				key = "HKEY_CURRENT_USER"
			elif add_r.reg_root == "HKLM":
				key = "HKEY_LOCAL_MACHINE"
			elif add_r.reg_root == "HKU":
				key = "HKEY_USERS"
			else:
				raise NotImplementedError(f"Root not implemented: {add_r}")

			if add_r.subkey:
				key = rf"{key}\{add_r.subkey}"
			if key not in reg:
				reg[key] = []
			if add_r.flags != FLG_ADDREG_KEYONLY:
				value = None
				# FLG_ADDREG_TYPE_SZ is the default
				flags = add_r.flags or FLG_ADDREG_TYPE_SZ
				addreg_type = flags & FLG_ADDREG_TYPE_MASK
				if addreg_type == FLG_ADDREG_TYPE_SZ:
					val = add_r.values[0].strip('"') if add_r.values else ""
					value = f'"{val}"'
				elif addreg_type == FLG_ADDREG_TYPE_MULTI_SZ:
					val = add_r.values[0].strip('"')
					value = reg_multi_sz([v.strip() for v in val.split(",")])
				elif addreg_type == FLG_ADDREG_TYPE_EXPAND_SZ:
					val = add_r.values[0].strip('"')
					value = reg_expand_sz(val)
				elif addreg_type == FLG_ADDREG_TYPE_DWORD:
					value = reg_dword(int(add_r.values[0], 0))
				elif addreg_type == FLG_ADDREG_TYPE_BINARY:
					value = f"hex:{','.join(add_r.values)}"
				elif addreg_type == FLG_ADDREG_TYPE_NONE:
					raise NotImplementedError(f"Type NONE not implemented: {add_r}")
				else:
					raise NotImplementedError(f"Flag not implemented: {add_r}")
				val = f'"{add_r.value_entry_name}"={value}'
				if val not in reg[key]:
					reg[key].append(val)
		return reg

	@staticmethod
	def _reg_dict_to_str(reg: dict[str, list[str]]) -> str:
		reg_str = ""
		for subkey in sorted(reg):
			reg_str += f"[{subkey}]\r\n"
			if reg[subkey]:
				reg_str += "\r\n".join(reg[subkey]) + "\r\n"
			reg_str += "\r\n"
		return reg_str

	def get_services_reg(
		self,
		target_os_version: INFTargetOSVersion,
		hardware_id: INFHardwareID | None = None,
		oem_inf_name: str = "oem0.inf",
		services_root: str = r"HKEY_LOCAL_MACHINE\SYSTEM\ControlSet001\Services",
	) -> str:
		self._ensure_parsed()
		reg = {}
		devices = self.get_devices(target_os_version, hardware_id=hardware_id)
		if not devices:
			raise RuntimeError(f"No devices found for {target_os_version} and {hardware_id}")

		for device in devices:
			for directive in device.install_directives:
				if isinstance(directive, INFServiceInstallDirective):
					svc_key = rf"{services_root}\{directive.ServiceName}"
					display_name = directive.DisplayName or ""
					reg[svc_key] = [
						f'"ImagePath"={reg_expand_sz(str(directive.ServiceBinary))}',
						f'"DisplayName"="@{oem_inf_name},{self._get_string_placeholder(display_name) or ""};{display_name}"',
						f'"Type"={reg_dword(directive.ServiceType or 0)}',
						f'"Start"={reg_dword(directive.StartType or 0)}',
						f'"ErrorControl"={reg_dword(directive.ErrorControl or 0)}',
						f'"Owners"={reg_multi_sz(oem_inf_name)}',
					]
					if directive.LoadOrderGroup:
						reg[svc_key].append(f'"Group"="{directive.LoadOrderGroup}"')
					reg.update(self._add_reg_to_reg(svc_key, directive.AddReg))

		return self._reg_dict_to_str(reg)

	def get_driver_database_dir_name(self, arch: Architecture) -> str:
		return f"{self.inf_name}_{arch.inf_value}_{self.hash:08x}"

	def get_device_hardware_reg(
		self,
		target_os_version: INFTargetOSVersion,
		hardware_id: INFHardwareID | None = None,
		oem_inf_name: str = "oem0.inf",
		database_root: str = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum",
	) -> str:
		# HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\PCI\VEN_1234&DEV_1111&SUBSYS_11001AF4&REV_02\3&13c0b0c5&0&10
		raise NotImplementedError("Not implemented")

	def get_device_software_reg(
		self,
		target_os_version: INFTargetOSVersion,
		hardware_id: INFHardwareID | None = None,
		oem_inf_name: str = "oem0.inf",
		database_root: str = r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class",
	) -> str:
		# HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Class\{4D36E972-E325-11CE-BFC1-08002BE10318}
		raise NotImplementedError("Not implemented")

	def get_driver_database_reg(
		self,
		target_os_version: INFTargetOSVersion,
		hardware_id: INFHardwareID | None = None,
		oem_inf_name: str = "oem0.inf",
		database_root: str = r"HKEY_LOCAL_MACHINE\SYSTEM\DriverDatabase",
	) -> str:
		self._ensure_parsed()
		reg = {}

		configurations: dict[str, list[INFDevice]] = {}
		devices = self.get_devices(target_os_version, hardware_id=hardware_id)
		if not devices:
			raise RuntimeError(f"No devices found for {target_os_version} and {hardware_id}")

		for device in devices:
			if device.configuration not in configurations:
				configurations[device.configuration] = []
			configurations[device.configuration].append(device)

			if device.hardware_id:
				reg[rf"{database_root}\DeviceIds\{device.hardware_id.to_string()}"] = [f'"{oem_inf_name}"=hex:01,ff,00,00']
			for compatible_id in device.compatible_ids:
				reg[rf"{database_root}\DeviceIds\{compatible_id.to_string()}"] = [f'"{oem_inf_name}"=hex:02,ff,00,00']

		driver_dir_name = self.get_driver_database_dir_name(arch=target_os_version.Architecture)
		reg[rf"{database_root}\DriverInfFiles\{oem_inf_name}"] = [
			f"@={reg_multi_sz(driver_dir_name)}",
			f'"Active"="{driver_dir_name}"',
			f'"Configurations"={reg_multi_sz(list(configurations))}',
		]

		package_root = rf"{database_root}\DriverPackages\{driver_dir_name}"
		assert self.version
		guid = UUID(self.version.ClassGUID)
		version = self.version.DriverVer.version
		# 100-nanoseconds since Jan 1 1601
		timestamp = int((self.version.DriverVer.date.timestamp() - datetime(1601, 1, 1, tzinfo=timezone.utc).timestamp()) * 10_000_000)
		hex_version = reg_hex(
			b"\x00\xff\x09\x00\x00\x00\x00\x00"
			+ guid.bytes_le
			+ timestamp.to_bytes(8, "little")
			+ version[3].to_bytes(2, "little")
			+ version[2].to_bytes(2, "little")
			+ version[1].to_bytes(2, "little")
			+ version[0].to_bytes(2, "little")
			+ b"\x00" * 8,
			null_terminated=False,
		)
		import_date = reg_hex(
			int((current_timestamp() - datetime(1601, 1, 1, tzinfo=timezone.utc).timestamp()) * 10_000_000).to_bytes(8, "little"),
			null_terminated=False,
		)
		reg[package_root] = [
			f'"Version"=hex:{hex_version}',
			f'"Provider"="{self.version.Provider or ""}"',
			f'"InfName"="{self.inf_name}"',
			'"OemPath"="opsi"',
			f'"ImportDate"=hex:{import_date}',
			# TODO
			# f'"Catalog"="driver.cat"'
			'"SignerName"="Microsoft Windows Hardware Compatibility Publisher"',
			'"SignerScore"=dword:0d000005',
			'"StatusFlags"=dword:00000012',
			f'@="{oem_inf_name}"',
		]

		reg[rf"{package_root}\Configurations"] = []
		for configuration, configuration_devices in configurations.items():
			service_install_directives: list[INFServiceInstallDirective] = []
			dev_add_reg_directives: list[INFAddRegDirective] = []
			for device in configuration_devices:
				service_install_directives.extend([d for d in device.install_directives if isinstance(d, INFServiceInstallDirective)])
				for directive in device.install_directives:
					if (
						isinstance(directive, INFAddRegDirective)
						and directive.section.ref_section
						and directive.section.ref_section.type
						in (
							INFSectionType.DD_INSTALL,
							INFSectionType.DD_INSTALL_HW,
						)
					):
						dev_add_reg_directives.append(directive)

			vals = []
			if service_install_directives:
				vals.append(f'"Service"="{service_install_directives[0].ServiceName}"')
			vals.append('"ConfigScope"=dword:00000007')
			vals.append('"ConfigFlags"=dword:00000000')
			reg[rf"{package_root}\Configurations\{configuration}"] = vals

			dev_key = rf"{package_root}\Configurations\{configuration}\Device"
			reg[dev_key] = []

			reg.update(self._add_reg_to_reg(dev_key, dev_add_reg_directives))

			reg[rf"{package_root}\Configurations\{configuration}\Services"] = []

			for sid in service_install_directives:
				svc_key = rf"{package_root}\Configurations\{configuration}\Services\{sid.ServiceName}"
				if not any([not ar.subkey for ar in sid.AddReg]):
					# No entry without subkey
					reg[svc_key] = []
				reg.update(self._add_reg_to_reg(svc_key, sid.AddReg))

		reg[rf"{package_root}\Descriptors"] = []

		cur_parent_key = None
		for device in devices:
			device_hardware_ids = device.compatible_ids.copy()
			if device.hardware_id:
				device_hardware_ids.insert(0, device.hardware_id)

			for device_id in device_hardware_ids:
				key = rf"{package_root}\Descriptors\{device_id.to_string()}"
				parent_key = "\\".join(key.split("\\")[:-1])
				if cur_parent_key != parent_key:
					reg[parent_key] = []
					cur_parent_key = parent_key

				reg[key] = [
					f'"Configuration"="{configuration}"',
					f'"Manufacturer"="{device.manufacturer}"',
					f'"Description"="{device.description}"',
				]

		return self._reg_dict_to_str(reg)

	def is_compatible(self, target_os_version: INFTargetOSVersion, hardware_id: INFHardwareID | None = None) -> bool:
		return bool(self.get_devices(target_os_version, hardware_id=hardware_id))
