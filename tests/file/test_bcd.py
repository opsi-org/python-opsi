# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
bcd tests
"""

import io
import platform
from pathlib import Path

import pytest

if platform.system() != "Linux":
	pytest.skip("BCD tests are currently only relevant on Linux", allow_module_level=True)

from opsi.file.bcd import BCD

DATA_PATH = Path("tests") / "data" / "bcd"


def test_fail_open() -> None:
	bcd_file = "/not/found"
	with pytest.raises(FileNotFoundError):
		BCD(filename=bcd_file)


def test_create_template(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	entries = bcd.get_boot_entries()
	assert len(entries) == 2
	assert "{3e8099ed-0999-11ec-9af5-2651b2ea4a87}" in [e["identifier"] for e in entries]
	assert "{9dea862c-5cdd-4e70-acc1-f32b344d4795}" in [e["identifier"] for e in entries]


def test_read_bcd_winpe() -> None:
	filename = DATA_PATH / "BCD.winpe"
	bcd = BCD(filename=filename)
	entries = bcd.get_boot_entries()
	assert len(entries) == 3

	entry = bcd.get_boot_entry_by_id("{7619dcc9-fafe-11d9-b411-000476eba25f}")
	assert entry["friendly_name"] is None
	assert entry["default"] is True
	assert entry["description"] == "Windows Setup"
	assert entry["locale"] == "en-US"
	assert entry["device"]["device_type"] == "boot"
	assert entry["device"]["device_type_raw"] == 5
	assert entry["device"]["options_id"] == "7619dcc8-fafe-11d9-b411-000476eba25f"
	assert entry["device"]["ramdisk_path"] == "\\sources\\boot.wim"

	entry = bcd.get_boot_entry_by_id("{9dea862c-5cdd-4e70-acc1-f32b344d4795}")
	assert entry["friendly_name"] == "{bootmgr}"
	assert entry["default"] is False
	assert entry["description"] == "Windows Boot Manager"
	assert entry["locale"] == "en-US"

	entry = bcd.get_boot_entry_by_id("{b2721d73-1db4-4c62-bf78-c548a880142d}")
	assert entry["friendly_name"] == "{memdiag}"
	assert entry["default"] is False
	assert entry["description"] == "Windows Memory Diagnostic"
	assert entry["locale"] == "en-US"
	assert entry["device"]["device_type"] == "boot"
	assert entry["device"]["ramdisk_path"] == ""
	assert entry["path"] == "\\boot\\memtest.exe"


def test_get_node_by_path(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	node_id = bcd.get_node_by_path(r"\\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\23000006")
	assert bcd.hive.node_name(node_id) == "23000006"
	node_id = bcd.get_node_by_path(r"\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\23000006")
	assert bcd.hive.node_name(node_id) == "23000006"
	node_id = bcd.get_node_by_path(None)
	assert bcd.hive.node_name(node_id) == "NewStoreRoot"
	with pytest.raises(ValueError):
		bcd.get_node_by_path(r"\notfound")


def test_print_tree(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	bcd.print_tree()
	file = io.StringIO()
	bcd.print_tree(path=r"\\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\12000004", file=file)
	file.seek(0)
	assert file.read().strip() == (
		r"[\\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\12000004]" "\n" '"Element"="Windows Boot Manager"'
	)
	file = io.StringIO()
	bcd.print_tree(path=r"\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\12000004", file=file)
	file.seek(0)
	assert file.read().strip() == (
		r"[\\Objects\{9dea862c-5cdd-4e70-acc1-f32b344d4795}\Elements\12000004]" "\n" '"Element"="Windows Boot Manager"'
	)


def test_print_boot_entries(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	bcd.print_boot_entries()
	file = io.StringIO()
	bcd.print_boot_entries(file=file)
	file.seek(0)
	expected = (
		"{3e8099ed-0999-11ec-9af5-2651b2ea4a87}\n"
		"friendly_name: \n"
		"default: yes\n"
		"description: Windows\n"
		"locale: en-US\n"
		"device: 0x00000000:0\n"
		"path: \\windows\\system32\\winload.exe\n"
		"osdevice: 0x00000000:0\n"
		"systemroot: \\windows\n"
		"\n"
		"{9dea862c-5cdd-4e70-acc1-f32b344d4795}\n"
		"friendly_name: {bootmgr}\n"
		"default: no\n"
		"description: Windows Boot Manager\n"
		"locale: de-DE\n"
		"device: 0x00000000:0\n"
		"\n"
	)
	out = file.read()
	assert out == expected


def test_format_value_fallback_without_key() -> None:
	bcd = BCD.__new__(BCD)

	class MockHive:
		@staticmethod
		def value_key(value_id: int) -> str:
			assert value_id == 1
			return "Element"

		@staticmethod
		def value_type(value_id: int) -> tuple[int, int]:
			assert value_id == 1
			return (9, 0)

	bcd.hive = MockHive()
	bcd.get_value = lambda value_id: b"abc"

	assert bcd.format_value(1) == '"Element"={vtype}:{value}'
	assert bcd.format_value(1, with_key=False) == "{vtype}:{value}"


def test_print_boot_entries_formats_boot_and_ramdisk_and_unsupported() -> None:
	bcd = BCD.__new__(BCD)
	bcd.get_boot_entries = lambda: [
		{
			"identifier": "{boot-entry}",
			"device": {
				"device_type": "boot",
				"device_type_raw": 5,
				"ramdisk_path": "sources\\boot.wim",
				"options_id": "7619dcc8-fafe-11d9-b411-000476eba25f",
			},
			"osdevice": {
				"device_type": "mystery",
				"device_type_raw": 99,
			},
		}
	]

	file = io.StringIO()
	bcd.print_boot_entries(file=file)

	assert file.getvalue() == (
		"{boot-entry}\n"
		"device: ramdisk=[boot]\\sources\\boot.wim,{7619dcc8-fafe-11d9-b411-000476eba25f}\n"
		"osdevice: Unsupported device type: 99/mystery\n"
		"\n"
	)


def test_get_boot_entry_by_id_not_found(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)

	with pytest.raises(KeyError, match="Entry with identifier 'missing' not found"):
		bcd.get_boot_entry_by_id("missing")


def test_update_device_info(tmp_path: Path) -> None:  # pylint: disable=too-many-branches
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	bcd.update_device_info(device_type="partition", disk_id=0x1BEEBEE1, partition_offset=2048)
	entries = bcd.get_boot_entries()
	for entry in entries:
		for key in ("device", "osdevice"):
			if key == "osdevice" and entry.get("friendly_name") == "{bootmgr}":
				continue
			assert entry[key]["device_type"] == "partition"
			assert entry[key]["device_type_raw"] == 6
			assert entry[key]["disk_id"] == 0x1BEEBEE1
			assert entry[key]["partition_offset"] == 2048

	bcd.update_device_info(device_type="partition", disk_id=0x2BEEBEE2, partition_offset=1024, entries=["{default}"])
	entries = bcd.get_boot_entries()
	for entry in entries:
		for key in ("device", "osdevice"):
			if key == "osdevice" and entry.get("friendly_name") == "{bootmgr}":
				continue
			assert entry[key]["device_type"] == "partition"
			assert entry[key]["device_type_raw"] == 6
			if entry.get("default"):
				assert entry[key]["disk_id"] == 0x2BEEBEE2
				assert entry[key]["partition_offset"] == 1024
			else:
				assert entry[key]["disk_id"] == 0x1BEEBEE1
				assert entry[key]["partition_offset"] == 2048

	bcd.update_device_info(
		device_type="partition",
		disk_id="5cfa8fcb-3382-48b8-b6cf-5ff512785d5f",
		partition_id="b924e51c-0f1b-4f16-8832-42e1bb8bb2ef",
		entries=["{default}", "{bootmgr}"],
	)
	entries = bcd.get_boot_entries()
	for entry in entries:
		for key in ("device", "osdevice"):
			if key == "osdevice" and entry.get("friendly_name") == "{bootmgr}":
				continue
			assert entry[key]["device_type"] == "partition"
			assert entry[key]["device_type_raw"] == 6
			assert entry[key]["disk_id"] == "5cfa8fcb-3382-48b8-b6cf-5ff512785d5f"
			assert entry[key]["partition_id"] == "b924e51c-0f1b-4f16-8832-42e1bb8bb2ef"

	bcd.update_device_info(
		device_type="partition",
		disk_id="5cfa8fcb-3382-48b8-b6cf-5ff512785d5f",
		partition_id="b924e51c-0f1b-4f16-8832-42e1bb8bb2ef",
		ramdisk_path="testimage.wim",
		options_id="e2fbc9fc-bb91-4a0b-9028-1abf46ffb981",
	)
	entries = bcd.get_boot_entries()
	for entry in entries:
		for key in ("device", "osdevice"):
			if key == "osdevice" and entry.get("friendly_name") == "{bootmgr}":
				continue
			assert entry[key]["device_type"] == "partition"
			assert entry[key]["device_type_raw"] == 6
			assert entry[key]["disk_id"] == "5cfa8fcb-3382-48b8-b6cf-5ff512785d5f"
			assert entry[key]["partition_id"] == "b924e51c-0f1b-4f16-8832-42e1bb8bb2ef"
			assert entry[key]["ramdisk_path"] == "testimage.wim"
			assert entry[key]["options_id"] == "e2fbc9fc-bb91-4a0b-9028-1abf46ffb981"


def test_update_boot_entry(tmp_path: Path) -> None:
	bcd_winpe = DATA_PATH / "BCD.winpe"
	bcd_file = tmp_path / "BCD"
	with open(bcd_winpe, "rb") as inf:
		with open(bcd_file, "wb") as outf:
			outf.write(inf.read())
	bcd = BCD(filename=bcd_file)
	bcd.update_boot_entry(entry="{default}", path=r"\Test\load.exe", description="opsi install", locale="en-US", system_root=r"\Windows")
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["path"] == r"\Test\load.exe"
	assert entry["description"] == "opsi install"
	assert entry["locale"] == "en-US"
	assert entry["systemroot"] == r"\Windows"


def test_update_boot_entry_adds_missing_element(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert "testsigning" not in entry

	bcd.update_boot_entry(default, testsigning=True)

	entry = bcd.get_boot_entry_by_id(default)
	assert entry["testsigning"] is True


def test_delete_boot_entry(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)
	default = bcd.get_default_boot_entry_guid()

	bcd.delete_boot_entry(default)

	entries = bcd.get_boot_entries()
	assert len(entries) == 1
	assert default not in [entry["identifier"] for entry in entries]
	with pytest.raises(KeyError, match=default):
		bcd.get_boot_entry_by_id(default)


def test_boot_entry_testsigning(tmp_path: Path) -> None:
	bcd_winpe = DATA_PATH / "BCD.options"
	bcd_file = tmp_path / "BCD"
	with open(bcd_winpe, "rb") as inf:
		with open(bcd_file, "wb") as outf:
			outf.write(inf.read())
	bcd = BCD(filename=bcd_file)
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["testsigning"] is True

	bcd.update_boot_entry(default, testsigning=False)
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["testsigning"] is False

	bcd.update_boot_entry(default, testsigning=True)
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["testsigning"] is True


def test_boot_entry_bootlog(tmp_path: Path) -> None:
	bcd_winpe = DATA_PATH / "BCD.options"
	bcd_file = tmp_path / "BCD"
	with open(bcd_winpe, "rb") as inf:
		with open(bcd_file, "wb") as outf:
			outf.write(inf.read())
	bcd = BCD(filename=bcd_file)
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["bootlog"] is True

	bcd.update_boot_entry(default, bootlog=False)
	default = bcd.get_default_boot_entry_guid()
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["bootlog"] is False

	bcd.update_boot_entry(default, bootlog=True)
	entry = bcd.get_boot_entry_by_id(default)
	assert entry["bootlog"] is True


def test_update_device_info_invalid_device_type(tmp_path: Path) -> None:
	bcd_file = tmp_path / "BCD"
	bcd = BCD(filename=bcd_file, create_from_template=True)

	with pytest.raises(ValueError, match="Invalid device type 'unsupported'"):
		bcd.update_device_info(device_type="unsupported")
