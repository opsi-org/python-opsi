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
Testing OPSI.Util.File

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os
import shutil
from contextlib import contextmanager

from OPSI.Util.File import IniFile, InfFile, TxtSetupOemFile, ZsyncFile

from .helpers import copyTestfileToTemporaryFolder, workInTemporaryDirectory

import pytest


def testParsingIniFileDoesNotFail():
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


@pytest.fixture(params=[
    'inf_testdata_1.inf',
    'inf_testdata_2.inf',
    'inf_testdata_3.inf',
    'inf_testdata_4.inf',
    'inf_testdata_5.inf',
    'inf_testdata_6.inf',
    'inf_testdata_7.inf',
    'inf_testdata_8.inf',
])
def infFile(request):
    yield InfFile(getAbsolutePathToTestData(request.param))


def testDeviceDataIsReadFromInfFile(infFile):
    infFile.parse()

    devices = infFile.getDevices()
    assert devices

    for dev in devices:
        assert dev['vendor']
        assert dev['device']


def testTxtSetupOemFileParseAndGenerateDoesNotFail(txtSetupOemFileInTempDirectory):
    txtSetupOemFileInTempDirectory.parse()

    txtSetupOemFileInTempDirectory.generate()


@pytest.fixture
def txtSetupOemFileInTempDirectory(txtSetupOemFilePath):
    with getTempTxtSetupOemFileFromPath(txtSetupOemFilePath) as setupFile:
        yield setupFile


@contextmanager
def getTempTxtSetupOemFileFromPath(filePath):
    with workInTemporaryDirectory() as tempDir:
        shutil.copy(filePath, tempDir)

        filename = os.path.basename(filePath)

        newPath = os.path.join(tempDir, filename)
        yield TxtSetupOemFile(newPath)


def txtSetupOemFileNames():
    yield 'txtsetupoem_testdata_1.oem'
    yield 'txtsetupoem_testdata_2.oem'
    yield 'txtsetupoem_testdata_3.oem'
    yield 'txtsetupoem_testdata_4.oem'
    yield 'txtsetupoem_testdata_5.oem'
    yield 'txtsetupoem_testdata_6.oem'
    yield 'txtsetupoem_testdata_7.oem'


@pytest.fixture(params=[f for f in txtSetupOemFileNames()])
def txtSetupOemFilePath(request):
    yield getAbsolutePathToTestData(request.param)


def getAbsolutePathToTestData(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'file', filename)


@pytest.fixture
def regeneratedtxtSetupOemFileWithWorkarounds(txtSetupOemFileInTempDirectory):
    txtSetupOemFile = txtSetupOemFileInTempDirectory
    txtSetupOemFile.parse()
    txtSetupOemFile.applyWorkarounds()
    txtSetupOemFile.generate()

    yield txtSetupOemFile


def testTxtSetupOemFileApplyingWorkaroundsRemovesComments(regeneratedtxtSetupOemFileWithWorkarounds):
    comment_chars = (';', '#')

    with open(regeneratedtxtSetupOemFileWithWorkarounds.getFilename()) as setupfile:
        for line in setupfile:
            assert not line.startswith(comment_chars)


def testTxtSetupOemFileApplyingWorkaroundsCreatesDisksSection(regeneratedtxtSetupOemFileWithWorkarounds):
    assert _sectionExists(regeneratedtxtSetupOemFileWithWorkarounds.getFilename(), '[Disks]')


def _sectionExists(filepath, sectionName):
    with open(filepath) as setupfile:
        return any(sectionName in line for line in setupfile)


def testTxtSetupOemFileApplyingWorkaroundsCreatesDefaultsSection(regeneratedtxtSetupOemFileWithWorkarounds):
    assert _sectionExists(regeneratedtxtSetupOemFileWithWorkarounds.getFilename(), '[Defaults]')


def testTxtSetupOemFileCommasAreFollowdBySpace(regeneratedtxtSetupOemFileWithWorkarounds):
    with open(regeneratedtxtSetupOemFileWithWorkarounds.getFilename()) as setupfile:
        for line in setupfile:
            if ',' in line:
                commaIndex = line.index(',')
                assert ' ' == line[commaIndex + 1]


def testTxtSetupOemFileApplyingWorkaroundsChangesContents(txtSetupOemFileInTempDirectory):
    with open(txtSetupOemFileInTempDirectory.getFilename()) as setupfile:
        before = setupfile.readlines()

    txtSetupOemFileInTempDirectory.parse()
    txtSetupOemFileInTempDirectory.applyWorkarounds()
    txtSetupOemFileInTempDirectory.generate()

    with open(txtSetupOemFileInTempDirectory.getFilename()) as setupfile:
        after = setupfile.readlines()

    assert before != after


class CopySetupOemFileTestsMixin(object):
    TEST_DATA_FOLDER = os.path.join(
        os.path.dirname(__file__), 'testdata', 'util', 'file',
    )
    ORIGINAL_SETUP_FILE = None

    @classmethod
    def setUpClass(self):
        oemSetupFile = copyTestfileToTemporaryFolder(
            os.path.join(self.TEST_DATA_FOLDER, self.ORIGINAL_SETUP_FILE)
        )

        self.txtSetupOemFile = TxtSetupOemFile(oemSetupFile)
        self.txtSetupOemFile.parse()

    @classmethod
    def tearDownClass(self):
        testDirectory = os.path.dirname(self.txtSetupOemFile.getFilename())
        if os.path.normpath(self.TEST_DATA_FOLDER) != os.path.normpath(testDirectory):
            try:
                shutil.rmtree(testDirectory)
            except OSError:
                pass

        del self.txtSetupOemFile


@pytest.mark.parametrize("filename, vendorId, deviceId", [
    ('txtsetupoem_testdata_1.oem', '10DE', '07F6'),
    ('txtsetupoem_testdata_3.oem', '10DE', '07F6'),
    ('txtsetupoem_testdata_4.oem', '1002', '4391'),
    ('txtsetupoem_testdata_7.oem', '8086', '3B22'),
])
def testReadingInExistingSpecialDevicesAndApplyingFixes(filename, vendorId, deviceId):
    absFile = getAbsolutePathToTestData(filename)

    with getTempTxtSetupOemFileFromPath(absFile) as setupFile:
        assert setupFile.isDeviceKnown(vendorId=vendorId, deviceId=deviceId)

        assert [] != setupFile.getFilesForDevice(vendorId=vendorId, deviceId=deviceId, fileTypes=[])

        assert setupFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)['description']

        setupFile.applyWorkarounds()
        setupFile.generate()

        assert [] != setupFile.getFilesForDevice(vendorId=vendorId, deviceId=deviceId, fileTypes=[])


@pytest.mark.parametrize("filename, vendorId, deviceId", [
    ('txtsetupoem_testdata_2.oem', '10DE', '07F6'),
    ('txtsetupoem_testdata_5.oem', '10DE', '07F6'),
    ('txtsetupoem_testdata_6.oem', '10DE', '07F6'),
])
def testCheckingForMissingVendorAndDevices(filename, vendorId, deviceId):
    absFile = getAbsolutePathToTestData(filename)

    with getTempTxtSetupOemFileFromPath(absFile) as setupFile:
        assert not setupFile.isDeviceKnown(vendorId=vendorId, deviceId=deviceId)

        with pytest.raises(Exception):
            setupFile.getFilesForDevice(vendorId=vendorId, deviceId=deviceId, fileTypes=[])

        with pytest.raises(Exception):
            setupFile.getComponentOptionsForDevice(vendorId=vendorId, deviceId=deviceId)

        setupFile.applyWorkarounds()
        setupFile.generate()

        with pytest.raises(Exception):
            setupFile.getFilesForDevice(vendorId=vendorId, deviceId=deviceId, fileTypes=[])


@pytest.mark.parametrize("filename", [
    'txtsetupoem_testdata_1.oem',
    'txtsetupoem_testdata_2.oem',
    'txtsetupoem_testdata_3.oem',
    'txtsetupoem_testdata_4.oem',
    'txtsetupoem_testdata_6.oem',
    'txtsetupoem_testdata_7.oem',
])
def testDevicesInTxtSetupOemFileHaveVendorAndDeviceId(filename):
    absFile = getAbsolutePathToTestData(filename)

    with getTempTxtSetupOemFileFromPath(absFile) as setupFile:
        devices = setupFile.getDevices()

        assert devices

        for device in devices:
            assert device['vendor']
            assert device['device']


@pytest.mark.parametrize("filename", ['txtsetupoem_testdata_5.oem'])
def testReadingDevicesContents(filename):
    absFile = getAbsolutePathToTestData(filename)

    with getTempTxtSetupOemFileFromPath(absFile) as setupFile:
        for device in setupFile.getDevices():
            assert device['vendor']
            assert 'fttxr5_O' == device['serviceName']


@pytest.mark.parametrize("filename", [
    pytest.mark.xfail('txtsetupoem_testdata_1.oem'),
    'txtsetupoem_testdata_2.oem',
    pytest.mark.xfail('txtsetupoem_testdata_3.oem'),
    'txtsetupoem_testdata_4.oem',
    'txtsetupoem_testdata_5.oem',
    'txtsetupoem_testdata_6.oem',
    'txtsetupoem_testdata_7.oem'
])
def testReadingDataFromTextfileOemSetup(filename):
    absFile = getAbsolutePathToTestData(filename)

    with getTempTxtSetupOemFileFromPath(absFile) as setupFile:
        assert not setupFile.isDeviceKnown(vendorId='10DE', deviceId='0AD4')

        with pytest.raises(Exception):
            setupFile.getFilesForDevice(vendorId='10DE', deviceId='0AD4', fileTypes=[])

        with pytest.raises(Exception):
            setupFile.getFilesForDevice(vendorId='10DE', deviceId='07F6', fileTypes=[])

        assert not setupFile.isDeviceKnown(vendorId='10DE', deviceId='0754')

        with pytest.raises(Exception):
            setupFile.getComponentOptionsForDevice(vendorId='10DE', deviceId='0AD4')


def testZsyncFile(tempDir):
    filename = 'opsi-configed_4.0.7.1.3-2.opsi.zsync'
    expectedHeaders = {
        'Blocksize': '2048',
        'Filename': 'opsi-configed_4.0.7.1.3-2.opsi',
        'Hash-Lengths': '2,2,5',
        'Length': '9574912',
        'SHA-1': '702afc14c311ce9e4083c893c9ac4f4390413ae9',
        'URL': 'opsi-configed_4.0.7.1.3-2.opsi',
        'zsync': '0.6.2',
    }

    def checkZsyncFile(zf):
        assert zf._data
        assert zf._header

        for key, value in expectedHeaders.items():
            assert zf._header[key] == value

        assert 'mtime' not in zf._header

    shutil.copy(os.path.join(os.path.dirname(__file__), 'testdata',
                'util', 'file', filename), tempDir)

    testFile = os.path.join(tempDir, filename)

    zf = ZsyncFile(testFile)
    assert not zf._parsed
    zf.parse()
    checkZsyncFile(zf)

    zf._header['mtime'] = 'should not be written'
    zf.generate()
    zf.close()
    del zf

    zf = ZsyncFile(testFile)
    zf.parse()
    checkZsyncFile(zf)
