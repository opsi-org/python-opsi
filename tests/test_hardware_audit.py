# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017 uib GmbH <info@uib.de>

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

from OPSI.Object import OpsiClient


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
			"state": None,
			"memoryType": "Unknown",
			"lastseen": None,
			"model": None,
			"type": "AuditHardwareOnHost",
			"deviceLocator": "DIMM 1",
			"firstseen": None,
			"dataWidth": 64
		},
	])


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
		"model": None,
		"type": "AuditHardwareOnHost",
		"deviceLocator": "DIMM 1",
		"dataWidth": 64
	}

	backend.auditHardwareOnHost_createObjects([ahoh])
	backend.auditHardwareOnHost_updateObjects([ahoh])
