#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2014 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Systen.Posix

Various unittests to test functionality of python-opsi.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import mock
import os
import unittest

import OPSI.System.Posix as Posix


class PosixMethodsTestCase(unittest.TestCase):
	def testGetBlockDeviceContollerInfo(self):
		testcase = [
			'/0/100/1f.2               storage        82801JD/DO (ICH10 Family) SATA AHCI Controller [8086:3A02]',
			'/0/100/1f.3               bus            82801JD/DO (ICH10 Family) SMBus Controller [8086:3A60]',
			'/0/1          scsi0       storage',
			'/0/1/0.0.0    /dev/sda    disk           500GB ST3500418AS',
			'/0/1/0.0.0/1  /dev/sda1   volume         465GiB Windows FAT volume',
		]

		deviceInfo = Posix.getBlockDeviceContollerInfo('dev/sda', testcase)
		self.assertTrue(deviceInfo)

		self.assertEqual('dev/sda', deviceInfo['device'])
		self.assertEqual('8086', deviceInfo['vendorId'])
		self.assertEqual('/0/100/1f.2', deviceInfo['hwPath'])
		self.assertEqual('82801JD/DO (ICH10 Family) SATA AHCI Controller', deviceInfo['description'])
		self.assertEqual('3A02', deviceInfo['deviceId'])

	def testGetActiveSessionIds(self):
		testdata = [
			'wenselowski tty4         2014-05-20 13:54   .         24093',
			'wenselowski pts/0        2014-05-20 09:45 01:10       15884 (:0.0)',
			'wenselowski pts/1        2014-05-20 12:58 00:46       14849 (:0.0)',
			'wenselowski pts/3        2014-05-20 13:01 00:43       15401 (:0.0)',
			'wenselowski pts/4        2014-05-20 13:03 00:40       15688 (:0.0)',
			'wenselowski pts/6        2014-05-19 16:45 01:15       20496 (:0.0)',
			'wenselowski pts/7        2014-05-19 17:17 00:04       25574 (:0.0)',
			'wenselowski pts/8        2014-05-20 10:50 00:16       27443 (:0.0)',
			'wenselowski pts/9        2014-05-20 13:27   .         18172 (:0.0)',
			'wenselowski pts/10       2014-05-20 13:42 00:02       21605 (:0.0)',
		]

		expectedIds = [24093, 15884, 14849, 15401, 15688, 20496, 25574, 27443, 18172, 21605]

		self.assertEquals(expectedIds, Posix.getActiveSessionIds(data=testdata))

	def testGetActiveSessionId(self):
		self.assertEquals(type(1), type(Posix.getActiveSessionId()))

	def testGetNetworkInterfaces(self):
		# TODO: make this independent from the underlying hardware...
		# Idea: prepare a file with information, pass the filename
		# to the function and read from that.
		Posix.getNetworkInterfaces()

	def testReadingDHCPLeasesFile(self):
		leasesFile = os.path.join(os.path.dirname(__file__), 'testdata',
			'system', 'posix', 'dhclient.leases'
		)
		self.assertTrue(os.path.exists(leasesFile))

		dhcpConfig = Posix.getDHCPResult('eth0', leasesFile)
		self.assertEquals('172.16.166.102', dhcpConfig['fixed-address'])
		self.assertEquals('linux/pxelinux.0', dhcpConfig['filename'])
		self.assertEquals('255.255.255.0', dhcpConfig['subnet-mask'])
		self.assertEquals('172.16.166.1', dhcpConfig['routers'])
		self.assertEquals('172.16.166.1', dhcpConfig['domain-name-servers'])
		self.assertEquals('172.16.166.1', dhcpConfig['dhcp-server-identifier'])
		self.assertEquals('win7client', dhcpConfig['host-name'])
		self.assertEquals('vmnat.local', dhcpConfig['domain-name'])
		self.assertEquals('3 2014/05/28 12:31:42', dhcpConfig['renew'])
		self.assertEquals('3 2014/05/28 12:36:36', dhcpConfig['rebind'])
		self.assertEquals('3 2014/05/28 12:37:51', dhcpConfig['expire'])


class GetHarddisksTestCase(unittest.TestCase):
	def testGetHarddisks(self):
		testData = [
			'/dev/sda:  19922944',
			'total: 19922944 blocks',
		]


		with mock.patch('OPSI.System.Posix.execute'):
			disks = Posix.getHarddisks(data=testData)

		self.assertEquals(1, len(disks))

	def testGetHarddisksIgnoresEverythingOutsideDev(self):
		testData = [
			'/no/dev/sdb:  19922944',
			'/dev/sda:  19922944',
			'/tmp/sda:  19922944',
			'total: 19922944 blocks',
		]

		with mock.patch('OPSI.System.Posix.execute'):
			disks = Posix.getHarddisks(data=testData)

		self.assertEquals(1, len(disks))

	def testGetHarddisksFailsIfNoDisks(self):
		testData = [
			'/no/dev/sdb:  19922944',
			'total: 19922944 blocks',
		]

		with mock.patch('OPSI.System.Posix.execute'):
			self.assertRaises(Exception, Posix.getHarddisks, data=testData)


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
		result = Posix.hardwareExtendedInventory(self.config, self.hardwareInfo)

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
		self.assertEqual({}, Posix.hardwareExtendedInventory({}, self.hardwareInfo))


class HPProliantDisksTestCase(unittest.TestCase):
	"Testing the behaviour of Disk objects on HP Proliant Hardware."

	def testReadingPartitionTable(self):
		outputFromSfdiskListing = [
			"",
			"Disk /fakedev/cciss/c0d0: 17562 cylinders, 255 heads, 32 sectors/track",
			"Units = cylinders of 4177920 bytes, blocks of 1024 bytes, counting from 0",
			"",
			"   Device             Boot  Start     End   #cyls    #blocks Id  System",
			"/fakedev/cciss/c0d0p1          0+  16558-  16558- 67556352    7  HPFS/NTFS",
			"/fakedev/cciss/c0d0p2   *  16558+  17561    1004- 4095584    c  W95 FAT32 (LBA)",
			"/fakedev/cciss/c0d0p3          0       -       0 0    0  Empty",
			"/fakedev/cciss/c0d0p4          0       -       0 0    0  Empty",
		]


		with mock.patch('OPSI.System.Posix.execute'):
			d = Posix.Harddisk('/fakedev/cciss/c0d0')

		d.partitions = []  # Make sure no parsing happened before
		with mock.patch('os.path.exists', mock.Mock(return_value=True)):
			# Making sure that we do not run into a timeout.
			d._parsePartitionTable(outputFromSfdiskListing)

		self.assertEquals('/fakedev/cciss/c0d0', d.device)
		self.assertEquals(17562, d.cylinders)
		self.assertEquals(255, d.heads)
		self.assertEquals(32, d.sectors)
		self.assertEquals(17562, d.cylinders)
		self.assertEquals(4177920, d.bytesPerCylinder)

		self.assertTrue(len(d.partitions) > 0)

		outputFromSecondSfdiskListing = [
			"",
			"Disk /fakedev/cciss/c0d0: 17562 cylinders, 255 heads, 32 sectors/track",
			"Units = sectors of 512 bytes, counting from 0",
			"",
			"              Device  Boot    Start       End #sectors  Id System",
			"/fakedev/cciss/c0d0p1          2048 135114751 135112704  7  HPFS/NTFS",
			"/fakedev/cciss/c0d0p2   * 135114752 143305919 8191168    c  W95 FAT32 (LBA)",
			"/fakedev/cciss/c0d0p3             0         - 0          0  Empty",
			"/fakedev/cciss/c0d0p4             0         - 0          0  Empty",
		]

		d._parseSectorData(outputFromSecondSfdiskListing)

		self.assertTrue(len(d.partitions) > 0)
		self.assertEquals(
			2,
			len(d.partitions),
			"Read out {0} partitons instead of the expected 2. "
			"Maybe parsing empty partitions?".format(len(d.partitions))
		)

		first_partition_expected = {
			'fs': u'ntfs',
			'cylSize': 16558,
			'number': 1,
			'secStart': 2048,
			'secSize': 135112704,
			'device': u'/fakedev/cciss/c0d0p1',
			'size': 69177999360L,
			'cylStart': 0,
			'end': 69182177280L,
			'secEnd': 135114751,
			'boot': False,
			'start': 0,
			'cylEnd': 16558,
			'type': u'7'
		}
		self.assertEquals(first_partition_expected, d.partitions[0])

		last_partition_expected = {
			'fs': u'fat32',
			'cylSize': 1004,
			'number': 2,
			'secStart': 135114752,
			'secSize': 8191168,
			'device': u'/fakedev/cciss/c0d0p2',
			'size': 4194631680L,
			'cylStart': 16558,
			'end': 73372631040L,
			'secEnd': 143305919,
			'boot': True,
			'start': 69177999360L,
			'cylEnd': 17561,
			'type': u'c'
		}
		self.assertEquals(last_partition_expected, d.partitions[-1])


class DiskTestCase(unittest.TestCase):

	def testReadingPartitionTable(self):
		outputFromSfdiskListing = [
			" ",
			" Disk /fakedev/sdb: 4865 cylinders, 255 heads, 63 sectors/track",
			" Units = cylinders of 8225280 bytes, blocks of 1024 bytes, counting from 0",
			" ",
			"    Device     Boot  Start     End   #cyls   #blocks   Id  System",
			" /fakedev/sdb1   *      0+   4228-   4229-  33961984    7  HPFS/NTFS",
			" /fakedev/sdb2       4355+   4865-    511-   4096696    c  W95 FAT32 (LBA)",
			" /fakedev/sdb3          0       -       0          0    0  Empty",
			" /fakedev/sdb4          0       -       0          0    0  Empty",
		]

		with mock.patch('OPSI.System.Posix.execute'):
			d = Posix.Harddisk('/fakedev/sdb')

		d.size = 39082680 * 1024  # Faking this
		d.partitions = []  # Make sure no parsing happened before

		with mock.patch('os.path.exists', mock.Mock(return_value=True)):
			# Making sure that we do not run into a timeout.
			d._parsePartitionTable(outputFromSfdiskListing)

		self.assertEquals('/fakedev/sdb', d.device)
		self.assertEquals(4865, d.cylinders)
		self.assertEquals(255, d.heads)
		self.assertEquals(63, d.sectors)
		self.assertEquals(8225280, d.bytesPerCylinder)

		self.assertTrue(len(d.partitions) > 0)

		outputFromSecondSfdiskListing = [
			"",
			"Disk /fakedev/sdb: 4865 cylinders, 255 heads, 63 sectors/track",
			"Units = sectors of 512 bytes, counting from 0",
			"",
			"   Device Boot    Start       End   #sectors  Id  System",
			"/fakedev/sdb1   *      2048  67926015   67923968   7  HPFS/NTFS",
			"/fakedev/sdb2      69971968  78165359    8193392   c  W95 FAT32 (LBA)",
			"/fakedev/sdb3             0         -          0   0  Empty",
			"/fakedev/sdb4             0         -          0   0  Empty",
		]
		d._parseSectorData(outputFromSecondSfdiskListing)

		self.assertTrue(len(d.partitions) > 0, "We should have partitions even after the second parsing.")

		self.assertEquals(512, d.bytesPerSector)
		self.assertEquals(78165360, d.totalSectors)


		self.assertTrue(4, len(d.partitions))

		expected = {
			'fs': u'ntfs',
			'cylSize': 4229,
			'number': 1,
			'secStart': 2048,
			'secSize': 67923968,
			'device': u'/fakedev/sdb1',
			'size': 34784709120L,
			'cylStart': 0,
			'end': 34784709120L,
			'secEnd': 67926015,
			'boot': True,
			'start': 0,
			'cylEnd': 4228,
			'type': u'7'
		}
		self.assertEquals(expected, d.partitions[0])

		expected_last_partition = {
			'fs': u'fat32',
			'cylSize': 511,
			'number': 2,
			'secStart': 69971968,
			'secSize': 8193392,
			'device': u'/fakedev/sdb2',
			'size': 4203118080L,
			'cylStart': 4355,
			'end': 40024212480L,
			'secEnd': 78165359,
			'boot': False,
			'start': 35821094400L,
			'cylEnd': 4865,
			'type': u'c'
		}
		self.assertEquals(expected_last_partition, d.partitions[-1])


class GetSambaServiceNameTestCase(unittest.TestCase):
	def testGettingDefaultIfNothingElseParsed(self):
		with mock.patch('OPSI.System.Posix.getServiceNames'):
			self.assertEquals("blabla", Posix.getSambaServiceName(default="blabla"))

	def testNoDefaultNoResultRaisesException(self):
		with mock.patch('OPSI.System.Posix.getServiceNames'):
			self.assertRaises(RuntimeError, Posix.getSambaServiceName)

	def testGettingFoundSambaServiceName(self):
		# TODO: make the tests run on SLES11SP3...
		with mock.patch('OPSI.System.Posix.getServiceNames', mock.Mock(return_value=set("abc"))):
			self.assertRaises(RuntimeError, Posix.getSambaServiceName)

		with mock.patch('OPSI.System.Posix.getServiceNames',  mock.Mock(return_value=set(["abc", "smb", "def"]))):
			self.assertEquals("smb", Posix.getSambaServiceName())

		with mock.patch('OPSI.System.Posix.getServiceNames',  mock.Mock(return_value=set(["abc", "smbd", "def"]))):
			self.assertEquals("smbd", Posix.getSambaServiceName())

		with mock.patch('OPSI.System.Posix.getServiceNames',  mock.Mock(return_value=set(["abc", "samba", "def"]))):
			self.assertEquals("samba", Posix.getSambaServiceName())


	def testParsingServiceOnDebian(self):
		commandOutput = [
			' [ ? ]  alsa-utils',
			' [ - ]  anacron',
			' [ + ]  atd',
			' [ ? ]  bootmisc.sh',
			' [ - ]  x11-common',
		]

		self.assertEquals(
			set(["alsa-utils", "anacron", "atd", "bootmisc.sh", "x11-common"]),
			Posix.getServiceNames(_serviceStatusOutput=commandOutput)
		)

	def testParsingServiceOnRHEL6(self):
		output = [
			'atd (PID  1439) wird ausgeführt ...',
			'dhcpd wurde beendet',
			'Tabelle: filter',
			'Chain INPUT (policy ACCEPT)',
			'num  target     prot opt source               destination         ',
			'1    ACCEPT     all      ::/0                 ::/0                state RELATED,ESTABLISHED ',
			'2    ACCEPT     icmpv6    ::/0                 ::/0                ',
			'3    ACCEPT     all      ::/0                 ::/0                ',
			'4    ACCEPT     tcp      ::/0                 ::/0                state NEW tcp dpt:22 ',
			'5    REJECT     all      ::/0                 ::/0                reject-with icmp6-adm-prohibited ',
			'',
			'Chain FORWARD (policy ACCEPT)',
			'num  target     prot opt source               destination         ',
			'1    REJECT     all      ::/0                 ::/0                reject-with icmp6-adm-prohibited ',
			'',
			'Chain OUTPUT (policy ACCEPT)',
			'num  target     prot opt source               destination         ',
			'',
			'iptables: Firewall läuft nicht. ',
			'lvmetad wurde beendet',
			'Netconsole-Modul nicht geladen',
			'Konfigurierte Geräte:',
			'lo eth0',
			'Derzeit aktive Geräte:',
			'lo eth0',
			'nmbd wurde beendet',
			'Checking opsi config service... (running).',
		]

		self.assertEquals(
			set(["atd", "dhcpd", "lvmetad", "nmbd"]),
			Posix.getServiceNames(_serviceStatusOutput=output)
		)

	def testParsingFromSystemd(self):
		output = [
			'iprdump.service - LSB: Start the ipr dump daemon',
			'   Loaded: loaded (/etc/rc.d/init.d/iprdump)',
			'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 14s ago',
			'  Process: 572 ExecStart=/etc/rc.d/init.d/iprdump start (code=exited, status=0/SUCCESS)',
			' Main PID: 581 (iprdump)',
			'   CGroup: /system.slice/iprdump.service',
			'           └─581 /sbin/iprdump --daemon',
			'',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local iprdump[572]: Starting iprdump: [  OK  ]',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local systemd[1]: Started LSB: Start the ipr dump daemon.',
			'iprinit.service - LSB: Start the ipr init daemon',
			'   Loaded: loaded (/etc/rc.d/init.d/iprinit)',
			'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 15s ago',
			'  Process: 537 ExecStart=/etc/rc.d/init.d/iprinit start (code=exited, status=0/SUCCESS)',
			' Main PID: 566 (iprinit)',
			'   CGroup: /system.slice/iprinit.service',
			'           └─566 /sbin/iprinit --daemon',
			'',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local iprinit[537]: Starting iprinit: [  OK  ]',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local systemd[1]: Started LSB: Start the ipr init daemon.',
			'iprupdate.service - LSB: Start the iprupdate utility',
			'   Loaded: loaded (/etc/rc.d/init.d/iprupdate)',
			'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 15s ago',
			'  Process: 525 ExecStart=/etc/rc.d/init.d/iprupdate start (code=exited, status=0/SUCCESS)',
			' Main PID: 567 (iprupdate)',
			'   CGroup: /system.slice/iprupdate.service',
			'           └─567 /sbin/iprupdate --daemon',
			'',
			'Okt 07 15:53:34 stb-40-srv-106.uib.local systemd[1]: Starting LSB: Start the iprupdate utility...',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local iprupdate[525]: Starting iprupdate: [  OK  ]',
			'Okt 07 15:53:35 stb-40-srv-106.uib.local systemd[1]: Started LSB: Start the iprupdate utility.',
			'Netconsole-Modul nicht geladen',
			'Konfigurierte Geräte:',
			'lo ens18',
			'Derzeit aktive Geräte:',
			'lo ens18',
		]

		self.assertEquals(
			set(["iprdump", "iprinit", "iprupdate"]),
			Posix.getServiceNames(_serviceStatusOutput=output)
		)

	def testParsingOpenSuse131(self):
		output = [
			'getty@tty1.service                                                           loaded active running Getty on tty1',
			'lvm2-lvmetad.service                                                         loaded active running LVM2 metadata daemon',
			'rc-local.service                                                             loaded active exited  /etc/init.d/boot.local Compatibility',
			'SuSEfirewall2.service                                                        loaded active exited  SuSEfirewall2 phase 2',
			'SuSEfirewall2_init.service                                                   loaded active exited  SuSEfirewall2 phase 1',
			'systemd-fsck@dev-disk-by\x2did-ata\x2dQEMU_HARDDISK_QM00005\x2dpart1.service loaded active exited  File System Check on /dev/disk/by-id/ata-QEMU_HARDDISK_QM00005-part1',
			'systemd-random-seed.service                                                  loaded active exited  Load/Save Random Seed',
			'user@0.service                                                               loaded active running User Manager for 0',
			'user@993.service                                                             loaded active running User Manager for 993',
		]

		self.assertEquals(
			set(
				[
					"getty@tty1", "lvm2-lvmetad", "rc-local", "SuSEfirewall2",
					"SuSEfirewall2_init",
					"systemd-fsck@dev-disk-by\x2did-ata\x2dQEMU_HARDDISK_QM00005\x2dpart1",
					"systemd-random-seed", "user@0", "user@993"
				]
			),
			Posix.getServiceNames(_serviceStatusOutput=output)
		)

	def testParsingOpensuse121(self):
		output = [
			'redirecting to systemctl',
			'SuSEfirewall2_init.service - LSB: SuSEfirewall2 phase 1',
			'	  Loaded: loaded (/etc/init.d/SuSEfirewall2_init)',
			'	  Active: inactive (dead)',
			'	  CGroup: name=systemd:/system/SuSEfirewall2_init.service',
			'Checking the status of SuSEfirewall2                                                                        unused',
			'redirecting to systemctl',
			'avahi-daemon.service - Avahi mDNS/DNS-SD Stack',
			'	  Loaded: loaded (/lib/systemd/system/avahi-daemon.service; enabled)',
			'	  Active: active (running) since Tue, 07 Oct 2014 16:00:13 +0200; 6min ago',
			'	Main PID: 611 (avahi-daemon)',
			'	  Status: "Server startup complete. Host name is stb-40-srv-111.local. Local service cookie is 634832754."',
			'	  CGroup: name=systemd:/system/avahi-daemon.service',
			'		  └ 611 avahi-daemon: running [stb-40-srv-111.local]',
			'redirecting to systemctl',
			'cgroup.service',
			'	  Loaded: masked (/dev/null)',
			'	  Active: inactive (dead)',
			'redirecting to systemctl',
			'device-mapper.service',
			'	  Loaded: masked (/dev/null)',
			'	  Active: inactive (dead)',
			'',
			"Warning: Unit file changed on disk, 'systemctl --system daemon-reload' recommended.",
			'redirecting to systemctl',
			'udev.service - udev Kernel Device Manager',
			'	  Loaded: loaded (/lib/systemd/system/udev.service; static)',
			'	  Active: active (running) since Tue, 07 Oct 2014 16:00:10 +0200; 6min ago',
			'	Main PID: 319 (udevd)',
			'	  CGroup: name=systemd:/system/udev.service',
			'		  ├ 319 /sbin/udevd',
			'		  ├ 452 /sbin/udevd',
			'		  └ 453 /sbin/udevd',
			'Checking opsi config service... (not running).',
		]

		self.assertEquals(
			set(["SuSEfirewall2_init", "SuSEfirewall2", "avahi-daemon",
				 "cgroup", "device-mapper", "udev"]),
			Posix.getServiceNames(_serviceStatusOutput=output)
		)


	def testParsingOpensuse122andOpenSuse123(self):
		output = [
			'console-kit-log-system-start.service loaded active exited      Console System Startup Logging',
			'getty@tty1.service                   loaded active running     Getty on tty1',
			'opsipxeconfd.service                 loaded failed failed      LSB: opsi pxe config service',
			'rc-local.service                     loaded active exited      /etc/init.d/boot.local Compatibility',
			'sshd.service                         loaded active running     OpenSSH Daemon',
			'SuSEfirewall2_setup.service          loaded active exited      LSB: SuSEfirewall2 phase 2',
		]

		self.assertEquals(
			set(["console-kit-log-system-start", "getty@tty1", "opsipxeconfd",
				 "rc-local", "sshd", "SuSEfirewall2_setup"]),
			Posix.getServiceNames(_serviceStatusOutput=output)
		)


if __name__ == '__main__':
	unittest.main()
