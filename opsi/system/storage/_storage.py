# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import struct
from pathlib import Path, PureWindowsPath
from random import randrange
from subprocess import run
from typing import Generic, Literal, TypeVar, overload
from uuid import UUID, uuid4

from opsi.logging import get_logger

logger = get_logger("opsi.system.storage")


PARTITION_TYPE_ALIASES = {
	"linux": {"MBR": "83", "GPT": "0fc63daf-8483-4772-8e79-3d69d8477de4"},
	"swap": {"MBR": "82", "GPT": "0657fd6d-a4ab-43c4-84e5-0933c84b4f4f"},
	"raid": {"MBR": "fd", "GPT": "a19d880f-05fc-4d3b-a006-743f0f84911e"},
	"lvm": {"MBR": "8e", "GPT": "e6d6d379-f507-44c2-a23c-238f2a3df928"},
	"uefi": {"MBR": "ef", "GPT": "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"},
	"ms_reserved": {"MBR": "07", "GPT": "e3c9e316-0b5c-4db8-817d-f92df00215ae"},
	"ms_basic_data": {"MBR": "07", "GPT": "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"},
	"ms_recovery": {"MBR": "07", "GPT": "de94bba4-06d1-4d40-a16a-bfd50179d6ac"},
}
# ioctl constants from linux/fs.h
BLKSSZGET = 0x1268


def _run_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
	logger.info("Running command %r with input %r", command, input)
	env = os.environ.copy()
	lp_orig = env.get("LD_LIBRARY_PATH_ORIG")
	if lp_orig is not None:
		env["LD_LIBRARY_PATH"] = lp_orig
	else:
		env.pop("LD_LIBRARY_PATH", None)
	env["LC_ALL"] = "C"

	proc = run(command, shell=False, env=env, input=input.encode("utf-8") if input else None, capture_output=True, check=False)
	out = proc.stderr.decode("utf-8") + proc.stdout.decode("utf-8")
	logger.debug("Command returncode=%r, output=%r", proc.returncode, out)

	if proc.returncode not in (valid_returncodes or [0]):
		raise RuntimeError(f"Command {command} failed: returncode={proc.returncode} output={out}")

	return out


def _get_block_devices() -> list[dict]:
	out = _run_command(["lsblk", "--json", "--paths", "--bytes", "--output-all"])
	data = json.loads(out)
	return data.get("blockdevices", [])


def get_disks() -> list[StorageDevice]:
	return [StorageDevice(path=dev["name"]) for dev in _get_block_devices() if dev.get("type") == "disk"]


class StorageDevice:
	"""A disk or partition"""

	def __init__(self, path: str | Path) -> None:
		self.path = path if isinstance(path, Path) else Path(path)
		self.size = 0
		self.model = None
		self.serial = None
		self.partition_table: PartitionTable | None = None
		self.windows_drive: PureWindowsPath | None = None
		self.mount_point: Path | None = None
		try:
			self._get_info()
		except RuntimeError:
			pass

	def __str__(self) -> str:
		return f"{self.__class__.__name__}(path={self.dev}, size={self.size}, model='{self.model}', serial='{self.serial}')"

	__repr__ = __str__

	@property
	def dev(self) -> str:
		return str(self.path)

	def _get_info(self) -> None:
		if self.path.is_file():
			self.size = self.path.stat().st_size
		else:
			for dev in _get_block_devices():
				if dev["name"] == self.dev:
					self.size = dev.get("size", self.size)
					self.model = dev.get("model", self.model)
					self.serial = dev.get("serial", self.serial)
		try:
			self.read_partition_table()
		except RuntimeError:
			pass

	def set_windows_drive(self, windows_drive: str) -> None:
		self.windows_drive = PureWindowsPath(f"{windows_drive[0].lower()}:/")

	def set_mount_point(self, mount_point: Path | str) -> None:
		self.mount_point = Path(mount_point) if not isinstance(mount_point, Path) else mount_point

	def mount(self, mount_point: Path | str | None = None) -> None:
		if mount_point:
			self.set_mount_point(mount_point)
		if not self.mount_point:
			raise RuntimeError("mount_point not defined")
		logger.info("Mounting device %r to '%s'", self.dev, self.mount_point)
		self.mount_point.mkdir(parents=True, exist_ok=True)
		_run_command(["mount", self.dev, str(self.mount_point)])

	def umount(self) -> None:
		if not self.mount_point:
			raise RuntimeError("Not mounted")
		logger.info("Umounting '%s'", self.mount_point)
		_run_command(["umount", str(self.mount_point)])

	def abs_path(self, path: Path | str | None) -> Path:
		if not self.mount_point:
			raise ValueError("mount_point not set")
		if not path:
			return self.mount_point
		path = Path(path) if not isinstance(path, Path) else path
		return self.mount_point / (path.relative_to("/") if path.is_absolute() else path)

	def win_path(self, path: Path | str | None) -> PureWindowsPath:
		if not self.windows_drive:
			raise ValueError("windows_drive not set")
		if not self.mount_point:
			raise ValueError("mount_point not set")
		if not path:
			return self.windows_drive
		path = Path(path) if not isinstance(path, Path) else path
		try:
			path = path.relative_to(self.mount_point)
		except ValueError:
			pass
		return self.windows_drive / PureWindowsPath(path)

	def wipe_metadata(self) -> None:
		"""Wipe meta-data like file system info, LVM, etc"""
		with open(self.path, "rb+") as dev:
			dev.write(bytearray(1024))

	@overload
	def create_partition_table(self, type: Literal["GPT"], id: str | UUID | None = None) -> GPTPartitionTable: ...

	@overload
	def create_partition_table(self, type: Literal["MBR"], id: str | int | None = None) -> MBRPartitionTable: ...

	def create_partition_table(
		self, type: Literal["GPT", "MBR"] = "GPT", id: str | int | UUID | None = None
	) -> GPTPartitionTable | MBRPartitionTable:
		if type not in ("GPT", "MBR"):
			raise ValueError(f"Invalid partition table type {type}, valid types are GPT and MBR")
		self.partition_table = MBRPartitionTable(self, id) if type == "MBR" else GPTPartitionTable(self, id)  # type: ignore[arg-type]
		self.partition_table.create()
		self.partition_table.read()
		return self.partition_table

	def read_partition_table(self) -> PartitionTable:
		self.partition_table = PartitionTable.from_device(self)
		return self.partition_table

	def create_filesystem(self, type: str, label: str | None = None) -> None:
		type = type.lower()
		args = []
		if type in ("fat32", "vfat"):
			type = "vfat"
			args += ["-F", "32"]
		elif type == "ntfs":
			args += ["--fast", "--force"]

		if label:
			if type == "vfat":
				args += ["-n"]
			else:
				args += ["-L"]
			args += [label]

		_run_command([f"mkfs.{type}"] + args + [self.dev])


TPartition = TypeVar("TPartition", bound="Partition")


class Partition(StorageDevice):
	unit_to_exp = {"K": 1, "M": 2, "G": 3, "T": 4, "P": 5, "E": 6, "Z": 7, "Y": 8}

	def __init__(
		self,
		partition_table: PartitionTable,
		number: int,
		*,
		type: str,
		start: str | int | None = None,
		size: str | int | None = None,
		path: Path | str | None = None,
	) -> None:
		if path:
			super().__init__(path)
		self.partition_table: PartitionTable = partition_table
		self.number = number
		self.type = type.lower()
		self.input_start, self.start = self._process_offset(start)
		self.input_size, self.size = self._process_offset(size)

	def _process_offset(self, value: str | int | None) -> tuple[str | int, int]:
		# sfdisk takes sectors or values of KiB, MiB, GiB, TiB, PiB, EiB, ZiB and YiB
		# "-" or empty value can be use to set start value automatically
		if value is None:
			return "-", 0

		sector_size = self.partition_table.sector_size

		if isinstance(value, int):
			# Sectors
			return value, value * sector_size

		match = re.search(r"^(\d+)(\D+)$", value)
		if not match:
			raise ValueError(f"Invalid value {value!r}")

		unit = match.group(2).upper()
		value = int(match.group(1))
		exp = 0

		if unit == "%":
			if value < 0 or value > 100:
				raise ValueError(f"Invalid percentage value {value!r}")
			size = self.partition_table.device.size
			if not size:
				raise ValueError("Percentage value is not supported because size of device is unknown")
			value = round(size * value / 100)
		else:
			exp = self.unit_to_exp.get(unit[0], 0)
			if not exp:
				raise ValueError(f"Invalid unit {match.group(2)!r}")
			if "I" in unit:
				return f"{value}{unit[0]}iB", value * 1024**exp

		# Use MiB as unit to make sfdisk align correctly
		val = int(value * (1000**exp / 1024**2)) or 1
		return f"{val}MiB", val * 1024**2

	def __str__(self) -> str:
		return f"{self.__class__.__name__}(number={self.number}, start={self.start}, size={self.size})"

	__repr__ = __str__

	def sfdisk_command(self) -> str:
		return ""


class MBRPartition(Partition):
	def __init__(
		self,
		partition_table: MBRPartitionTable,
		number: int,
		*,
		type: str,
		start: str | int | None = None,
		size: str | int | None = None,
		path: Path | str | None = None,
		bootable: bool = False,
	) -> None:
		if number < 1 or number > 64:
			raise ValueError(f"Invalid partition number: {number}")
		if number > 4:
			logger.warning("Logical MBR partitions not spported")
		if not re.match(r"^[0-9a-fA-F]{1,2}", type):
			alias = PARTITION_TYPE_ALIASES.get(type)
			if not alias:
				raise ValueError(f"Invalid type {type!r}")
			type = alias["MBR"]
		super().__init__(partition_table=partition_table, number=number, type=type, start=start, size=size, path=path)
		self.bootable = bootable

	def sfdisk_command(self) -> str:
		# "-" is only valid for newer sfdisk versions
		start = f",start={self.input_start}" if self.input_start and self.input_start != "-" else ""
		size = f",size={self.input_size}" if self.input_size and self.input_size != "-" else ""
		return f"type={self.type}{start}{size}{',bootable' if self.bootable else ''}\n"

	def write_boot_record(self, type: str | None = None) -> None:
		arg = "-w"
		if type:
			arg = f"--{type.lower()}"
		out = _run_command(["ms-sys", "-f", arg, self.dev]).lower()
		if "unable to automaticly select boot record" in out:
			if "ntfs file system" in out:
				out = _run_command(["ms-sys", "-f", "--ntfs", self.dev]).lower()
			elif "fat32 file system" in out:
				out = _run_command(["ms-sys", "-f", "--fat32", self.dev]).lower()
		if "unable" in out or "usage:" in out:
			raise RuntimeError(f"Failed to write boot record: {out}")


class GPTPartition(Partition):
	def __init__(
		self,
		partition_table: GPTPartitionTable,
		number: int,
		*,
		type: str,
		start: str | int | None = None,
		size: str | int | None = None,
		path: Path | str | None = None,
		name: str | None = None,
		uuid: str | UUID | None = None,
		attrs: str | None = None,
	) -> None:
		if number < 1 or number > 128:
			raise ValueError(f"Invalid partition number: {number}")
		if attrs:
			logger.warning("GPT attributes not implemented, got: %s", attrs)
		type = self._set_type(type)
		super().__init__(partition_table=partition_table, number=number, type=type, start=start, size=size, path=path)
		self.name: str | None = None
		self._set_name(name)
		self.uuid = ""
		self._set_uuid(uuid)

	def _set_uuid(self, uuid: str | UUID | None) -> None:
		if not uuid:
			uuid = uuid4()
		self.uuid = str(uuid if isinstance(uuid, UUID) else UUID(uuid))

	def set_uuid(self, uuid: str | UUID) -> None:
		self._set_uuid(uuid)
		logger.info("Setting %r uuid to %r", self, self.uuid)
		_run_command(["sfdisk", "--part-uuid", self.partition_table.device.dev, str(self.number), self.uuid])

	def _set_type(self, type: str | UUID | None) -> str:
		if not type:
			self.type = "00000000-0000-0000-0000-000000000000"
			return self.type

		if isinstance(type, UUID):
			self.type = str(type)
			return self.type

		alias = PARTITION_TYPE_ALIASES.get(type)
		if alias:
			self.type = alias["GPT"]
			return self.type

		try:
			self.type = str(UUID(type))
		except ValueError as err:
			raise ValueError(f"Invalid type {type!r}") from err

		return self.type

	def set_type(self, type: str | UUID | None) -> None:
		self._set_type(type)
		logger.info("Setting %r type to %r", self, self.type)
		_run_command(["sfdisk", "--part-type", self.partition_table.device.dev, str(self.number), self.type])

	def _set_name(self, name: str | None) -> None:
		self.name = name

	def set_name(self, name: str) -> None:
		self._set_name(name)
		logger.info("Setting %r name to %r", self, self.name)
		_run_command(["sfdisk", "--part-label", self.partition_table.device.dev, str(self.number), self.name or ""])

	def sfdisk_command(self) -> str:
		name = f',name="{self.name}"' if self.name is not None else ""
		start = f",start={self.input_start}" if self.input_start and self.input_start != "-" else ""
		size = f",size={self.input_size}" if self.input_size and self.input_size != "-" else ""
		return f"type={self.type},uuid={self.uuid}{name}{start}{size}\n"


class PartitionTable(Generic[TPartition]):
	label = ""
	partition_type = Partition

	def __init__(self, device: StorageDevice, id: str | int) -> None:
		self.device = device
		self._set_id(id)
		self.sector_size = 512
		self._partitions: dict[int, TPartition] = {}

	def __str__(self) -> str:
		return f"{self.__class__.__name__}(partitions={len(self._partitions)})"

	__repr__ = __str__

	@classmethod
	def _read_data(cls, device: StorageDevice) -> dict:
		return json.loads(_run_command(["sfdisk", "-J", device.dev]))

	@classmethod
	def from_device(cls, device: StorageDevice) -> MBRPartitionTable | GPTPartitionTable:
		data = cls._read_data(device)
		label = data["partitiontable"]["label"]
		partition_table: GPTPartitionTable | MBRPartitionTable
		if label == GPTPartitionTable.label:
			partition_table = GPTPartitionTable(device)
		elif label == MBRPartitionTable.label:
			partition_table = MBRPartitionTable(device)
		else:
			raise NotImplementedError(f"Partition type {label} not supported")
		partition_table.read()
		return partition_table

	def _set_id(self, id: str | int | UUID) -> None:
		self.id = id

	@property
	def str_id(self) -> str:
		return str(self.id)

	def _set_label(self) -> None:
		_run_command(["sfdisk", self.device.dev], input=f"label: {self.label}\nlabel-id: {self.str_id}\nwrite\n")

	def set_id(self, id: str | int | UUID | None = None) -> None:
		if id:
			self._set_id(id)
		self._set_label()

	def create(self) -> None:
		logger.info("Creating partition table %s on %r", self, self.device.dev)
		self._set_label()

	def _ioctl_read(self, code: int) -> int:
		buf = bytearray(struct.calcsize("I"))
		with open(self.device.dev, "rb") as f:
			fcntl.ioctl(f.fileno(), code, buf)
		return int(struct.unpack("I", buf)[0])

	def _get_sector_size(self) -> int:
		try:
			return self._ioctl_read(BLKSSZGET)
		except OSError as err:
			logger.warning("Failed to get sector size using ioctl, defaulting to 512: %s", err)
			if err.errno != errno.ENOTTY:  # not a block device
				raise
		return 512

	def read(self) -> None:
		data = self._read_data(self.device)
		self._set_id(data["partitiontable"]["id"])
		self.sector_size = self._get_sector_size()
		self._partitions = {}
		number_re = re.compile(r"\D(\d+)$")
		partition_type = GPTPartition if isinstance(self, GPTPartitionTable) else MBRPartition
		for part in data["partitiontable"].get("partitions", []):
			part["path"] = part.pop("node")
			match = number_re.search(part["path"])
			if not match:
				raise RuntimeError(f"Failed to get partition number from {part['path']}")
			number = int(match.group(1))

			self._partitions[number] = partition_type(self, number, **part)  # type: ignore

	def _create_partition(self, partition: TPartition) -> TPartition:
		logger.info("Creating partition: %s", partition)
		_run_command(["sfdisk", "-N", str(partition.number), self.device.dev], input=partition.sfdisk_command())
		self.read()
		return self._partitions[partition.number]

	def get_partition(self, number: int) -> TPartition:
		try:
			return self._partitions[number]
		except KeyError as err:
			raise ValueError(f"Partition {number} does not exist") from err

	def get_partitions(self) -> list[TPartition]:
		return list(self._partitions.values())

	@property
	def partitions(self) -> list[TPartition]:
		return self.get_partitions()

	def delete_partition(self, number: int) -> None:
		partition = self._partitions.get(number)
		if not partition:
			raise ValueError(f"Partition {number} does not exist")
		logger.info("Deleting partition: %s", partition)
		_run_command(["sfdisk", "--delete", self.device.dev, str(number)])
		self.read()


class MBRPartitionTable(PartitionTable):
	label = "dos"
	partition_type = MBRPartition

	def __init__(self, device: StorageDevice, id: int | str | None = None) -> None:
		super().__init__(device, id or randrange(0, 2**32 - 1))
		self._partitions: dict[int, MBRPartition] = {}

	def _set_id(self, id: str | int | UUID) -> None:
		if isinstance(id, str):
			id = int(id, base=16)
		self.id = int(id)

	@property
	def str_id(self) -> str:
		return f"0x{self.id:08x}"

	def create_partition(
		self,
		*,
		type: str,
		number: int | None = None,
		start: str | int | None = None,
		size: str | int | None = None,
		bootable: bool = False,
	) -> MBRPartition:
		if number is None:
			number = (list(self._partitions)[-1] if self._partitions else 0) + 1
		part = MBRPartition(partition_table=self, number=number, type=type, start=start, size=size, bootable=bootable)
		return self._create_partition(part)

	def get_partition(self, number: int) -> MBRPartition:
		return super().get_partition(number)

	def write_boot_record(self, type: str | None = None) -> None:
		arg = "-w"
		if type:
			arg = f"--{type.lower()}"
		out = _run_command(["ms-sys", "-f", arg, self.device.dev]).lower()
		if "unable to automaticly select boot record" in out:
			out = _run_command(["ms-sys", "-f", "--mbr7", self.device.dev])
		if "unable" in out or "usage:" in out:
			raise RuntimeError(f"Failed to write boot record: {out}")


class GPTPartitionTable(PartitionTable):
	label = "gpt"
	partition_type = GPTPartition

	def __init__(self, device: StorageDevice, id: UUID | str | None = None) -> None:
		super().__init__(device, str(id or uuid4()))
		self._partitions: dict[int, GPTPartition] = {}

	def _set_id(self, id: str | int | UUID) -> None:
		if not isinstance(id, UUID):
			self.id = str(UUID(str(id)))
		else:
			self.id = str(id)

	def create_partition(
		self,
		*,
		type: str,
		number: int | None = None,
		start: str | int | None = None,
		size: str | int | None = None,
		name: str | None = None,
		uuid: str | None = None,
	) -> GPTPartition:
		if number is None:
			number = (list(self._partitions)[-1] if self._partitions else 0) + 1
		part = GPTPartition(partition_table=self, number=number, type=type, start=start, size=size, name=name, uuid=uuid)
		return self._create_partition(part)

	def get_partition(self, number: int) -> GPTPartition:
		return super().get_partition(number)
