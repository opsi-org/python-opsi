# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
storage tests
"""

import errno
import platform
from pathlib import Path, PureWindowsPath
from uuid import UUID, uuid4

import pytest

from opsi.logging import LOG_WARNING
from opsi.testing.helper import log_stream

if platform.system() != "Linux":
	pytest.skip("storage tests are only relevant on Linux", allow_module_level=True)

import opsi.system.storage._storage as storage_module
from opsi.system.storage import (
	GPTPartition,
	GPTPartitionTable,
	MBRPartition,
	MBRPartitionTable,
	Partition,
	PartitionTable,
	StorageDevice,
	get_disks,
)
from opsi.system.storage._storage import PartitionTableType, _run_command


@pytest.mark.storage_utils
def test_get_disks() -> None:
	for disk in get_disks():
		assert isinstance(disk, StorageDevice)
		assert disk.path
		assert disk.size
		# assert disk.model
		# assert disk.serial
		print(disk)
		print(disk.partition_table)


def test_process_offset() -> None:
	device = StorageDevice(path="/tmp/none")
	device.size = 100 * 1024**3  # 100 GiB
	table = GPTPartitionTable(device)

	part = GPTPartition(partition_table=table, number=1, start=1, size=1, type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	assert part.start == 512
	assert part.size == 512

	part = GPTPartition(partition_table=table, number=1, start="2MiB", size="2MIb", type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	assert part.start == 2097152
	assert part.start % 2048 == 0
	assert part.size == 2097152
	assert part.size % 2048 == 0

	part = GPTPartition(partition_table=table, number=1, start="3MB", size="3GB", type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	assert part.start == 2097152
	assert part.start % 2048 == 0
	assert part.size == 2999975936
	assert part.size % 2048 == 0

	part = GPTPartition(partition_table=table, number=1, start="10%", size="50%", type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	assert part.start == 10737418240
	assert part.start % 2048 == 0
	assert part.size == 53687091200
	assert part.size % 2048 == 0

	part = GPTPartition(partition_table=table, number=1, start=None, size=None, type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	assert part.start == 0
	assert part.size == 0


@pytest.mark.storage_utils
def test_storage_device_info(tmp_path: Path) -> None:
	device_path = tmp_path / "dev"
	device_path.write_bytes(bytearray(4096))
	device = StorageDevice(path=device_path)
	assert device.size == 4096
	assert device.model is None


@pytest.mark.storage_utils
def test_wipe_metadata(tmp_path: Path) -> None:
	device_path = tmp_path / "dev"
	device_path.write_bytes(b"x" * 2048)
	device = StorageDevice(path=device_path)
	device.wipe_metadata()
	assert device_path.read_bytes() == (b"\0" * 1024) + (b"x" * 1024)


@pytest.mark.storage_utils
def test_set_ids(tmp_path: Path) -> None:  # pylint: disable=too-many-statements
	device_path = tmp_path / "dev"
	device_path.write_bytes(bytearray(1 * 1024 * 1024))
	device = StorageDevice(path=device_path)

	# GPT
	partition_table: PartitionTable = device.create_partition_table("GPT")
	assert partition_table.id
	assert isinstance(partition_table.id, str)
	assert UUID(partition_table.id)

	gpt_id = partition_table.id
	partition_table.read()

	assert gpt_id == partition_table.id
	new_gpt_id = uuid4()
	partition_table.set_id(new_gpt_id)
	assert partition_table.id == str(new_gpt_id)
	assert partition_table.str_id == str(new_gpt_id)

	gpt_id = partition_table.id
	partition_table.read()
	assert partition_table.id == str(new_gpt_id)

	partition_table = device.create_partition_table("GPT", "a0000000-0000-0000-0000-00000000000f")
	assert partition_table.id == "a0000000-0000-0000-0000-00000000000f"
	partition_table.read()
	assert partition_table.id == "a0000000-0000-0000-0000-00000000000f"

	partition_table.create_partition(type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7", number=1)
	partition_table.read()
	part = partition_table.get_partition(1)
	assert part.uuid
	assert isinstance(part.uuid, str)
	assert UUID(part.uuid)
	assert part.type == "ebd0a0a2-b9e5-4433-87c0-68b6b72699c7"

	part.set_uuid("10000000-0000-0000-0000-000000000001")
	assert part.uuid == "10000000-0000-0000-0000-000000000001"
	partition_table.read()
	part = partition_table.get_partition(1)
	assert part.uuid == "10000000-0000-0000-0000-000000000001"

	part.set_type(None)
	assert part.type == "00000000-0000-0000-0000-000000000000"
	partition_table.read()
	part = partition_table.get_partition(1)
	assert part.type == "00000000-0000-0000-0000-000000000000"

	part.set_type("56e49a75-462a-4ed8-bc43-28221e9a8aee")
	assert part.type == "56e49a75-462a-4ed8-bc43-28221e9a8aee"
	partition_table.read()
	part = partition_table.get_partition(1)
	assert part.type == "56e49a75-462a-4ed8-bc43-28221e9a8aee"

	part.set_type("linux")
	assert part.type == "0fc63daf-8483-4772-8e79-3d69d8477de4"
	partition_table.read()
	part = partition_table.get_partition(1)
	assert part.type == "0fc63daf-8483-4772-8e79-3d69d8477de4"

	# MBR
	partition_table = device.create_partition_table("MBR")
	assert partition_table.id
	assert isinstance(partition_table.id, int)

	mbr_id = partition_table.id
	partition_table.read()

	assert mbr_id == partition_table.id
	new_mbr_id = int("aabbccdd", 16)
	partition_table.set_id(new_mbr_id)
	assert partition_table.id == new_mbr_id
	assert partition_table.str_id == "0xaabbccdd"

	mbr_id = partition_table.id
	partition_table.read()
	assert partition_table.id == new_mbr_id

	partition_table = device.create_partition_table("MBR", "0xb0")
	assert partition_table.str_id == "0x000000b0"
	partition_table.read()
	assert partition_table.str_id == "0x000000b0"


@pytest.mark.storage_utils
def test_create_and_read_partition_table(tmp_path: Path) -> None:  # pylint: disable=too-many-statements
	device_path = tmp_path / "dev"
	device_path.write_bytes(bytearray(50 * 1024 * 1024))

	# GPT
	device = StorageDevice(path=device_path)
	partition_table: PartitionTable = device.create_partition_table("GPT")
	assert isinstance(partition_table, GPTPartitionTable)
	assert isinstance(partition_table.id, str)
	assert UUID(partition_table.id)
	gpt_id = partition_table.id

	partition_table.create_partition(type="uefi", start="1M", size="10M")
	partition_table.create_partition(type="00000000-0000-0000-0000-000000000002", start="11M", size="11M", name="part 2")
	partition_table.create_partition(type="00000000-0000-0000-0000-000000000003", start="22M", size="12M")
	partition_table.create_partition(type="00000000-0000-0000-0000-000000000004", start="34M", size="1M")
	partition_table.create_partition(type="00000000-0000-0000-0000-000000000005", start="49M", uuid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
	print(partition_table.partitions)

	assert partition_table.get_partition(1).type == "c12a7328-f81f-11d2-ba4b-00a0c93ec93b"
	assert partition_table.get_partition(1).number == 1
	assert partition_table.get_partition(1).start == 1048576
	assert partition_table.get_partition(1).size == 9437184
	assert partition_table.get_partition(1).uuid
	assert isinstance(partition_table.get_partition(1).uuid, str)
	assert UUID(partition_table.get_partition(1).uuid)
	assert partition_table.get_partition(2).name == "part2"
	assert partition_table.get_partition(3).number == 3
	assert partition_table.get_partition(3).start == 20971520
	assert partition_table.get_partition(3).size == 11534336
	assert partition_table.get_partition(5).number == 5
	assert partition_table.get_partition(5).start == 48234496
	assert partition_table.get_partition(5).size == 3145728
	assert partition_table.get_partition(5).uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

	device = StorageDevice(path=device_path)
	partition_table = device.read_partition_table()
	assert isinstance(partition_table, GPTPartitionTable)
	assert gpt_id == partition_table.id

	assert partition_table.get_partition(5).uuid == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
	partition_table.delete_partition(3)
	with pytest.raises(ValueError, match="Partition 3 does not exist"):
		partition_table.get_partition(3)

	partition_table.create_partition(number=3, type="00000000-0000-0000-0000-000000000003", start="22M", size="12M")
	assert partition_table.get_partition(3).number == 3
	assert partition_table.get_partition(3).start == 20971520
	assert partition_table.get_partition(3).size == 11534336

	# MBR
	device = StorageDevice(path=device_path)
	partition_table = device.create_partition_table("MBR")
	assert isinstance(partition_table, MBRPartitionTable)
	assert isinstance(partition_table.id, int)
	mbr_id = partition_table.id

	partition_table.create_partition(type="linux", start="1M", size="10M", bootable=True)
	partition_table.create_partition(type="a2", start="11M", size="11M")
	partition_table.create_partition(type="a3", start="22M", size="12M")
	partition_table.create_partition(type="a4", start="34M")
	print(partition_table.partitions)

	assert partition_table.get_partition(1).type == "83"
	assert partition_table.get_partition(1).number == 1
	assert partition_table.get_partition(1).start == 1048576
	assert partition_table.get_partition(1).size == 9437184
	assert partition_table.get_partition(2).number == 2
	assert partition_table.get_partition(2).start == 10485760
	assert partition_table.get_partition(2).size == 10485760
	assert partition_table.get_partition(3).number == 3
	assert partition_table.get_partition(3).start == 20971520
	assert partition_table.get_partition(3).size == 11534336
	assert partition_table.get_partition(4).number == 4
	assert partition_table.get_partition(4).start == 33554432
	assert partition_table.get_partition(4).size == 18874368

	device = StorageDevice(path=device_path)
	partition_table = device.read_partition_table()
	assert isinstance(partition_table, MBRPartitionTable)
	assert mbr_id == partition_table.id
	assert partition_table.get_partition(1).start == 1048576
	assert partition_table.get_partition(4).size == 18874368

	parts = partition_table.get_partitions()
	assert len(parts) == 4
	partition_table.delete_partition(3)
	parts = partition_table.partitions
	assert len(parts) == 3
	with pytest.raises(ValueError, match="Partition 3 does not exist"):
		partition_table.get_partition(3)

	partition_table.create_partition(number=3, type="a3", start="22M", size="12M")
	assert partition_table.get_partition(3).number == 3
	assert partition_table.get_partition(3).start == 20971520
	assert partition_table.get_partition(3).size == 11534336

	parts = partition_table.partitions
	assert len(parts) == 4


@pytest.mark.storage_utils
def test_create_filesystem(tmp_path: Path) -> None:
	device_path = tmp_path / "dev"
	device_path.write_bytes(bytearray(10 * 1024 * 1024))
	device = StorageDevice(path=device_path)
	table = device.create_partition_table("GPT")
	partition = table.create_partition(type="ebd0a0a2-b9e5-4433-87c0-68b6b72699c7")
	partition.path.write_bytes(bytearray(partition.size))
	partition.create_filesystem("ntfs", "test label")
	out = _run_command(["ntfslabel", partition.dev])
	assert out.strip() == "test label"


@pytest.mark.storage_utils
def test_create_boot_record(tmp_path: Path) -> None:
	device_path = tmp_path / "dev"
	device_path.write_bytes(bytearray(10 * 1024 * 1024))
	device = StorageDevice(path=device_path)

	table = device.create_partition_table(PartitionTableType.MBR)
	partition = table.create_partition(type="07")
	partition.path.write_bytes(bytearray(partition.size))
	partition.create_filesystem("ntfs")
	table.write_boot_record()
	partition.write_boot_record()
	table.write_boot_record("mbr")
	partition.write_boot_record("ntfs")

	table = device.create_partition_table("MBR")
	partition = table.create_partition(type="0c")
	partition.path.write_bytes(bytearray(partition.size))
	partition.create_filesystem("fat32")
	table.write_boot_record()
	partition.write_boot_record()
	table.write_boot_record("mbrdos")
	partition.write_boot_record("fat16")


def test_abs_path_win_path() -> None:
	device = StorageDevice(path="/not/existent")

	mount_point = "/mnt/win"
	windows_drive = "c"
	device.set_mount_point(mount_point)
	device.set_windows_drive(windows_drive)

	path: Path | PureWindowsPath = device.abs_path("windows/system32")
	assert isinstance(path, Path)
	assert str(path) == f"{mount_point}/windows/system32"
	path = device.abs_path("/windows/system32")
	assert str(path) == f"{mount_point}/windows/system32"

	path = device.win_path("windows/system32")
	assert isinstance(path, PureWindowsPath)
	assert str(path) == f"{windows_drive}:\\windows\\system32"
	path = device.win_path("/windows/system32")
	assert str(path) == f"{windows_drive}:\\windows\\system32"


def _noop_get_info(self: StorageDevice) -> None:
	return None


def test_get_block_devices_and_get_disks_filter_non_disk_entries(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(storage_module, "_run_command", lambda command: '{"blockdevices": [{"name": "/dev/sda", "type": "disk"}]}')
	assert storage_module._get_block_devices() == [{"name": "/dev/sda", "type": "disk"}]

	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	monkeypatch.setattr(
		storage_module,
		"_get_block_devices",
		lambda: [
			{"name": "/dev/sda", "type": "disk"},
			{"name": "/dev/sda1", "type": "part"},
			{"name": "/dev/sdb", "type": "disk"},
		],
	)

	disks = get_disks()

	assert [disk.dev for disk in disks] == ["/dev/sda", "/dev/sdb"]


def test_storage_device_populates_block_device_info_and_ignores_runtime_errors(monkeypatch: pytest.MonkeyPatch) -> None:
	def fake_read_partition_table(self: StorageDevice) -> None:
		raise RuntimeError("failed to read")

	monkeypatch.setattr(
		storage_module,
		"_get_block_devices",
		lambda: [{"name": "/dev/test0", "size": 2048, "model": "model-x", "serial": "serial-y"}],
	)
	monkeypatch.setattr(StorageDevice, "read_partition_table", fake_read_partition_table)

	device = StorageDevice(path="/dev/test0")

	assert device.dev == "/dev/test0"
	assert device.size == 2048
	assert device.model == "model-x"
	assert device.serial == "serial-y"
	assert str(device) == "StorageDevice(path=/dev/test0, size=2048, model='model-x', serial='serial-y')"


def test_storage_device_file_metadata_mounting_and_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	device_path = tmp_path / "device.img"
	device_path.write_bytes(b"x" * 2048)
	device = StorageDevice(path=device_path)

	assert device.size == 2048
	device.wipe_metadata()
	assert device_path.read_bytes() == (b"\0" * 1024) + (b"x" * 1024)

	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	mounted_device = StorageDevice(path="/dev/test1")
	commands: list[list[str]] = []

	def fake_run_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		commands.append(command)
		return ""

	monkeypatch.setattr(storage_module, "_run_command", fake_run_command)

	with pytest.raises(RuntimeError, match="mount_point not defined"):
		mounted_device.mount()
	with pytest.raises(RuntimeError, match="Not mounted"):
		mounted_device.umount()
	with pytest.raises(ValueError, match="mount_point not set"):
		mounted_device.abs_path("file")
	with pytest.raises(ValueError, match="windows_drive not set"):
		mounted_device.win_path("file")

	mount_point = tmp_path / "mnt"
	mounted_device.mount(mount_point)
	mounted_device.set_windows_drive("D")

	assert mount_point.is_dir()
	assert commands[0] == ["mount", "/dev/test1", str(mount_point)]
	assert mounted_device.abs_path(None) == mount_point
	assert mounted_device.abs_path("etc/hosts") == mount_point / "etc/hosts"
	assert mounted_device.abs_path("/etc/hosts") == mount_point / "etc/hosts"
	assert mounted_device.win_path(None) == PureWindowsPath("d:/")
	assert mounted_device.win_path("windows/system32") == PureWindowsPath("d:/windows/system32")
	assert mounted_device.win_path(mount_point / "windows/system32") == PureWindowsPath("d:/windows/system32")

	mounted_device.umount()
	assert commands[1] == ["umount", str(mount_point)]


def test_create_partition_table_and_filesystem_commands(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test2")
	created: list[str] = []
	read: list[str] = []
	commands: list[list[str]] = []

	def fake_create(self: PartitionTable) -> None:
		created.append(type(self).__name__)

	def fake_read(self: PartitionTable) -> None:
		read.append(type(self).__name__)

	def fake_run_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		commands.append(command)
		return ""

	monkeypatch.setattr(GPTPartitionTable, "create", fake_create)
	monkeypatch.setattr(GPTPartitionTable, "read", fake_read)
	monkeypatch.setattr(MBRPartitionTable, "create", fake_create)
	monkeypatch.setattr(MBRPartitionTable, "read", fake_read)
	monkeypatch.setattr(storage_module, "_run_command", fake_run_command)

	gpt_table = device.create_partition_table(PartitionTableType.GPT)
	mbr_table = device.create_partition_table("MBR", 123)

	assert isinstance(gpt_table, GPTPartitionTable)
	assert isinstance(mbr_table, MBRPartitionTable)
	assert created == ["GPTPartitionTable", "MBRPartitionTable"]
	assert read == ["GPTPartitionTable", "MBRPartitionTable"]

	with pytest.raises(ValueError, match="Invalid value 'bsd' for partition table type, supported values are: 'GPT', 'MBR'"):
		device.create_partition_table("bsd")

	device.create_filesystem("fat32", "EFI")
	device.create_filesystem("ntfs", "System")
	device.create_filesystem("ext4")

	assert commands == [
		["mkfs.vfat", "-F", "32", "-n", "EFI", "/dev/test2"],
		["mkfs.ntfs", "--fast", "--force", "-L", "System", "/dev/test2"],
		["mkfs.ext4", "/dev/test2"],
	]


def test_partition_offset_validation_and_base_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test3")
	table = PartitionTable(device, "id")
	partition = Partition(table, 1, type="dummy", path=tmp_path / "part.img")

	assert str(partition) == "Partition(number=1, start=0, size=0)"
	assert partition.sfdisk_command() == ""
	assert partition._process_offset("4KiB") == ("4KiB", 4096)

	with pytest.raises(ValueError, match="Invalid value"):
		partition._process_offset("invalid")
	with pytest.raises(ValueError, match="Invalid percentage value"):
		partition._process_offset("101%")
	with pytest.raises(ValueError, match="size of device is unknown"):
		partition._process_offset("10%")
	with pytest.raises(ValueError, match="Invalid unit"):
		partition._process_offset("2XB")


def test_mbr_partition_and_partition_table_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test4")
	table = MBRPartitionTable(device, "0x10")

	assert table.str_id == "0x00000010"

	with pytest.raises(ValueError, match="Invalid partition number"):
		MBRPartition(table, 0, type="83")
	with pytest.raises(ValueError, match="Invalid type"):
		MBRPartition(table, 1, type="invalid")

	with log_stream(LOG_WARNING, format="%(message)s") as stream:
		partition = MBRPartition(table, 5, type="linux", start=1, size=2, path="/dev/test4p5", bootable=True)

	assert "Logical MBR partitions not spported" in stream.getvalue()
	assert partition.sfdisk_command() == "type=83,start=1,size=2,bootable\n"

	boot_calls: list[list[str]] = []
	boot_outputs = iter(
		[
			"unable to automaticly select boot record: ntfs file system",
			"success",
			"usage: ms-sys",
		]
	)

	def fake_boot_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		boot_calls.append(command)
		return next(boot_outputs)

	monkeypatch.setattr(storage_module, "_run_command", fake_boot_command)
	partition.write_boot_record()
	assert boot_calls == [
		["ms-sys", "-f", "-w", "/dev/test4p5"],
		["ms-sys", "-f", "--ntfs", "/dev/test4p5"],
	]

	with pytest.raises(RuntimeError, match="Failed to write boot record"):
		partition.write_boot_record("fat16")

	table_calls: list[list[str]] = []
	table_outputs = iter(["unable to automaticly select boot record", "success", "unable to write"])

	def fake_table_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		table_calls.append(command)
		return next(table_outputs)

	monkeypatch.setattr(storage_module, "_run_command", fake_table_command)
	table.write_boot_record()
	assert table_calls == [
		["ms-sys", "-f", "-w", "/dev/test4"],
		["ms-sys", "-f", "--mbr7", "/dev/test4"],
	]
	with pytest.raises(RuntimeError, match="Failed to write boot record"):
		table.write_boot_record("mbr")

	auto_created: list[tuple[int, str]] = []

	def fake_create_partition(self: MBRPartitionTable, partition: MBRPartition) -> MBRPartition:
		auto_created.append((partition.number, partition.type))
		return partition

	monkeypatch.setattr(MBRPartitionTable, "_create_partition", fake_create_partition)
	table._partitions = {1: partition}
	auto_partition = table.create_partition(type="83")
	assert auto_partition.number == 2
	assert auto_created == [(2, "83")]


def test_gpt_partition_and_partition_table_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test5")
	table = GPTPartitionTable(device, uuid4())
	partition_uuid = uuid4()

	assert table.id == table.str_id

	with pytest.raises(ValueError, match="Invalid partition number"):
		GPTPartition(table, 129, type="linux")

	with log_stream(LOG_WARNING, format="%(message)s") as stream:
		partition = GPTPartition(table, 1, type="linux", start=1, size=2, name="data", uuid=partition_uuid, attrs="80")

	assert "GPT attributes not implemented" in stream.getvalue()
	assert partition.type == "0fc63daf-8483-4772-8e79-3d69d8477de4"
	assert partition.uuid == str(partition_uuid)
	assert partition.sfdisk_command() == (f'type=0fc63daf-8483-4772-8e79-3d69d8477de4,uuid={partition_uuid},name="data",start=1,size=2\n')
	assert GPTPartition(table, 2, type=None).type == "00000000-0000-0000-0000-000000000000"  # ty: ignore[invalid-argument-type]
	assert partition._set_type(partition_uuid) == str(partition_uuid)

	with pytest.raises(ValueError, match="Invalid type"):
		GPTPartition(table, 4, type="invalid")

	commands: list[list[str]] = []

	def fake_run_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		commands.append(command)
		return ""

	monkeypatch.setattr(storage_module, "_run_command", fake_run_command)
	partition.set_uuid("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
	partition.set_type(None)
	partition.set_name("EFI")

	assert commands == [
		["sfdisk", "--part-uuid", "/dev/test5", "1", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
		["sfdisk", "--part-type", "/dev/test5", "1", "00000000-0000-0000-0000-000000000000"],
		["sfdisk", "--part-label", "/dev/test5", "1", "EFI"],
	]

	auto_created: list[tuple[int, str]] = []

	def fake_create_partition(self: GPTPartitionTable, part: GPTPartition) -> GPTPartition:
		auto_created.append((part.number, part.type))
		return part

	monkeypatch.setattr(GPTPartitionTable, "_create_partition", fake_create_partition)
	table._partitions = {1: partition}
	auto_partition = table.create_partition(type="linux")
	assert auto_partition.number == 2
	assert auto_created == [(2, "0fc63daf-8483-4772-8e79-3d69d8477de4")]


def test_partition_table_factory_read_and_delete(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test6")
	read_calls: list[str] = []

	def fake_gpt_read(self: GPTPartitionTable) -> None:
		read_calls.append("gpt")

	def fake_mbr_read(self: MBRPartitionTable) -> None:
		read_calls.append("mbr")

	monkeypatch.setattr(GPTPartitionTable, "read", fake_gpt_read)
	monkeypatch.setattr(MBRPartitionTable, "read", fake_mbr_read)
	monkeypatch.setattr(
		PartitionTable,
		"_read_data",
		classmethod(lambda cls, storage_device: {"partitiontable": {"label": "gpt"}}),
	)
	assert isinstance(PartitionTable.from_device(device), GPTPartitionTable)
	monkeypatch.setattr(
		PartitionTable,
		"_read_data",
		classmethod(lambda cls, storage_device: {"partitiontable": {"label": "dos"}}),
	)
	assert isinstance(PartitionTable.from_device(device), MBRPartitionTable)
	assert read_calls == ["gpt", "mbr"]

	monkeypatch.setattr(
		PartitionTable,
		"_read_data",
		classmethod(lambda cls, storage_device: {"partitiontable": {"label": "bsd"}}),
	)
	with pytest.raises(NotImplementedError, match="Partition type bsd not supported"):
		PartitionTable.from_device(device)

	table = GPTPartitionTable(device, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
	assert str(table) == "GPTPartitionTable(partitions=0)"

	label_calls: list[tuple[list[str], str | None]] = []

	def fake_label_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		label_calls.append((command, input))
		return ""

	monkeypatch.setattr(storage_module, "_run_command", fake_label_command)
	table.set_id("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
	table.create()
	assert label_calls == [
		(
			[
				"sfdisk",
				"/dev/test6",
			],
			"label: gpt\nlabel-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb\nwrite\n",
		),
		(
			[
				"sfdisk",
				"/dev/test6",
			],
			"label: gpt\nlabel-id: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb\nwrite\n",
		),
	]


def test_partition_table_sector_size_read_create_and_delete(monkeypatch: pytest.MonkeyPatch) -> None:
	monkeypatch.setattr(StorageDevice, "_get_info", _noop_get_info)
	device = StorageDevice(path="/dev/test7")
	table = GPTPartitionTable(device, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

	monkeypatch.setattr(PartitionTable, "_ioctl_read", lambda self, code: 4096)
	assert table._get_sector_size() == 4096

	def raise_enotty(self: PartitionTable, code: int) -> int:
		raise OSError(errno.ENOTTY, "not a block device")

	monkeypatch.setattr(PartitionTable, "_ioctl_read", raise_enotty)
	assert table._get_sector_size() == 512

	def raise_eio(self: PartitionTable, code: int) -> int:
		raise OSError(errno.EIO, "io error")

	monkeypatch.setattr(PartitionTable, "_ioctl_read", raise_eio)
	with pytest.raises(OSError):
		table._get_sector_size()

	partition_uuid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaab"
	monkeypatch.setattr(GPTPartitionTable, "_get_sector_size", lambda self: 4096)
	monkeypatch.setattr(
		GPTPartitionTable,
		"_read_data",
		classmethod(
			lambda cls, storage_device: {
				"partitiontable": {
					"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
					"partitions": [
						{
							"node": "/dev/test7p1",
							"type": "linux",
							"start": 1,
							"size": 2,
							"name": "data",
							"uuid": partition_uuid,
						}
					],
				}
			}
		),
	)
	table.read()
	partition = table.get_partition(1)
	assert isinstance(partition, GPTPartition)
	assert table.id == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
	assert table.sector_size == 4096
	assert table.partitions == [partition]
	assert table.get_partitions() == [partition]

	with pytest.raises(ValueError, match="Partition 2 does not exist"):
		table.get_partition(2)

	monkeypatch.setattr(
		GPTPartitionTable,
		"_read_data",
		classmethod(
			lambda cls, storage_device: {
				"partitiontable": {
					"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
					"partitions": [{"node": "/dev/testx", "type": "linux"}],
				}
			}
		),
	)
	with pytest.raises(RuntimeError, match="Failed to get partition number"):
		table.read()

	commands: list[tuple[list[str], str | None]] = []

	def fake_run_command(command: list[str], input: str | None = None, valid_returncodes: list[int] | None = None) -> str:
		commands.append((command, input))
		return ""

	def fake_read(self: GPTPartitionTable) -> None:
		self._partitions = {3: GPTPartition(self, 3, type="linux", start=1, size=2)}

	monkeypatch.setattr(storage_module, "_run_command", fake_run_command)
	monkeypatch.setattr(GPTPartitionTable, "read", fake_read)
	created = table._create_partition(GPTPartition(table, 3, type="linux", start=1, size=2))
	assert created.number == 3
	assert commands[0][0] == ["sfdisk", "-N", "3", "/dev/test7"]
	assert commands[0][1] is not None
	assert commands[0][1].startswith("type=0fc63daf-8483-4772-8e79-3d69d8477de4,uuid=")
	assert commands[0][1].endswith(",start=1,size=2\n")

	with pytest.raises(ValueError, match="Partition 9 does not exist"):
		table.delete_partition(9)

	table._partitions = {3: created}
	table.delete_partition(3)
	assert commands[1] == (["sfdisk", "--delete", "/dev/test7", "3"], None)
