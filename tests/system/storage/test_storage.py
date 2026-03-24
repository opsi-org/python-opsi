# opsi.system is part of the desktop management solution opsi http://www.opsi.org
# Copyright (c) 2021-2025 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

"""
storage tests
"""

import platform
from pathlib import Path, PureWindowsPath
from uuid import UUID, uuid4

import pytest

from opsi.system.storage import (
	GPTPartition,
	GPTPartitionTable,
	MBRPartitionTable,
	PartitionTable,
	StorageDevice,
	get_disks,
)
from opsi.system.storage._storage import _run_command

if platform.system() != "Linux":
	pytest.skip("storage tests are only relevant on Linux", allow_module_level=True)


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

	table = device.create_partition_table("MBR")
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
