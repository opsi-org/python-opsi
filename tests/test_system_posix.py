#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.System.Posix import getBlockDeviceContollerInfo, hardwareExtendedInventory


class PosixMethodsTestCase(unittest.TestCase):
	def testGetBlockDeviceContollerInfo(self):
		testcase = [
			'/0/100/1f.2               storage        82801JD/DO (ICH10 Family) SATA AHCI Controller [8086:3A02]',
			'/0/100/1f.3               bus            82801JD/DO (ICH10 Family) SMBus Controller [8086:3A60]',
			'/0/1          scsi0       storage',
			'/0/1/0.0.0    /dev/sda    disk           500GB ST3500418AS',
			'/0/1/0.0.0/1  /dev/sda1   volume         465GiB Windows FAT volume',
		]

		deviceInfo = getBlockDeviceContollerInfo('dev/sda', testcase)
		self.assertTrue(deviceInfo)

		self.assertEqual('dev/sda', deviceInfo['device'])
		self.assertEqual('8086', deviceInfo['vendorId'])
		self.assertEqual('/0/100/1f.2', deviceInfo['hwPath'])
		self.assertEqual('82801JD/DO (ICH10 Family) SATA AHCI Controller', deviceInfo['description'])
		self.assertEqual('3A02', deviceInfo['deviceId'])


class PosixHardwareInventoryTestCase(unittest.TestCase):
	def setUp(self):
		self.config = [
			{
				'Values': [
					{'Opsi': 'name', 'WMI': 'Name', 'UI': u'Name', 'Linux': 'id', 'Scope': 'i', 'Type': 'varchar(100)'},
					{'Opsi': 'description', 'WMI': 'Description', 'UI': u'Description', 'Linux': 'description', 'Scope': 'g', 'Type': 'varchar(100)'},
					{'Opsi': 'vendor', 'WMI': 'Manufacturer', 'UI': u'Vendor', 'Linux': 'vendor', 'Scope': 'g', 'Type': 'varchar(50)'},
					{'Opsi': 'model', 'WMI': 'Model', 'UI': u'Model', 'Linux': 'product', 'Scope': 'g', 'Type': 'varchar(100)'},
					{'Opsi': 'serialNumber', 'WMI': 'SerialNumber', 'UI': u'Serial number', 'Linux': 'serial', 'Scope': 'i', 'Type': 'varchar(50)'},
					{'Opsi': 'systemType', 'WMI': 'SystemType', 'UI': u'Type', 'Linux': 'configuration/chassis', 'Scope': 'i', 'Type': 'varchar(50)'},
					{'Opsi': 'totalPhysicalMemory', 'WMI': 'TotalPhysicalMemory', 'UI': u'Physical Memory', 'Linux': 'core/memory/size', 'Scope': 'i', 'Type': 'bigint', 'Unit': 'Byte'},
					{'Opsi': 'dellexpresscode', 'Python': "str(int(#{'COMPUTER_SYSTEM':'serialNumber','CHASSIS':'serialNumber'}#,36))", 'Cmd': "#dellexpresscode\\dellexpresscode.exe#.split('=')[1]", 'UI': u'Dell Expresscode', 'Scope': 'i', 'Type': 'varchar(50)', 'Condition': 'vendor=[dD]ell*'}
				],
				'Class': {'Opsi': 'COMPUTER_SYSTEM', 'WMI': 'select * from Win32_ComputerSystem', 'UI': u'Computer', 'Linux': '[lshw]system'}
			},
		]

		self.hardwareInfo = {
			"COMPUTER_SYSTEM" :
				[
					{
						"totalPhysicalMemory" : "2147483648",
						"vendor" : "Dell Inc.",
						"name" : "de-sie-gar-hk01",
						"systemType" : "desktop",
						"serialNumber" : "",
						"model" : "OptiPlex 755",
						"description" : "Desktop Computer"
					}
				]
			}

	def tearDown(self):
		del self.hardwareInfo

	def testHardwareExtendedInventory(self):
		result = hardwareExtendedInventory(self.config, self.hardwareInfo)

		expected = {
			'COMPUTER_SYSTEM': [
				{
					'dellexpresscode': None,
					'description': 'Desktop Computer',
					'model': 'OptiPlex 755',
					'name': 'de-sie-gar-hk01',
					'serialNumber': '',
					'systemType': 'desktop',
					'totalPhysicalMemory': '2147483648',
					'vendor': 'Dell Inc.'
				}
			]
		}
		self.assertNotEqual({}, result)
		self.assertEqual(expected, result)

	def testHardwareExtendedInventoryReturnsSafelyWithoutConfig(self):
		self.assertEqual({}, hardwareExtendedInventory({}, self.hardwareInfo))


if __name__ == '__main__':
	unittest.main()
