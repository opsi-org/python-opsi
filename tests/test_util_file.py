#!/usr/bin/env python
#-*- coding: utf-8 -*-

import os
import unittest

from OPSI.Util.File import IniFile, InfFile, TxtSetupOemFile


class ParseIniFileTestCase(unittest.TestCase):
    def test_parsing_does_not_fail(self):
        iniTestData = '''
#[section1]
# abc = def

[section2]
abc = def # comment

[section3]
key = value ;comment ; comment2

[section4]
key = value \; no comment \# comment2 ;# comment3

[section5]
key = \;\;\;\;\;\;\;\;\;\;\;\;
        '''

        iniFile = IniFile('filename_is_irrelevant_for_this')
        iniFile.parse(iniTestData.split('\n'))


class ParseInfFileTestCase(unittest.TestCase):
    def setUp(self):
        pathToConfig = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file', 'inf_testdata_8.inf')
        infFile = InfFile(pathToConfig)
        infFile.parse()
        self.devices = infFile.getDevices()

    def tearDown(self):
        del self.devices

    def testDevicesAreRead(self):
        devices = self.devices

        self.assertNotEqual(None, devices)
        self.assertNotEqual([], devices)
        self.assertTrue(bool(devices), 'No devices found.')

    def test_device_data_is_correct(self):
        devices = self.devices

        for dev in devices:
            self.assertNotEqual(None, dev['vendor'])
            self.assertNotEqual(None, dev['device'])


class SetupOemTestCase1(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_1.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        for (vendorId, deviceId) in (('10DE', '07F6'), ):
            self.assertTrue(
                self.txtSetupOemFile.isDeviceKnown(
                    vendorId=vendorId,
                    deviceId=deviceId
                ),
                'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
            )

            self.assertNotEqual(
                [],
                self.txtSetupOemFile.getFilesForDevice(
                    vendorId=vendorId,
                    deviceId=deviceId,
                    fileTypes=[]
                )
            )

            self.assertTrue(
                bool(
                    self.txtSetupOemFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)['description']
                )
            )

            self.txtSetupOemFile.applyWorkarounds()
            self.txtSetupOemFile.generate()

            self.assertNotEqual(
                [],
                self.txtSetupOemFile.getFilesForDevice(
                    vendorId=vendorId,
                    deviceId=deviceId,
                    fileTypes=[]
                )
            )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(None, device['vendor'])
            self.assertNotEqual(None, device['device'])


class SetupOemTestCase2(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_2.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        for (vendorId, deviceId) in (('10DE', '07F6'), ):
            self.assertFalse(
                self.txtSetupOemFile.isDeviceKnown(
                    vendorId=vendorId,
                    deviceId=deviceId
                ),
                'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
            )

            self.assertRaises(
                Exception,
                self.txtSetupOemFile.getFilesForDevice,
                vendorId=vendorId,
                deviceId=deviceId,
                fileTypes=[]
            )

            self.assertRaises(
                Exception,
                self.txtSetupOemFile.getComponentOptionsForDevice,
                vendorId=vendorId,
                deviceId=deviceId
            )

            self.txtSetupOemFile.applyWorkarounds()
            self.txtSetupOemFile.generate()

            self.assertRaises(
                Exception,
                self.txtSetupOemFile.getFilesForDevice,
                vendorId=vendorId,
                deviceId=deviceId,
                fileTypes=[]
            )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(None, device['vendor'])
            self.assertNotEqual(None, device['device'])


class SetupOemTestCase3(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_3.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        for (vendorId, deviceId) in (('10DE', '07F6'), ):
            self.assertTrue(
                self.txtSetupOemFile.isDeviceKnown(
                    vendorId=vendorId,
                    deviceId=deviceId
                ),
                'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
            )

            self.assertNotEqual(
                [],
                self.txtSetupOemFile.getFilesForDevice(
                    vendorId=vendorId,
                    deviceId=deviceId,
                    fileTypes=[]
                )
            )

            self.assertTrue(
                bool(
                    self.txtSetupOemFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)['description']
                )
            )

            self.txtSetupOemFile.applyWorkarounds()
            self.txtSetupOemFile.generate()

            self.assertNotEqual(
                [],
                self.txtSetupOemFile.getFilesForDevice(
                    vendorId=vendorId,
                    deviceId=deviceId,
                    fileTypes=[]
                )
            )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(None, device['vendor'])
            self.assertNotEqual(None, device['device'])


class SetupOemTestCase4(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_4.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingDataFromTextfile(self):
        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0AD4'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='0AD4',
            fileTypes=[]
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='07F6',
            fileTypes=[]
        )

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0754'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getComponentOptionsForDevice,
            vendorId='10DE',
            deviceId = '0AD4'
        )

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        (vendorId, deviceId) = ('1002', '4391')

        self.assertTrue(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId=vendorId,
                deviceId=deviceId
            ),
            'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
        )

        self.assertNotEqual(
            [],
            self.txtSetupOemFile.getFilesForDevice(
                vendorId=vendorId,
                deviceId=deviceId,
                fileTypes=[]
            )
        )

        self.assertTrue(
            bool(
                self.txtSetupOemFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)['description']
            )
        )

        self.txtSetupOemFile.applyWorkarounds()
        self.txtSetupOemFile.generate()

        self.assertNotEqual(
            [],
            self.txtSetupOemFile.getFilesForDevice(
                vendorId=vendorId,
                deviceId=deviceId,
                fileTypes=[]
            )
        )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(
                None,
                device['vendor'],
                'The vendor should be set but isn\'t: {0}'.format(device))
            self.assertNotEqual(None, device['device'])


class SetupOemTestCase5(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_5.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingDataFromTextfile(self):
        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0AD4'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='07F6',
            fileTypes=[]
        )

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0754'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getComponentOptionsForDevice,
            vendorId='10DE',
            deviceId = '0AD4'
        )

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        vendorId, deviceId = ('10DE', '07F6')

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId=vendorId,
                deviceId=deviceId
            ),
            'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId=vendorId,
            deviceId=deviceId,
            fileTypes=[]
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getComponentOptionsForDevice,
            vendorId=vendorId,
            deviceId=deviceId
        )

        self.txtSetupOemFile.applyWorkarounds()
        self.txtSetupOemFile.generate()

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId=vendorId,
            deviceId=deviceId,
            fileTypes=[]
        )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(
                None,
                device['vendor'],
                'The vendor should be set but isn\'t: {0}'.format(device))
            self.assertEqual('fttxr5_O', device['serviceName'])


class SetupOemTestCase6(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_6.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingDataFromTextfile(self):
        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0AD4'
            )
        )

        self.assertRaises(Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='0AD4',
            fileTypes=[]
        )

        self.assertRaises(
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='07F6',
            fileTypes=[]
        )

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0754'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getComponentOptionsForDevice,
            vendorId='10DE',
            deviceId = '0AD4'
        )

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        (vendorId, deviceId) = ('10DE', '07F6')

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId=vendorId,
                deviceId=deviceId
            ),
            'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
        )

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(None, device['vendor'])
            self.assertNotEqual(None, device['device'])


class SetupOemTestCase7(unittest.TestCase):
    def setUp(self):
        oemSetupFile = os.path.join(os.path.dirname(__file__), 'testdata',
                                    'util', 'file',
                                    'txtsetupoem_testdata_7.oem')

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    def tearDown(self):
        del self.txtSetupOemFile

    def testDevicesAreRead(self):
        devices = self.txtSetupOemFile.getDevices()

        self.assertTrue(bool(devices), 'No devices found!')

    def testReadingDataFromTextfile(self):
        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0AD4'
            )
        )

        self.assertRaises(Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='0AD4',
            fileTypes=[]
        )

        self.assertRaises(Exception,
            self.txtSetupOemFile.getFilesForDevice,
            vendorId='10DE',
            deviceId='07F6',
            fileTypes=[]
        )

        self.assertFalse(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId='10DE',
                deviceId = '0754'
            )
        )

        self.assertRaises(
            Exception,
            self.txtSetupOemFile.getComponentOptionsForDevice,
            vendorId='10DE',
            deviceId = '0AD4'
        )

    def testReadingInSpecialDevicesAndApplyingFixes(self):
        (vendorId, deviceId) = ('8086', '3B22')

        self.assertTrue(
            self.txtSetupOemFile.isDeviceKnown(
                vendorId=vendorId,
                deviceId=deviceId
            ),
            'No device found for vendor "{0}" and device ID "{1}"'.format(vendorId, deviceId)
        )

        filesBeforeWorkarounds = self.txtSetupOemFile.getFilesForDevice(
            vendorId=vendorId,
            deviceId=deviceId,
            fileTypes=[]
        )
        self.assertNotEqual([],filesBeforeWorkarounds)

        self.assertNotEqual(
            '',
            self.txtSetupOemFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)['description']
        )

        self.txtSetupOemFile.applyWorkarounds()
        self.txtSetupOemFile.generate()

        filesAfterWorkarounds = self.txtSetupOemFile.getFilesForDevice(
            vendorId=vendorId,
            deviceId=deviceId,
            fileTypes=[]
        )

        self.assertNotEqual([], filesAfterWorkarounds)
        self.assertEqual(filesBeforeWorkarounds, filesAfterWorkarounds)

    def testGenerationDoesNotFail(self):
        self.txtSetupOemFile.generate()

    def testDevicesContents(self):
        devices = self.txtSetupOemFile.getDevices()

        for device in devices:
            self.assertNotEqual(None, device['vendor'])
            self.assertNotEqual(None, device['device'])


if __name__ == '__main__':
    unittest.main()
