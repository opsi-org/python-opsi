# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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
import pytest
import sys
from contextlib import contextmanager

import OPSI.System.Posix as Posix

if sys.version_info > (3, ):
	long = int


def testGetBlockDeviceContollerInfo():
	data = [
		'/0/100/1f.2               storage        82801JD/DO (ICH10 Family) SATA AHCI Controller [8086:3A02]',
		'/0/100/1f.3               bus            82801JD/DO (ICH10 Family) SMBus Controller [8086:3A60]',
		'/0/1          scsi0       storage',
		'/0/1/0.0.0    /dev/sda    disk           500GB ST3500418AS',
		'/0/1/0.0.0/1  /dev/sda1   volume         465GiB Windows FAT volume',
	]

	deviceInfo = Posix.getBlockDeviceContollerInfo('dev/sda', data)
	assert deviceInfo

	assert 'dev/sda' == deviceInfo['device']
	assert '8086' == deviceInfo['vendorId']
	assert '/0/100/1f.2' == deviceInfo['hwPath']
	assert '82801JD/DO (ICH10 Family) SATA AHCI Controller' == deviceInfo['description']
	assert '3A02' == deviceInfo['deviceId']


def testGetActiveSessionIds():
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

	assert expectedIds == Posix.getActiveSessionIds(data=testdata)


def testGetActiveSessionId():
	assert isinstance(Posix.getActiveSessionId(), int)


def testGetNetworkInterfaces():
	# TODO: make this independent from the underlying hardware...
	# Idea: prepare a file with information, pass the filename
	# to the function and read from that.
	Posix.getNetworkInterfaces()


def testReadingDHCPLeasesFile():
	leasesFile = os.path.join(
		os.path.dirname(__file__),
		'testdata', 'system', 'posix', 'dhclient.leases'
	)
	assert os.path.exists(leasesFile)

	dhcpConfig = Posix.getDHCPResult('eth0', leasesFile)
	assert '172.16.166.102' == dhcpConfig['fixed-address']
	assert 'linux/pxelinux.0' == dhcpConfig['filename']
	assert '255.255.255.0' == dhcpConfig['subnet-mask']
	assert '172.16.166.1' == dhcpConfig['routers']
	assert '172.16.166.1' == dhcpConfig['domain-name-servers']
	assert '172.16.166.1' == dhcpConfig['dhcp-server-identifier']
	assert 'win7client' == dhcpConfig['host-name']
	assert 'vmnat.local' == dhcpConfig['domain-name']
	assert '3 2014/05/28 12:31:42' == dhcpConfig['renew']
	assert '3 2014/05/28 12:36:36' == dhcpConfig['rebind']
	assert '3 2014/05/28 12:37:51' == dhcpConfig['expire']


def testGetHarddisks():
	testData = [
		'/dev/sda:  19922944',
		'total: 19922944 blocks',
	]

	with mock.patch('OPSI.System.Posix.execute'):
		disks = Posix.getHarddisks(data=testData)

	assert 1 == len(disks)


def testGetHarddisksIgnoresEverythingOutsideDev():
	testData = [
		'/no/dev/sdb:  19922944',
		'/dev/sda:  19922944',
		'/tmp/sda:  19922944',
		'total: 19922944 blocks',
	]

	with mock.patch('OPSI.System.Posix.execute'):
		disks = Posix.getHarddisks(data=testData)

	assert 1 == len(disks)


def testGetHarddisksFailsIfNoDisks():
	testData = [
		'/no/dev/sdb:  19922944',
		'total: 19922944 blocks',
	]

	with mock.patch('OPSI.System.Posix.execute'):
		with pytest.raises(Exception):
			Posix.getHarddisks(data=testData)


@pytest.fixture
def hardwareConfigAndHardwareInfo():
	config = [
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

	hardwareInfo = {
		"COMPUTER_SYSTEM":
			[
				{
					"totalPhysicalMemory": "2147483648",
					"vendor": "Dell Inc.",
					"name": "de-sie-gar-hk01",
					"systemType": "desktop",
					"serialNumber": "",
					"model": "OptiPlex 755",
					"description": "Desktop Computer"
				}
			]
		}

	yield config, hardwareInfo


def testHardwareExtendedInventory(hardwareConfigAndHardwareInfo):
	config, hardwareInfo = hardwareConfigAndHardwareInfo
	result = Posix.hardwareExtendedInventory(config, hardwareInfo)

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
	assert {} != result
	assert expected == result


def testHardwareExtendedInventoryReturnsSafelyWithoutConfig(hardwareConfigAndHardwareInfo):
	config, hardwareInfo = hardwareConfigAndHardwareInfo
	assert {} == Posix.hardwareExtendedInventory({}, hardwareInfo)


@pytest.mark.parametrize("versionString, isUbuntuXenial", [
	('sfdisk von util-linux 2.27.1', True),
	('sfdisk von util-linux 2.20.1', False)
])
def testGettingSfdiskVersion(versionString, isUbuntuXenial):
	with mock.patch('OPSI.System.Posix.execute', mock.Mock(return_value=[versionString])):
		with mock.patch('OPSI.System.Posix.which', mock.Mock(return_value='/sbin/sfdisk')):
			assert Posix.isXenialSfdiskVersion() == isUbuntuXenial


@pytest.mark.skipif(True, reason="temporarily disabled")
def testReadingPartitionTableOnHPProliantDisksTest():
	"Testing the behaviour of Disk objects on HP Proliant Hardware."

	outputFromSfdiskListing = [
		"",
		"Disk /dev/cciss/c0d0: 298,1 GiB, 320039378944 bytes, 625076912 sectors",
		"Units: sectors of 1 * 512 = 512 bytes",
		"Sector size (logical/physical): 512 bytes / 512 bytes",
		"I/O size (minimum/optimal): 512 bytes / 512 bytes",
		"Disklabel type: dos",
		"Disk identifier: 0xa7c8dddf",
		"",
		"Device            Boot Start       End   Sectors   Size Id Type",
		"/fakedev/cciss/c0d0p1 *     2048 625074863 625072816 298,1G  7 HPFS/NTFS/exFAT",
	]

	outputFromSfdiskGeometry = [
		"/fakedev/cciss/c0d0: 76602 cylinders, 255 heads, 32 sectors/track",
	]

	with mock.patch('OPSI.System.Posix.execute'):
		d = Posix.Harddisk('/fakedev/cciss/c0d0')

	with mock.patch('OPSI.System.Posix.execute', mock.Mock(return_value=outputFromSfdiskGeometry)):
		with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=True)):
			with mock.patch('os.path.exists', mock.Mock(return_value=True)):
				d._parsePartitionTable(outputFromSfdiskListing)

		assert '/fakedev/cciss/c0d0' == d.device
		assert 76602 == d.cylinders
		assert 255 == d.heads
		assert 32 == d.sectors
		# assert 4177920 == d.bytesPerCylinder
		assert len(d.partitions) > 0

	outputFromSecondSfdiskListing = [
		"",
		"Disk /dev/cciss/c0d0: 298,1 GiB, 320039378944 bytes, 625076912 sectors",
		"Units: sectors of 1 * 512 = 512 bytes",
		"Sector size (logical/physical): 512 bytes / 512 bytes",
		"I/O size (minimum/optimal): 512 bytes / 512 bytes",
		"Disklabel type: dos",
		"Disk identifier: 0xa7c8dddf",
		"",
		"Device            Boot Start       End   Sectors   Size Id Type",
		"/fakedev/cciss/c0d0p1 *     2048 625074863 625072816 298,1G 7 HPFS/NTFS/exFAT",
	]

	blkidOutput = [
		"ntfs"
	]

	with mock.patch('OPSI.System.Posix.execute', mock.Mock(return_value=blkidOutput)):
		with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=True)):
			d._parseSectorData(outputFromSecondSfdiskListing)

	assert len(d.partitions) > 0
	assert 1 == len(d.partitions)

	first_partition_expected = {
		'fs': u'ntfs',
		'cylSize': 625072816,
		'number': 1,
		'secStart': 2048,
		'secSize': 625072816,
		'device': u'/fakedev/cciss/c0d0p1',
		'size': long(69177999360),
		'cylStart': 0,
		'end': long(69182177280),
		'secEnd': 135114751,
		'boot': False,
		'start': 0,
		'cylEnd': 16558,
		'type': u'HPFS/NTFS'
	}
	assert first_partition_expected == d.partitions[0]


def testReadingPartitionTableOnHPProliantDisksWithOldSfdiskVersion():
	"Testing the behaviour of Disk objects on HP Proliant Hardware with an old version of sfdisk."
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

	with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=False)):
		with mock.patch('os.path.exists', mock.Mock(return_value=True)):
			d._parsePartitionTable(outputFromSfdiskListing)

	assert '/fakedev/cciss/c0d0' == d.device
	assert 17562 == d.cylinders
	assert 255 == d.heads
	assert 32 == d.sectors
	assert 4177920 == d.bytesPerCylinder

	assert len(d.partitions) > 0

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

	with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=False)):
		d._parseSectorData(outputFromSecondSfdiskListing)

	assert len(d.partitions) > 0
	assert 2 == len(d.partitions)

	first_partition_expected = {
		'fs': u'ntfs',
		'cylSize': 16558,
		'number': 1,
		'secStart': 2048,
		'secSize': 135112704,
		'device': u'/fakedev/cciss/c0d0p1',
		'size': long(69177999360),
		'cylStart': 0,
		'end': long(69182177280),
		'secEnd': 135114751,
		'boot': False,
		'start': 0,
		'cylEnd': 16558,
		'type': u'7'
	}
	assert first_partition_expected == d.partitions[0]

	last_partition_expected = {
		'fs': u'fat32',
		'cylSize': 1004,
		'number': 2,
		'secStart': 135114752,
		'secSize': 8191168,
		'device': u'/fakedev/cciss/c0d0p2',
		'size': long(4194631680),
		'cylStart': 16558,
		'end': long(73372631040),
		'secEnd': 143305919,
		'boot': True,
		'start': long(69177999360),
		'cylEnd': 17561,
		'type': u'c'
	}
	assert last_partition_expected == d.partitions[-1]


def testReadingPartitionTableFromOldSfdiskVersion():
	# TODO: proper name plz
	# TODO: is this still relevant?
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

	with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=False)):
		with mock.patch('os.path.exists', mock.Mock(return_value=True)):
			# Making sure that we do not run into a timeout.
			d._parsePartitionTable(outputFromSfdiskListing)

	assert '/fakedev/sdb' == d.device
	assert 4865 == d.cylinders
	assert 255 == d.heads
	assert 63 == d.sectors
	assert 8225280 == d.bytesPerCylinder

	assert len(d.partitions) > 0

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
	with mock.patch('OPSI.System.Posix.isXenialSfdiskVersion', mock.Mock(return_value=False)):
		d._parseSectorData(outputFromSecondSfdiskListing)

	assert 512 == d.bytesPerSector
	assert 78165360 == d.totalSectors
	assert len(d.partitions) > 0
	assert 2 == len(d.partitions)

	expected = {
		'fs': u'ntfs',
		'cylSize': 4229,
		'number': 1,
		'secStart': 2048,
		'secSize': 67923968,
		'device': u'/fakedev/sdb1',
		'size': long(34784709120),
		'cylStart': 0,
		'end': long(34784709120),
		'secEnd': 67926015,
		'boot': True,
		'start': 0,
		'cylEnd': 4228,
		'type': u'7'
	}
	assert expected == d.partitions[0]

	expected_last_partition = {
		'fs': u'fat32',
		'cylSize': 511,
		'number': 2,
		'secStart': 69971968,
		'secSize': 8193392,
		'device': u'/fakedev/sdb2',
		'size': long(4203118080),
		'cylStart': 4355,
		'end': long(40024212480),
		'secEnd': 78165359,
		'boot': False,
		'start': long(35821094400),
		'cylEnd': 4865,
		'type': u'c'
	}
	assert expected_last_partition == d.partitions[-1]


def testGetSambaServiceNameGettingDefaultIfNothingElseParsed():
	with mock.patch('OPSI.System.Posix.getServiceNames'):
		assert "blabla" == Posix.getSambaServiceName(default="blabla", staticFallback=False)


@pytest.mark.parametrize("values", ([], set("abc")))
def testGetSambaServiceNameFailsIfNoServiceFound(values):
	with mock.patch('OPSI.System.Posix.getServiceNames', mock.Mock(return_value=values)):
		with pytest.raises(RuntimeError):
			Posix.getSambaServiceName(staticFallback=False)


@pytest.mark.parametrize("expectedName, services", (
	("smb", set(["abc", "smb", "def"])),
	("smbd", set(["abc", "smbd", "def"])),
	("samba", set(["abc", "samba", "def"])),
))
def testGetSambaServiceNameGettingFoundSambaServiceName(expectedName, services):
	with mock.patch('OPSI.System.Posix.getServiceNames',  mock.Mock(return_value=services)):
		assert expectedName == Posix.getSambaServiceName()


def testGetServiceNameParsingFromSystemd():
	output = [
		'iprdump.service - LSB: Start the ipr dump daemon',
		'   Loaded: loaded (/etc/rc.d/init.d/iprdump)',
		'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 14s ago',
		'  Process: 572 ExecStart=/etc/rc.d/init.d/iprdump start (code=exited, status=0/SUCCESS)',
		' Main PID: 581 (iprdump)',
		'   CGroup: /system.slice/iprdump.service',
		'           └─581 /sbin/iprdump --daemon',
		'',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid iprdump[572]: Starting iprdump: [  OK  ]',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid systemd[1]: Started LSB: Start the ipr dump daemon.',
		'iprinit.service - LSB: Start the ipr init daemon',
		'   Loaded: loaded (/etc/rc.d/init.d/iprinit)',
		'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 15s ago',
		'  Process: 537 ExecStart=/etc/rc.d/init.d/iprinit start (code=exited, status=0/SUCCESS)',
		' Main PID: 566 (iprinit)',
		'   CGroup: /system.slice/iprinit.service',
		'           └─566 /sbin/iprinit --daemon',
		'',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid iprinit[537]: Starting iprinit: [  OK  ]',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid systemd[1]: Started LSB: Start the ipr init daemon.',
		'iprupdate.service - LSB: Start the iprupdate utility',
		'   Loaded: loaded (/etc/rc.d/init.d/iprupdate)',
		'   Active: active (running) since Di 2014-10-07 15:53:35 CEST; 4min 15s ago',
		'  Process: 525 ExecStart=/etc/rc.d/init.d/iprupdate start (code=exited, status=0/SUCCESS)',
		' Main PID: 567 (iprupdate)',
		'   CGroup: /system.slice/iprupdate.service',
		'           └─567 /sbin/iprupdate --daemon',
		'',
		'Okt 07 15:53:34 stb-40-srv-106.test.invalid systemd[1]: Starting LSB: Start the iprupdate utility...',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid iprupdate[525]: Starting iprupdate: [  OK  ]',
		'Okt 07 15:53:35 stb-40-srv-106.test.invalid systemd[1]: Started LSB: Start the iprupdate utility.',
		'Netconsole-Modul nicht geladen',
		'Konfigurierte Geräte:',
		'lo ens18',
		'Derzeit aktive Geräte:',
		'lo ens18',
	]

	assert set(["iprdump", "iprinit", "iprupdate"]) == Posix.getServiceNames(_serviceStatusOutput=output)


def testParsingSystemdOutputFromCentOS7():
	output = [
		'UNIT FILE                                   STATE   ',
		'proc-sys-fs-binfmt_misc.automount           static  ',
		'tmp.mount                                   disabled',
		'brandbot.path                               disabled',
		'systemd-ask-password-console.path           static  ',
		'session-1.scope                             static  ',
		'session-c2.scope                            static  ',
		'dhcpd.service                               disabled',
		'dhcpd6.service                              disabled',
		'getty@.service                              enabled ',
		'initrd-cleanup.service                      static  ',
		'smb.service                                 enabled ',
		'systemd-backlight@.service                  static  ',
		'-.slice                                     static  ',
		'machine.slice                               static  ',
		'syslog.socket                               static  ',
		'systemd-udevd-kernel.socket                 static  ',
		'basic.target                                static  ',
		'systemd-tmpfiles-clean.timer                static  ',
		'',
		'219 unit files listed.'
	]

	expectedServices = set([
		"dhcpd", "dhcpd6", "getty@", "initrd-cleanup", "smb",
		"systemd-backlight@"
	])
	assert expectedServices == Posix.getServiceNames(_serviceStatusOutput=output)


def testGetNetworkDeviceConfigFromNoDeviceRaisesAnException():
	with pytest.raises(Exception):
		Posix.getNetworkDeviceConfig(None)


def testGetNetworkDeviceConfigFromNewIfconfigOutput():
	"""
	Testing output from new version of ifconfig.

	This was obtained on CentOS 7.
	"""
	def fakeExecute(command):
		if command.startswith('ifconfig'):
			return [
				"eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500",
				"	inet 172.26.2.25  netmask 255.255.0.0  broadcast 172.26.255.255",
				"	inet6 fe80::215:5dff:fe01:151b  prefixlen 64  scopeid0x20<link>",
				"	ether 00:15:5d:01:15:1b  txqueuelen 1000  (thernet)",
				"	RX packets 12043  bytes 958928 (936.4 KiB)"
				"	RX errors 0  dropped 0  overruns 0  frame ",
				"	TX packets 1176  bytes 512566 (500.5 KiB)",
				"	TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0"
			]
		elif command.startswith('ip'):
			return []
		else:
			raise Exception("Ooops, unexpected code.")

	with mock.patch('OPSI.System.Posix.execute', fakeExecute):
		with mock.patch('OPSI.System.Posix.which', lambda cmd: cmd):
			config = Posix.getNetworkDeviceConfig('eth0')

	expectedConfig = {
		'device': 'eth0',
		'hardwareAddress': u'00:15:5d:01:15:1b',
		'gateway': None,
		'broadcast': u"172.26.255.255",
		'ipAddress': u"172.26.2.25",
		'netmask': u"255.255.0.0",
	}

	# The following values must but may not have a value.
	assert 'vendorId' in config
	assert 'deviceId' in config

	for key in expectedConfig:
		assert expectedConfig[key] == config[key], 'Key {key} differs: {0} vs. {1}'.format(expectedConfig[key], config[key], key=key)


def testGetNetworkDeviceConfigFromOldIfconfigOutput():
	def fakeExecute(command):
		if command.startswith('ifconfig'):
			return [
				"eth0      Link encap:Ethernet  Hardware Adresse 54:52:00:63:99:b3  ",
				"  inet Adresse:192.168.1.14  Bcast:192.168.255.255  Maske:255.255.0.0",
				"  inet6-Adresse: fe80::5652:ff:fe63:993b/64 Gültigkeitsbereich:Verbindung",
				"  UP BROADCAST RUNNING MULTICAST  MTU:1500  Metrik:1",
				"  RX packets:271140257 errors:0 dropped:0 overruns:0 frame:0",
				"  TX packets:181955440 errors:0 dropped:0 overruns:0 carrier:0",
				"  Kollisionen:0 Sendewarteschlangenlänge:1000 ",
				"  RX bytes:227870261729 (212.2 GiB)  TX bytes:926518540483 (862.8 GiB)"
			]
		elif command.startswith('ip'):
			return []
		else:
			raise Exception("Ooops, unexpected code.")

	with mock.patch('OPSI.System.Posix.execute', fakeExecute):
		with mock.patch('OPSI.System.Posix.which', lambda cmd: cmd):
			config = Posix.getNetworkDeviceConfig('eth0')

	expectedConfig = {
		'device': 'eth0',
		'gateway': None,
		'hardwareAddress': u'54:52:00:63:99:b3',
		'broadcast': u"192.168.255.255",
		'ipAddress': u"192.168.1.14",
		'netmask': u"255.255.0.0",
	}

	# The following values must exist but may not have a value.
	assert 'vendorId' in config
	assert 'deviceId' in config

	for key in expectedConfig:
		assert expectedConfig[key] == config[key], 'Key {key} differs: {0} vs. {1}'.format(expectedConfig[key], config[key], key=key)


def testGetEthernetDevicesOnDebianWheezy():
	@contextmanager
	def fakeReader(*args):
		def output():
			yield "Inter-|   Receive                                                |  Transmit"
			yield " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed"
			yield " vnet0: 135768236 1266823    0    0    0     0          0         0 2756215935 3204376    0    0    0     0       0          0"
			yield "    lo: 201420303 1045113    0    0    0     0          0         0 201420303 1045113    0    0    0     0       0          0"
			yield "   br0: 1603065924 7426776    0    2    0     0          0         0 10073037907 6616183    0    0    0     0       0          0"
			yield " vnet3: 122147784 1153388    0    0    0     0          0         0 2420527905 1758588    0    0    0     0       0          0"
			yield " vnet2: 124533117 1167654    0    0    0     0          0         0 2481424486 1796157    0    0    0     0       0          0"
			yield "  eth0: 4729787536 7116606    0    0    0     0          0         0 264028375 1534628    0    0    0     0       0          0"
			yield " vnet1: 125965483 1179479    0    0    0     0          0         0 2461937669 1800948    0    0    0     0       0          0"

		yield output()

	with mock.patch('__builtin__.open', fakeReader):
		devices = Posix.getEthernetDevices()
		assert 2 == len(devices)
		assert 'br0' in devices
		assert 'eth0' in devices


def testReadingUnpredictableNetworkInterfaceNames():
	"""
	We should be able to run on whatever distro that uses \
	Predictable Network Interface Names.

		What's this? What's this?
		There's something very wrong
		What's this?
		There's people singing songs
	"""
	@contextmanager
	def fakeReader(*args):
		def output():
			yield "Inter-|   Receive                                                |  Transmit"
			yield " face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed"
			yield " ens18:  130499    1836    0    0    0     0          0         0    34158     164    0    0    0     0       0          0"
			yield "    lo:       0       0    0    0    0     0          0         0        0       0    0    0    0     0       0          0"

		yield output()

	with mock.patch('__builtin__.open', fakeReader):
		devices = Posix.getEthernetDevices()
		assert 1 == len(devices)
		assert 'ens18' in devices


def testExecutingWithWaitForEndingWorks():
	"""
	waitForEnding must be an accepted keyword.

	This is to have the same keywords and behaviours on Windows and
	Linux.
	"""
	Posix.execute('echo bla', waitForEnding=True)


def testExecutingWithShellWorks():
	"""
	'shell' must be an accepted keyword.

	This is to have the same keywords and behaviours on Windows and
	Linux.
	"""
	Posix.execute('echo bla', shell=True)
