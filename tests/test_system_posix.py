#!/usr/bin/env python
#-*- coding: utf-8 -*-

import unittest

from OPSI.System.Posix import getBlockDeviceContollerInfo


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


if __name__ == '__main__':
    unittest.main()
