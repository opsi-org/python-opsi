# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017-2019 uib GmbH <info@uib.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Testing hardware audit behaviour.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import pytest
from OPSI.Object import AuditHardwareOnHost, OpsiClient


def testHardwareAuditAcceptingHugeMemoryClockSpeeds(hardwareAuditBackendWithHistory):
	"""
	Testing that the backend accepts a memory speed larger than the size
	of an signed int in MySQL.

	Datatype sizes are:
	* signed INT from -2147483648 to 2147483647
	* signed BIGINT from -9223372036854775808 to 9223372036854775807
	"""
	backend = hardwareAuditBackendWithHistory

	client = OpsiClient(id='foo.bar.invalid')
	backend.host_insertObject(client)

	backend.auditHardwareOnHost_setObsolete([client.id])
	backend.auditHardwareOnHost_updateObjects([
		{
			"hostId": client.id,
			"vendor": "Micron",
			"description": "Physikalischer Speicher",
			"tag": "Physical Memory 0",
			"speed": 2400000000,
			"hardwareClass": "MEMORY_MODULE",
			"formFactor": "SODIMM",
			"capacity": "8589934592",
			"name": "DIMM 1",
			"serialNumber": "15E64109",
			"memoryType": "Unknown",
			"type": "AuditHardwareOnHost",
			"deviceLocator": "DIMM 1",
			"dataWidth": 64
		},
	])


@pytest.mark.parametrize("objects", [1, 5, 50])
def testHardwareAuditObsoletingOldHardware(hardwareAuditBackendWithHistory, objects):
	backend = hardwareAuditBackendWithHistory

	client = OpsiClient(id='foo.bar.invalid')
	backend.host_insertObject(client)

	for _ in range(objects):
		ahoh = {
			"hostId": client.id,
			"vendor": "Micron",
			"description": "Physikalischer Speicher",
			"tag": "Physical Memory 0",
			"speed": 2400000000,
			"hardwareClass": "MEMORY_MODULE",
			"formFactor": "SODIMM",
			"capacity": "8589934592",
			"name": "DIMM 1",
			"serialNumber": "15E64109",
			"memoryType": "Unknown",
			"model": None,
			"type": "AuditHardwareOnHost",
			"deviceLocator": "DIMM 1",
			"dataWidth": 64,
			"state": 1
		}

		backend.auditHardwareOnHost_createObjects([ahoh])

	backend.auditHardwareOnHost_setObsolete([client.id])


@pytest.mark.parametrize("objects", [1, 5, 50])
def testHardwareAuditObsoletingAllObjects(hardwareAuditBackendWithHistory, objects):
	backend = hardwareAuditBackendWithHistory

	client = OpsiClient(id='foo.bar.invalid')
	backend.host_insertObject(client)

	for _ in range(objects):
		ahoh = {
			"hostId": client.id,
			"vendor": "Micron",
			"description": "Physikalischer Speicher",
			"tag": "Physical Memory 0",
			"speed": 2400000000,
			"hardwareClass": "MEMORY_MODULE",
			"formFactor": "SODIMM",
			"capacity": "8589934592",
			"name": "DIMM 1",
			"serialNumber": "15E64109",
			"memoryType": "Unknown",
			"model": None,
			"type": "AuditHardwareOnHost",
			"deviceLocator": "DIMM 1",
			"dataWidth": 64,
			"state": 1
		}

		backend.auditHardwareOnHost_createObjects([ahoh])

	backend.auditHardwareOnHost_setObsolete(None)


def testUpdatingAuditHardware(hardwareAuditBackendWithHistory):
	backend = hardwareAuditBackendWithHistory

	client = OpsiClient(id='foo.bar.invalid')
	backend.host_insertObject(client)

	ahoh = {
		"hostId": client.id,
		"vendor": "Micron",
		"description": "Physikalischer Speicher",
		"tag": "Physical Memory 0",
		"speed": 2400000000,
		"hardwareClass": "MEMORY_MODULE",
		"formFactor": "SODIMM",
		"capacity": "8589934592",
		"name": "DIMM 1",
		"serialNumber": "15E64109",
		"memoryType": "Unknown",
		"type": "AuditHardwareOnHost",
		"deviceLocator": "DIMM 1",
		"dataWidth": 64
	}

	backend.auditHardwareOnHost_createObjects([ahoh])
	backend.auditHardwareOnHost_updateObjects([ahoh])


def testAccepting10GBNetworkInterfaces(hardwareAuditBackendWithHistory):
	backend = hardwareAuditBackendWithHistory

	nic = {
		'vendorId': '15AD',
		'macAddress': '00:50:56:af:fe:af',
		'hardwareClass': 'NETWORK_CONTROLLER',
		'subsystemVendorId': '15AD',
		'type': 'AuditHardwareOnHost',
		'revision': '01',
		'hostId': 'machine.test.invalid',
		'vendor': 'VMware',
		'description': 'Ethernet interface',
		'subsystemDeviceId': '07B0',
		'deviceId': '07B0',
		'autoSense': 'off',
		'netConnectionStatus': 'yes',
		'maxSpeed': 10000000000,
		'name': 'VMXNET3 Ethernet Controller',
		'serialNumber': '00:50:56:af:fe:af',
		'model': 'VMXNET3 Ethernet Controller',
		'ipAddress': '192.168.123.45',
		'adapterType': 'twisted pair'
	}
	auditHardware = AuditHardwareOnHost.fromHash(nic)

	backend.auditHardwareOnHost_insertObject(auditHardware)
