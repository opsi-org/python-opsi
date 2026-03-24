# opsi.system is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2021-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
efi tests
"""

import shutil
from os import statvfs_result
from pathlib import Path
from unittest.mock import patch

from opsi.system.efi import EFIBootManager, cleanup_efi_nvram, get_efi_nvram_stats


def test_get_boot_entries() -> None:
	EFIBootManager.efivars_path = Path("tests/data/efi/efivars")
	ebm = EFIBootManager()
	entries = ebm.get_boot_entries()

	assert len(entries) == 3

	assert entries[0].bootnum == 0
	assert entries[0].label == "Windows Boot Manager"
	assert entries[0].file_path_list[0].loader == r"\EFI\Microsoft\Boot\bootmgfw.efi"

	assert entries[1].bootnum == 1
	assert entries[1].label == "deepin"
	assert entries[1].file_path_list[0].loader == r"\EFI\deepin\shimx64.efi"

	assert entries[2].bootnum == 2
	assert entries[2].label == "ubuntu"
	assert entries[2].file_path_list[0].loader == r"\EFI\ubuntu\shimx64.efi"


def test_get_boot_order() -> None:
	EFIBootManager.efivars_path = Path("tests/data/efi/efivars")
	ebm = EFIBootManager()
	boot_order = ebm.get_boot_order()
	assert boot_order == [2, 1, 0]


def test_set_boot_order(tmp_path: Path) -> None:
	src = Path("tests/data/efi/efivars")
	dst = tmp_path / "efivars"
	shutil.copytree(src, dst)

	EFIBootManager.efivars_path = dst
	ebm = EFIBootManager()
	boot_order = ebm.get_boot_order()
	assert boot_order == [2, 1, 0]

	ebm.set_boot_order([1, 2, 0])
	boot_order = ebm.get_boot_order()
	assert boot_order == [1, 2, 0]

	ebm.set_boot_order(["Windows Boot Manager", 1, "ubuntu"])
	boot_order = ebm.get_boot_order()
	assert boot_order == [0, 1, 2]


def test_get_boot_current() -> None:
	EFIBootManager.efivars_path = Path("tests/data/efi/efivars")
	ebm = EFIBootManager()
	assert ebm.get_boot_current() == 2


def test_get_boot_next() -> None:
	EFIBootManager.efivars_path = Path("tests/data/efi/efivars")
	ebm = EFIBootManager()
	assert ebm.get_boot_next() == 1


def test_set_boot_next(tmp_path: Path) -> None:
	src = Path("tests/data/efi/efivars")
	dst = tmp_path / "efivars"
	shutil.copytree(src, dst)

	EFIBootManager.efivars_path = dst
	ebm = EFIBootManager()

	assert ebm.get_boot_next() == 1
	ebm.set_boot_next(2)
	assert ebm.get_boot_next() == 2

	ebm.unset_boot_next()
	assert ebm.get_boot_next() is None


def test_get_efi_nvram_stats() -> None:
	with patch("opsi.system.efi._efi.EFIVAR_FS", "tests/data/efi/efivars"), patch("opsi.system.efi._efi.statvfs") as mock_statvfs:
		# f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, f_files, f_ffree, f_favail, f_flag, f_namemax
		mock_statvfs.return_value = statvfs_result((1, 1, 251804, 156164, 151044, 0, 0, 0, 4110, 255))

		stats = get_efi_nvram_stats()
		assert stats.block_size == 1
		assert stats.blocks_total == 251804
		assert stats.blocks_used == 95640
		assert stats.blocks_free == 156164
		assert stats.blocks_available == 151044
		assert stats.size_total == 251804
		assert stats.size_used == 95640
		assert stats.size_free == 156164
		assert stats.size_available == 151044
		assert round(stats.usage, 4) == 0.3798


def test_cleanup_efi_nvram() -> None:
	unlinked = []

	def mock_unlink(self: Path) -> None:
		nonlocal unlinked
		unlinked.append(self)

	with patch("opsi.system.efi._efi.EFIVAR_FS", "tests/data/efi/efivars"), patch("opsi.system.efi._efi.Path.unlink", mock_unlink):
		cleanup_efi_nvram()

	assert len(unlinked) == 2
	for entry in unlinked:
		assert entry.name in ("dump-12345678-9abc-def0-1234-56789abcdef0", "dump-type0-12345678-9abc-def0-1234-56789abcdef0")
