# This file is part of the device management solution OPSI http://www.opsi.org
# Copyright (c) 2020-2026 uib GmbH <info@uib.de>
# This code is owned by the uib GmbH, Mainz, Germany (uib.de). All rights reserved.
# License: AGPL-3.0-only

from opsi.system.storage._storage import (
	GPTPartition,
	GPTPartitionTable,
	MBRPartition,
	MBRPartitionTable,
	Partition,
	PartitionTable,
	StorageDevice,
	get_disks,
)

__all__ = [
	"StorageDevice",
	"PartitionTable",
	"MBRPartitionTable",
	"GPTPartitionTable",
	"Partition",
	"MBRPartition",
	"GPTPartition",
	"get_disks",
]
