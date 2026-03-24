# opsi.system is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2021-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
This file is part of opsi - https://www.opsi.org
"""

import re
import uuid
from dataclasses import dataclass
from enum import Enum
from os import statvfs
from pathlib import Path
from struct import pack, unpack
from typing import Dict, Generator, List, Tuple, Type

from opsi.logging import get_logger

BOOT_VAR_RE = re.compile(
	r"^Boot(?P<bootnum>[0-9a-f]{4})-(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", flags=re.IGNORECASE
)
BOOT_ORDER_VAR_RE = re.compile(r"^BootOrder-(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", flags=re.IGNORECASE)
BOOT_CURRENT_VAR_RE = re.compile(
	r"^BootCurrent-(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", flags=re.IGNORECASE
)
BOOT_NEXT_VAR_RE = re.compile(r"^BootNext-(?P<guid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", flags=re.IGNORECASE)
EFIVAR_FS = "/sys/firmware/efi/efivars"

logger = get_logger("opsi.system.efi")

# See EFI_LOAD_OPTION in https://dox.ipxe.org/UefiSpec_8h_source.html
# 9. Protocols — Device Path Protocol
# 9.3.7 BIOS Boot Specification Device Path
# https://superuser.com/questions/1613541/whats-the-meaning-of-the-bytes-between-filepathlistlength-and-description-i
# struct {
#     uint32_t Attributes = 0x00000007, /* NON_VOLATILE | BOOTSERVICE_ACCESS | RUNTIME_ACCESS */
#     Data[] = (struct efi_load_option) {
#         uint32_t attributes = 0x00000001, /* ACTIVE */
#         uint16_t file_path_list_length = 0x000d, /* 13 */
#         char16_t description[] = L"UEFI:Removable Device",
#         file_path_list[] = {
#             {
#                 uint8_t type = 0x05, /* BIOSBootDevice - table 44 */
#                 uint8_t subtype = 0x01, /* BiosBootDevice */
#                 uint16_t length = 0x0009, /* 4 (header) + 5 (data) */
#                 /* table 101 */
#                 uint16_t device_type = 0x0082, /* unknown reserved value */
#                 uint16_t status_flag = 0x0000,
#                 char description_string[] = "",
#             },
#             {
#                 uint8_t type = 0x7f, /* EndOfDevicePath - table 44 */
#                 uint8_t subtype = 0xff, /* EndEntireDevicePath - table 45 */
#                 uint16_t length = 0x0004, /* 4 (header) + 0 (data) */
#                 /* no data */
#             },
#         },
#         uint8_t optional_data[] = {},
#     }
# }


def cleanup_efi_nvram() -> None:
	# The dump-* files are special UEFI variables created by the firmware to record crash dumps or error logs.
	# They usually come from the UEFI Crash Dump or Error Record Persistence mechanisms,
	# used when the firmware or OS experiences a fatal event.

	efivars_path = Path(EFIVAR_FS)
	if not efivars_path.is_dir():
		raise RuntimeError(f"EFI variables filesystem not found at {efivars_path}")

	efivars = efivars_path.glob("dump-*")
	for efivar in efivars:
		logger.info("Removing EFI variable: %s", efivar)
		efivar.unlink()


@dataclass
class EFINVRAMStats:
	block_size: int
	blocks_total: int
	blocks_free: int
	blocks_available: int

	@property
	def blocks_used(self) -> int:
		return self.blocks_total - self.blocks_free

	@property
	def size_total(self) -> int:
		return self.blocks_total * self.block_size

	@property
	def size_free(self) -> int:
		return self.blocks_free * self.block_size

	@property
	def size_available(self) -> int:
		return self.blocks_available * self.block_size

	@property
	def size_used(self) -> int:
		return self.blocks_used * self.block_size

	@property
	def usage(self) -> float:
		return self.blocks_used / self.blocks_total if self.blocks_total > 0 else 0


def get_efi_nvram_stats() -> EFINVRAMStats:
	# From the kernel source (fs/efivars/super.c)
	#   This is not a normal filesystem, so no point in pretending it has a block
	#   size; we declare f_bsize to 1, so that we can then report the exact value
	#   sent by EFI QueryVariableInfo in f_blocks and f_bfree
	#   In f_bavail we declare the free space that the kernel will allow writing
	#   when the storage_paranoia x86 quirk is active. To use more, users
	#   should boot the kernel with efi_no_storage_paranoia.
	#
	# Without the efi_no_storage_paranoia kernel parameter the kernel keeps a reserved free space.
	# On Linux 6.14.0 EFI_MIN_RESERVE is 5120 bytes.
	efivars_path = Path(EFIVAR_FS)
	if not efivars_path.is_dir():
		raise RuntimeError(f"EFI variables filesystem not found at {efivars_path}")
	stats = statvfs(efivars_path)
	return EFINVRAMStats(
		block_size=stats.f_bsize,
		blocks_total=stats.f_blocks,
		blocks_free=stats.f_bfree,
		blocks_available=stats.f_bavail,
	)


class EFIVariableAttribute(Enum):
	NON_VOLATILE = 0x1
	BOOTSERVICE_ACCESS = 0x2
	RUNTIME_ACCESS = 0x4
	HARDWARE_ERROR_RECORD = 0x8
	AUTHENTICATED_WRITE_ACCESS = 0x10
	TIME_BASED_AUTHENTICATED_WRITE_ACCESS = 0x20
	APPEND_WRITE = 0x40


class DevicePathType(Enum):
	HARDWARE_DEVICE_PATH = 0x1
	ACPI_DEVICE_PATH = 0x2
	MESSAGING_DEVICE_PATH = 0x3
	MEDIA_DEVICE_PATH = 0x4
	BIOS_BOOT_SPECIFICATION_DEVICE_PATH = 0x5
	END_OF_HARDWARE_DEVICE_PATH = 0x7F


@dataclass
class EFIFilePath:
	type: int
	sub_type: int
	device_type: int | None = None
	status_flag: int | None = None
	loader: str | None = None
	part_id: str | None = None


@dataclass
class EFIBootEntry:
	guid: str
	label: str
	bootnum: int
	attributes: int
	file_path_list: List[EFIFilePath]
	optional_data: bytes | None = None

	@classmethod
	def _read_description(cls: Type["EFIBootEntry"], data: bytes, offset: int = 0) -> Tuple[bytes, int]:
		description_bytes = b""
		view = memoryview(data)
		while True:
			dat = view[offset : offset + 2]
			offset += 2
			if not dat or dat == b"\x00\x00":
				break
			description_bytes += dat
		return description_bytes, offset

	@classmethod
	def _read_file_path(cls: Type["EFIBootEntry"], data: bytes, offset: int = 0) -> Tuple[EFIFilePath, int]:
		file_path = EFIFilePath(type=unpack("<B", data[offset : offset + 1])[0], sub_type=unpack("<B", data[offset + 1 : offset + 2])[0])
		length = unpack("<H", data[offset + 2 : offset + 4])[0]
		offset += 4
		if length > 4:
			file_path.device_type = unpack("<H", data[offset : offset + 2])[0]
			file_path.status_flag = unpack("<H", data[offset + 2 : offset + 4])[0]
			offset += 4
			_tdata = data[offset : offset + length - 4]
			offset += length - 4
			description, offset = cls._read_description(data, offset)
			if file_path.type == 4 and file_path.sub_type == 1 and file_path.device_type == 1:
				file_path.loader = description.decode("utf-16")
				file_path.part_id = str(uuid.UUID(bytes_le=_tdata[16:32]))
		return file_path, offset

	@classmethod
	def from_file(cls: Type["EFIBootEntry"], file: Path) -> "EFIBootEntry":
		match = BOOT_VAR_RE.match(file.name)
		if not match:
			raise ValueError("Invalid filename: {file!r}")

		bootnum = int(match.group("bootnum"), 16)
		guid = match.group("guid")
		data = file.read_bytes()
		_efi_var_attributes = unpack("<I", data[0:4])[0]
		attributes = unpack("<I", data[4:8])[0]
		file_path_list_length = unpack("<H", data[8:10])[0]
		offset = 10
		label_bytes, offset = cls._read_description(data, offset)
		label = label_bytes.decode("utf-16")
		optional_data = data[offset + file_path_list_length :]

		file_path_list_data = data[offset : offset + file_path_list_length]
		offset = 0
		file_path_list = []
		while offset < file_path_list_length:
			file_path, offset = cls._read_file_path(file_path_list_data, offset)
			file_path_list.append(file_path)

		return EFIBootEntry(
			guid=guid,
			label=label,
			bootnum=bootnum,
			attributes=attributes,
			file_path_list=file_path_list,
			optional_data=optional_data,
		)

	def __repr__(self) -> str:
		return f"<EFIBootEntry bootnum={self.bootnum} label='{self.label}'>"


class EFIBootManager:
	efivars_path = Path(EFIVAR_FS)

	def __init__(self) -> None:
		if not self.efivars_path.is_dir():
			raise RuntimeError(f"EFI variables filesystem not found at {self.efivars_path}")

		self.guid = None
		match = None
		try:
			file = next(self._get_var_files(BOOT_CURRENT_VAR_RE))
			match = BOOT_CURRENT_VAR_RE.match(file.name)
		except StopIteration:
			try:
				file = next(self._get_var_files(BOOT_ORDER_VAR_RE))
				match = BOOT_ORDER_VAR_RE.match(file.name)
			except StopIteration as err:
				raise RuntimeError("Failed to get BootCurrent and BootOrder var") from err

		if not match:
			raise RuntimeError("Failed to get guid")

		self.guid = match.group("guid")

	def _get_var_files(self, pattern: re.Pattern) -> Generator[Path, None, None]:
		for file in self.efivars_path.iterdir():
			if not file.is_file():
				continue
			match = pattern.match(file.name)
			if not match:
				continue
			if self.guid and match.group("guid") != self.guid:
				continue
			yield file

	def get_boot_entries(self) -> List[EFIBootEntry]:
		entries = [EFIBootEntry.from_file(file) for file in self._get_var_files(BOOT_VAR_RE)]
		# boot_order = self.get_boot_order()
		# return sorted(entries, key=lambda e: boot_order.index(e.bootnum))
		return sorted(entries, key=lambda e: e.bootnum)

	def get_boot_order(self) -> List[int]:
		boot_order = []
		for file in self._get_var_files(BOOT_ORDER_VAR_RE):
			data = file.read_bytes()
			_efi_var_attributes = unpack("<I", data[0:4])[0]
			for offset in range(4, len(data), 2):
				bootnum = unpack("<H", data[offset : offset + 2])[0]
				boot_order.append(bootnum)
			break
		return boot_order

	def set_boot_order(self, boot_order: List[int | str]) -> None:
		bootnum_by_label: Dict[str, int] = {}
		for file in self._get_var_files(BOOT_ORDER_VAR_RE):
			data = file.read_bytes()[0:4]
			for bootnum in boot_order:
				if isinstance(bootnum, str):
					if not bootnum_by_label:
						bootnum_by_label = {entry.label: entry.bootnum for entry in self.get_boot_entries()}
					bootnum = bootnum_by_label[bootnum]
				data += pack("<H", bootnum)
			file.write_bytes(data)
			break

	def get_boot_current(self) -> int | None:
		try:
			file = next(self._get_var_files(BOOT_CURRENT_VAR_RE))
		except StopIteration as err:
			raise RuntimeError("Failed to get BootCurrent var") from err
		data = file.read_bytes()
		return unpack("<H", data[4:6])[0]

	def get_boot_next(self) -> int | None:
		try:
			file = next(self._get_var_files(BOOT_NEXT_VAR_RE))
		except StopIteration:
			# File not found
			return None
		data = file.read_bytes()
		return unpack("<H", data[4:6])[0]

	def set_boot_next(self, bootnum: int | None) -> None:
		if bootnum is None:
			self.unset_boot_next()
		else:
			file = self.efivars_path / f"BootNext-{self.guid}"
			file.write_bytes(pack("<I", 7) + pack("<H", bootnum))

	def unset_boot_next(self) -> None:
		try:
			file = next(self._get_var_files(BOOT_NEXT_VAR_RE))
			file.unlink()
		except StopIteration:
			pass
