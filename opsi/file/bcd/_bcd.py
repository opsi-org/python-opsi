# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

import base64
import gzip
import os
import pathlib
import sys
from struct import pack
from typing import IO
from uuid import UUID

import hivex

BCD_TEMPLATE = """
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
Bv4Ps1fWggCQAAA=
"""

BCD_OBJECTS = {
	"0ce4991b-e6b3-4b16-b23c-5e0d9250e5d9": {"symbolic_name": "GUID_EMS_SETTINGS_GROUP", "friendly_name": "{emssettings}"},
	"1afa9c49-16ab-4a5c-4a90-212802da9460": {
		"symbolic_name": "GUID_RESUME_LOADER_SETTINGS_GROUP",
		"friendly_name": "{resumeloadersettings}",
	},
	"1cae1eb7-a0df-4d4d-9851-4860e34ef535": {"symbolic_name": "GUID_DEFAULT_BOOT_ENTRY", "friendly_name": "{default}"},
	"313e8eed-7098-4586-a9bf-309c61f8d449": {
		"symbolic_name": "GUID_KERNEL_DEBUGGER_SETTINGS_GROUP",
		"friendly_name": "{kerneldbgsettings}",
	},
	"4636856e-540f-4170-a130-a84776f4c654": {"symbolic_name": "GUID_DEBUGGER_SETTINGS_GROUP", "friendly_name": "{eventsettings}"},
	"466f5a88-0af2-4f76-9038-095b170dc21c": {"symbolic_name": "GUID_WINDOWS_LEGACY_NTLDR", "friendly_name": "{ntldr}"},
	"5189b25c-5558-4bf2-bca4-289b11bd29e2": {"symbolic_name": "GUID_BAD_MEMORY_GROUP", "friendly_name": "{badmemory}"},
	"6efb52bf-1766-41db-a6b3-0ee5eff72bd7": {"symbolic_name": "GUID_BOOT_LOADER_SETTINGS_GROUP", "friendly_name": "{bootloadersettings}"},
	"7254a080-1510-4e85-ac0f-e7fb3d444736": {"symbolic_name": "GUID_WINDOWS_SETUP_EFI", "friendly_name": None},
	"7ea2e1ac-2e61-4728-aaa3-896d9d0a9f0e": {"symbolic_name": "GUID_GLOBAL_SETTINGS_GROUP", "friendly_name": "{globalsettings}"},
	"7ff607e0-4395-11db-b0de-0800200c9a66": {"symbolic_name": "GUID_HYPERVISOR_SETTINGS_GROUP", "friendly_name": "{hypervisorsettings}"},
	"9dea862c-5cdd-4e70-acc1-f32b344d4795": {"symbolic_name": "GUID_WINDOWS_BOOTMGR", "friendly_name": "{bootmgr}"},
	"a1943bbc-ea85-487c-97c7-c9ede908a38a": {"symbolic_name": "GUID_WINDOWS_OS_TARGET_TEMPLATE_PCAT", "friendly_name": None},
	"a5a30fa2-3d06-4e9f-b5f4-a01df9d1fcba": {"symbolic_name": "GUID_FIRMWARE_BOOTMGR", "friendly_name": "{fwbootmgr}"},
	"ae5534e0-a924-466c-b836-758539a3ee3a": {"symbolic_name": "GUID_WINDOWS_SETUP_RAMDISK_OPTIONS", "friendly_name": "{ramdiskoptions}"},
	"b012b84d-c47c-4ed5-b722-c0c42163e569": {"symbolic_name": "GUID_WINDOWS_OS_TARGET_TEMPLATE_EFI", "friendly_name": None},
	"b2721d73-1db4-4c62-bf78-c548a880142d": {"symbolic_name": "GUID_WINDOWS_MEMORY_TESTER", "friendly_name": "{memdiag}"},
	"cbd971bf-b7b8-4885-951a-fa03044f5d71": {"symbolic_name": "GUID_WINDOWS_SETUP_PCAT", "friendly_name": None},
	"fa926493-6f1c-4193-a414-58f0b2456d1e": {"symbolic_name": "GUID_CURRENT_BOOT_ENTRY", "friendly_name": "{current}"},
}

BCDE_LIBRARY_TYPE_APPLICATION_DEVICE = 0x11000001
BCDE_LIBRARY_TYPE_APPLICATION_PATH = 0x12000002
BCDE_LIBRARY_TYPE_DESCRIPTION = 0x12000004
BCDE_LIBRARY_TYPE_PREFERRED_LOCALE = 0x12000005
BCDE_LIBRARY_TYPE_INHERIT = 0x14000006
BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES = 0x16000049
BCDE_OSLOADER_TYPE_OS_DEVICE = 0x21000001
BCDE_OSLOADER_TYPE_SYSTEM_ROOT = 0x22000002
BCDE_OSLOADER_TYPE_LOG_INITIALIZATION = 0x26000090
BCDE_OSLOADER_TYPE_KERNEL_DEBUGGER_ENABLED = 0x260000A0

OSLOADER_ELEMENTS = {
	BCDE_LIBRARY_TYPE_APPLICATION_DEVICE: {"symbolic_name": "BCDE_LIBRARY_TYPE_APPLICATION_DEVICE", "friendly_name": "device"},
	BCDE_LIBRARY_TYPE_APPLICATION_PATH: {"symbolic_name": "BCDE_LIBRARY_TYPE_APPLICATION_PATH", "friendly_name": "path"},
	BCDE_LIBRARY_TYPE_DESCRIPTION: {"symbolic_name": "BCDE_LIBRARY_TYPE_DESCRIPTION", "friendly_name": "description"},
	BCDE_LIBRARY_TYPE_PREFERRED_LOCALE: {"symbolic_name": "BCDE_LIBRARY_TYPE_PREFERRED_LOCALE", "friendly_name": "locale"},
	BCDE_OSLOADER_TYPE_OS_DEVICE: {"symbolic_name": "BCDE_OSLOADER_TYPE_OS_DEVICE", "friendly_name": "osdevice"},
	BCDE_OSLOADER_TYPE_SYSTEM_ROOT: {"symbolic_name": "BCDE_OSLOADER_TYPE_SYSTEM_ROOT", "friendly_name": "systemroot"},
	BCDE_LIBRARY_TYPE_INHERIT: {"symbolic_name": "BCDE_LIBRARY_TYPE_INHERIT", "friendly_name": "inherit"},
	BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES: {
		"symbolic_name": "BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES",
		"friendly_name": "testsigning",
	},
	BCDE_OSLOADER_TYPE_LOG_INITIALIZATION: {"symbolic_name": "BCDE_OSLOADER_TYPE_LOG_INITIALIZATION", "friendly_name": "bootlog"},
	BCDE_OSLOADER_TYPE_KERNEL_DEBUGGER_ENABLED: {"symbolic_name": "BCDE_OSLOADER_TYPE_KERNEL_DEBUGGER_ENABLED", "friendly_name": "debug"},
}

OBJECT_TYPES = {1: "application object", 2: "inherit object", 3: "device object"}

IMAGE_TYPES = {1: "firmware application", 2: "windows boot application", 3: "legacy loader application", 4: "real-mode application"}

APPLICATION_TYPES = {
	1: "fwbootmgr",
	2: "bootmgr",
	3: "osloader",
	4: "resume",
	5: "memdiag",
	6: "ntldr",
	7: "setupldr",
	8: "bootsector",
	9: "startup	all",
	10: "bootapp",
}

INHERIT_TYPES = {1: "inheritable by any object", 2: "inheritable by application objects", 3: "inheritable by device objects"}

DEVICE_TYPES = {0: "disk", 2: "legacy partition", 3: "serial", 4: "udp", 5: "boot", 6: "partition", 8: "locate"}


class BCD:
	def __init__(self, filename: str | pathlib.Path, create_from_template: bool = False) -> None:
		self.filename = filename
		if isinstance(self.filename, pathlib.Path):
			self.filename = str(self.filename)
		if create_from_template:
			self.write_template()
		if not os.path.exists(self.filename):
			raise FileNotFoundError(f"BCD not found: {self.filename}")
		self.hive = hivex.Hivex(self.filename, write=True)

	def write_template(self) -> None:
		with open(self.filename, "wb") as file:
			file.write(gzip.decompress(base64.b64decode(BCD_TEMPLATE)))

	def get_node_by_path(self, path: str | None = None) -> int:
		node = self.hive.root()
		if not path:
			return node
		for name in path.split("\\"):
			if not name:
				continue
			cnode = self.hive.node_get_child(node, name)
			if cnode is None:
				raise ValueError(f"Node not found: {name}")
			node = cnode
		return node

	def print_tree(self, path: str | None = None, file: IO | None = None) -> None:
		if not file:
			file = sys.stdout
		node = self.get_node_by_path(path)
		if node == self.hive.root():
			path = "\\"
		assert path
		if path != "\\" and not path.startswith("\\\\"):
			path = f"\\{path}"

		print(f"[{path}]", file=file)
		for value_id in self.hive.node_values(node):
			print(self.format_value(value_id), file=file)
		print("", file=file)
		children = self.hive.node_children(node)
		for child_id in children:
			self.print_tree(f"{path}\\{self.hive.node_name(child_id)}", file)

	def get_value(self, value_id: int) -> str:
		vtype = self.hive.value_type(value_id)[0]
		if vtype == 1:
			return self.hive.value_string(value_id)
		if vtype == 4:
			return self.hive.value_dword(value_id)
		return self.hive.value_value(value_id)[1]

	def format_value(self, value_id: int, with_key: bool = True) -> str:
		key = self.hive.value_key(value_id)
		value = self.get_value(value_id)
		vtype = self.hive.value_type(value_id)[0]
		if vtype == 1:
			value = f'"{value}"'
		elif vtype in (3, 7):
			value = ",".join([f"{v:02x}" for v in value])
			value = f"hex({vtype}):{value}"
		elif vtype == 4:
			value = f"dword:0x{value:08x} ({value})"
		else:
			value = "{vtype}:{value}"

		if with_key:
			return f'"{key}"={value}'
		return value

	@staticmethod
	def decode_object_type(value: int) -> dict:
		decoded: dict[str, int | str] = {}
		decoded["object_type_raw"] = (0xF0000000 & value) >> 28
		decoded["object_type"] = OBJECT_TYPES.get(int(decoded["object_type_raw"]), "unknown")
		if decoded["object_type_raw"] == 1:
			# application object
			decoded["image_type_raw"] = (0x00F00000 & value) >> 20
			decoded["image_type"] = IMAGE_TYPES.get(int(decoded["image_type_raw"]), "unknown")
			decoded["application_type_raw"] = 0xFFFFF & value
			decoded["application_type"] = APPLICATION_TYPES.get(int(decoded["application_type_raw"]), "unknown")
		elif decoded["object_type_raw"] == 2:
			decoded["inherit_type_raw"] = (0x00F00000 & value) >> 20
			decoded["inherit_type"] = INHERIT_TYPES.get(int(decoded["inherit_type_raw"]), "unknown")
		return decoded

	@staticmethod
	def get_device_info_offset(data: bytes) -> int:
		options_id = UUID(bytes_le=data[:16])
		if str(options_id) == "00000000-0000-0000-0000-000000000000":
			return 0
		return 52

	@staticmethod
	def decode_device_data(data: bytes) -> dict:
		# MBR example:
		# c8,dc,19,76,fe,fa,d9,11,b4,11,00,04,76,eb,a2,5f (16)
		# 00,00,00,00,01,00,00,00,a0,00,00,00,00,00,00,00 (32)
		# 03,00,00,00,00,00,00,00,00,00,00,00,00,00,00,00 (48)
		# 00,00,00,00|00,00,00,00,01,00,00,00,78,00,00,00 (64)
		# 05,00,00,00|05|00,00,00,00,00,00,00,48,00,00,00 (80)
		# 00,00,00,00,00,00,d0,d5,03,00,00,00,00,00,00,00 (96)
		# 00,00,00,00,00,00,00,00,00,00,00,00,2e,b4,a0,49 (112)
		# 2f,96,7f,42,be,78,70,2e,7d,34,50,66,00,00,00,00 (128)
		# 00,00,00,00,00,00,00,00,00,00,00,00,5c|00,73,00 (144)
		# 6f,00,75,00,72,00,63,00,65,00,73,00,5c,00,62,00 (160)
		# 6f,00,6f,00,74,00,2e,00,77,00,69,00,6d,00,00,00 (176)

		# GPT example:
		# c8,dc,19,76,fe,fa,d9,11,b4,11,00,04,76,eb,a2,5f (16)
		# 00,00,00,00,01,00,00,00,a0,00,00,00,00,00,00,00 (32)
		# 03,00,00,00,00,00,00,00,00,00,00,00,00,00,00,00 (48)
		# 00,00,00,00,00,00,00,00,01,00,00,00,78,00,00,00 (64)
		# 05,00,00,00,06,00,00,00,00,00,00,00,48,00,00,00 (80)
		# 00,00,00,00|0b,da,9b,f8,9f,8a,2a,47,aa,c8,80,44 (96)
		# fa,df,b2,40|00,00,00,00,00,00,00,00|46,7c,1f,6e (112)
		# 39,06,86,43,82,e3,e2,0c,98,94,80,25|00,00,00,00 (128)
		# 00,00,00,00,00,00,00,00,00,00,00,00,5c,00,73,00 (144)
		# 6f,00,75,00,72,00,63,00,65,00,73,00,5c,00,62,00 (160)
		# 6f,00,6f,00,74,00,2e,00,77,00,69,00,6d,00,00,00 (176)

		# print(",".join([f"{v:02x}" for v in data]))
		offset = BCD.get_device_info_offset(data)
		decoded: dict[str, int | str] = {}
		decoded["options_id"] = str(UUID(bytes_le=data[:16]))
		decoded["device_type_raw"] = data[offset + 16]
		decoded["device_type"] = DEVICE_TYPES.get(int(decoded["device_type_raw"]), "unknown")
		decoded["ramdisk_path"] = data[offset + 88 :].decode("utf-16-le").rstrip("\x00")
		if decoded["device_type"] == "partition":
			if data[offset + 60 : offset + 72] == b"\x00" * 12:
				decoded["disk_id"] = int.from_bytes(data[offset + 56 : offset + 60], byteorder="little", signed=False)
				decoded["partition_offset"] = int.from_bytes(data[offset + 32 : offset + 40], byteorder="little", signed=False)
			else:
				decoded["disk_id"] = str(UUID(bytes_le=data[offset + 56 : offset + 72]))
				decoded["partition_id"] = str(UUID(bytes_le=data[offset + 32 : offset + 48]))
		return decoded

	def get_application_object_node_ids(self, entry_filter: list[str] | None = None) -> list[int]:
		root = self.hive.root()
		default_id = self.get_default_boot_entry_guid()
		node_ids = []
		for node_id in self.hive.node_children(self.hive.node_get_child(root, "Objects")):
			obj_type = self.hive.value_dword(self.hive.node_values(self.hive.node_get_child(node_id, "Description"))[0])
			obj_type = self.decode_object_type(obj_type)
			if obj_type["object_type_raw"] != 1:
				continue

			elements_id = self.hive.node_get_child(node_id, "Elements")
			if entry_filter:
				identifier = self.hive.node_name(node_id)
				friendly_name = BCD_OBJECTS.get(identifier[1:-1], {}).get("friendly_name")
				description = None
				element_id = self.hive.node_get_child(elements_id, f"{BCDE_LIBRARY_TYPE_DESCRIPTION:x}")
				if element_id:
					value_id = self.hive.node_values(element_id)[0]
					description = self.hive.value_string(value_id)
				default = default_id == identifier and "{default}" in entry_filter
				if identifier not in entry_filter and friendly_name not in entry_filter and description not in entry_filter and not default:
					continue

			node_ids.append(node_id)

		return node_ids

	def get_default_boot_entry_guid(self) -> str:
		default_boot_el_id = self.get_node_by_path(r"\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\23000003")
		return self.hive.value_string(self.hive.node_values(default_boot_el_id)[0])

	def print_boot_entries(self, file: IO | None = None) -> None:
		if not file:
			file = sys.stdout
		for entry in self.get_boot_entries():
			print(entry["identifier"], file=file)
			for attr in (
				"friendly_name",
				"default",
				"description",
				"locale",
				"device",
				"path",
				"osdevice",
				"systemroot",
				"testsigning",
				"bootlog",
			):
				if attr not in entry:
					continue
				val = entry[attr]
				if val is None:
					val = ""
				elif isinstance(val, bool):
					val = "yes" if val else "no"
				if attr in ("device", "osdevice"):
					str_repr = ""
					if isinstance(val, dict):
						if val["device_type"] == "boot":
							str_repr = "boot"
						elif val["device_type"] == "partition":
							disk_id = val["disk_id"]
							if isinstance(disk_id, int):
								disk_id = f"0x{disk_id:08x}"
							str_repr = f"{disk_id}:{val.get('partition_id', val.get('partition_offset', '?'))}"
						else:
							str_repr = f"Unsupported device type: {val.get('device_type_raw')}/{val.get('device_type')}"

						if val.get("ramdisk_path") and val.get("options_id"):
							# ramdisk=[<parent>]<path>,<optionsid>
							str_repr = f"ramdisk=[{str_repr}]\\{val['ramdisk_path']},{{{val['options_id']}}}"

					val = str_repr
				print(f"{attr}: {val}", file=file)
			print("", file=file)

	def get_boot_entries(self) -> list[dict]:
		entries = []
		default_boot_entry = self.get_default_boot_entry_guid()
		for node_id in self.get_application_object_node_ids():
			identifier = self.hive.node_name(node_id)
			entries.append(
				{
					"identifier": identifier,
					"friendly_name": BCD_OBJECTS.get(identifier[1:-1], {}).get("friendly_name"),
					"default": identifier == default_boot_entry,
				}
			)
			elements_id = self.hive.node_get_child(node_id, "Elements")
			for element in (
				BCDE_LIBRARY_TYPE_APPLICATION_DEVICE,
				BCDE_LIBRARY_TYPE_APPLICATION_PATH,
				BCDE_LIBRARY_TYPE_DESCRIPTION,
				BCDE_LIBRARY_TYPE_PREFERRED_LOCALE,
				BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES,
				BCDE_OSLOADER_TYPE_OS_DEVICE,
				BCDE_OSLOADER_TYPE_SYSTEM_ROOT,
				BCDE_OSLOADER_TYPE_LOG_INITIALIZATION,
				BCDE_OSLOADER_TYPE_KERNEL_DEBUGGER_ENABLED,
			):
				element_id = self.hive.node_get_child(elements_id, f"{element:x}")
				if element_id:
					value_id = self.hive.node_values(element_id)[0]
					value: str | dict | bool | bytes = self.get_value(value_id)
					if element in (
						BCDE_LIBRARY_TYPE_APPLICATION_DEVICE,
						BCDE_OSLOADER_TYPE_OS_DEVICE,
					):
						assert isinstance(value, bytes)
						value = self.decode_device_data(value)
					elif element in (BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES, BCDE_OSLOADER_TYPE_LOG_INITIALIZATION):
						value = value == b"\x01"
					entries[-1][OSLOADER_ELEMENTS.get(element, {}).get("friendly_name")] = value
		return entries

	def get_boot_entry_by_id(self, identifier: str) -> dict:
		for entry in self.get_boot_entries():
			if identifier == entry["identifier"]:
				return entry
		raise KeyError(f"Entry with identifier '{identifier}' not found")

	def update_boot_entry(
		self,
		entry: str | None = None,
		path: str | None = None,
		description: str | None = None,
		locale: str | None = None,
		system_root: str | None = None,
		testsigning: bool | None = None,
		bootlog: bool | None = None,
	) -> None:
		for node_id in self.get_application_object_node_ids(entry_filter=[entry] if entry else []):
			updates: dict[int, str | bytes] = {}
			if path is not None:
				updates[BCDE_LIBRARY_TYPE_APPLICATION_PATH] = path
			if description is not None:
				updates[BCDE_LIBRARY_TYPE_DESCRIPTION] = description
			if locale is not None:
				updates[BCDE_LIBRARY_TYPE_PREFERRED_LOCALE] = locale
			if system_root is not None:
				updates[BCDE_OSLOADER_TYPE_SYSTEM_ROOT] = system_root
			if testsigning is not None:
				updates[BCDE_LIBRARY_TYPE_ALLOW_PRERELEASE_SIGNATURES] = b"\x01" if testsigning else b"\x00"
			if bootlog is not None:
				updates[BCDE_OSLOADER_TYPE_LOG_INITIALIZATION] = b"\x01" if bootlog else b"\x00"
			elements_id = self.hive.node_get_child(node_id, "Elements")
			for element, value in updates.items():
				element_id = self.hive.node_get_child(elements_id, f"{element:x}")
				if not element_id:
					element_id = self.hive.node_add_child(elements_id, f"{element:x}")

				vtype = 3
				if isinstance(value, str):
					vtype = 1
					value = value.encode("utf-16-le")
				data = {"t": vtype, "key": "Element", "value": value}
				self.hive.node_set_value(element_id, data)

		self.hive.commit(self.filename)

	def delete_boot_entry(self, entry: str | None = None) -> None:
		for node_id in self.get_application_object_node_ids(entry_filter=[entry] if entry else []):
			self.hive.node_delete_child(node_id)
		self.hive.commit(self.filename)

	def update_device_info(
		self,
		device_type: int | str | None = None,
		disk_id: int | str | None = None,
		partition_offset: int | None = None,
		partition_id: str | None = None,
		ramdisk_path: str | None = None,
		options_id: str | None = None,
		entries: list[str] | None = None,
	) -> None:
		for node_id in self.get_application_object_node_ids(entry_filter=entries):
			elements_id = self.hive.node_get_child(node_id, "Elements")
			for element in (BCDE_LIBRARY_TYPE_APPLICATION_DEVICE, BCDE_OSLOADER_TYPE_OS_DEVICE):
				element_id = self.hive.node_get_child(elements_id, f"{element:x}")
				if element_id:
					value_id = self.hive.node_values(element_id)[0]
					raw_data = self.hive.value_value(value_id)[1]
					offset = BCD.get_device_info_offset(raw_data)
					if (options_id is not None or ramdisk_path is not None) and offset == 0:
						raw_data = (
							b"\x01\x01\x01\x01\x01\x01\x01\x01"
							b"\x01\x01\x01\x01\x01\x01\x01\x01"
							b"\x00\x00\x00\x00\x01\x00\x00\x00"
							b"\xa0\x00\x00\x00\x00\x00\x00\x00"
							b"\x03\x00\x00\x00\x00\x00\x00\x00"
							b"\x00\x00\x00\x00\x00\x00\x00\x00"
							b"\x00\x00\x00\x00\x00\x00\x00\x00"
							b"\x01\x00\x00\x00\x78\x00\x00\x00"
							b"\x05\x00\x00\x00" + raw_data[16:]
						)
						offset = 52
					if options_id is not None and offset != 0:
						raw_data = UUID(options_id.lstrip("{").rstrip("}")).bytes_le + raw_data[16:]
					if device_type is not None:
						if not isinstance(device_type, int):
							for number, name in DEVICE_TYPES.items():
								if name == device_type:
									device_type = number
						if device_type not in DEVICE_TYPES:
							raise ValueError(f"Invalid device type '{device_type}'")
						raw_data = raw_data[: offset + 16] + pack("B", device_type) + raw_data[offset + 17 :]
					if partition_id is not None:
						raw_data = raw_data[: offset + 32] + UUID(partition_id.lstrip("{").rstrip("}")).bytes_le + raw_data[offset + 48 :]
					elif partition_offset is not None:
						raw_data = raw_data[: offset + 32] + pack("<Q", partition_offset) + b"\x00" * 8 + raw_data[offset + 48 :]
					if disk_id is not None:
						disk_id_data = None
						disk_id_type = b"\x00"
						if isinstance(disk_id, int):
							# MBR
							disk_id_data = pack("<I", disk_id) + b"\x00" * 12
							disk_id_type = b"\x01"
						else:
							# GPT
							disk_id_data = UUID(disk_id.lstrip("{").rstrip("}")).bytes_le
							disk_id_type = b"\x00"
						raw_data = (
							raw_data[: offset + 52]
							+ disk_id_type
							+ raw_data[offset + 53 : offset + 56]
							+ disk_id_data
							+ raw_data[offset + 72 :]
						)
					if ramdisk_path is not None and offset != 0:
						raw_data = raw_data[: offset + 88] + ramdisk_path.encode("utf-16-le") + b"\x00\x00"
					# print(",".join([f"{v:02x}" for v in raw_data]))
					data = {"t": self.hive.value_type(value_id)[0], "key": self.hive.value_key(value_id), "value": raw_data}
					self.hive.node_set_value(element_id, data)
		self.hive.commit(self.filename)
