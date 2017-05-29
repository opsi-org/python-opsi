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
Testing OPSI.Util.File.Opsi

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""
from __future__ import absolute_import

import os

import pytest

from OPSI.Util.File.Opsi import BackendDispatchConfigFile, OpsiConfFile, PackageControlFile
from .helpers import createTemporaryTestfile


def testReadingAllUsedBackends():
	exampleConfig = '''
backend_.*         : file, mysql, opsipxeconfd, dhcpd
host_.*            : file, mysql, opsipxeconfd, dhcpd
productOnClient_.* : file, mysql, opsipxeconfd
configState_.*     : file, mysql, opsipxeconfd
license.*          : mysql
softwareLicense.*  : mysql
audit.*            : mysql
.*                 : mysql
'''

	dispatchConfig = BackendDispatchConfigFile('not_reading_file')

	assert set(('file', 'mysql', 'opsipxeconfd', 'dhcpd')) == dispatchConfig.getUsedBackends(lines=exampleConfig.split('\n'))


def testParsingIgnoresCommentedLines():
	exampleConfig = '''
;backend_.*.*  : fail
	#audit.*            : fail
		.*                 : yolofile
'''

	dispatchConfig = BackendDispatchConfigFile('not_reading_file')
	usedBackends = dispatchConfig.getUsedBackends(lines=exampleConfig.split('\n'))

	assert 'fail' not in usedBackends
	assert set(('yolofile',)), usedBackends


def testBackendDispatchConfigFileNotFailingOnInvalidLines():
	"""
	Reading invalid lines in a config must not lead to an exception.
	"""
	exampleConfig = '''
this does not work
'''

	dispatchConfig = BackendDispatchConfigFile('not_reading_file')
	dispatchConfig.parse(lines=exampleConfig.split('\n'))


def testBackendDispatchConfigFileBackendsCanBeEmpty():
	exampleConfig = '''
no_backends_follow:\t
empty_backends:\t, ,
'''

	dispatchConfig = BackendDispatchConfigFile('not_reading_file')
	result = dispatchConfig.parse(lines=exampleConfig.split('\n'))

	assert 1 == len(result)
	regex, backends = result[0]
	assert 'empty_backends' == regex
	assert tuple() == backends


@pytest.fixture
def opsiConfigFile():
	path = os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'file', 'opsi', 'opsi.conf')
	return OpsiConfFile(filename=path)


def testReadingFileAdminGroupReturnsLowercaseName(opsiConfigFile):
	assert 'mypcpatch' == opsiConfigFile.getOpsiFileAdminGroup()


def testReturningDefaultForFileAdminGroup(opsiConfigFile):
	opsiConfigFile.parse([''])
	assert 'pcpatch' == opsiConfigFile.getOpsiFileAdminGroup()


def testReadingReadonlyGroups(opsiConfigFile):
	assert ['myopsireadonlys'] == opsiConfigFile.getOpsiGroups("readonly")


def testGettingDefaultForReadonlyGroups(opsiConfigFile):
	opsiConfigFile.parse([''])
	assert opsiConfigFile.getOpsiGroups("readonly") is None


def testReadingPigzStatus(opsiConfigFile):
	assert not opsiConfigFile.isPigzEnabled()


def testGettingDefaultPigzStatus(opsiConfigFile):
	opsiConfigFile.parse([''])
	assert opsiConfigFile.isPigzEnabled()


@pytest.fixture
def opsiControlFilePath():
	# The file is the one that was causing a problem in
	# https://forum.opsi.org/viewtopic.php?f=7&t=7907
	return os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'file', 'opsi', 'control_with_german_umlauts'
	)


def testParsingControlFileWithGermanUmlautsInDescription(opsiControlFilePath):
	p = PackageControlFile(opsiControlFilePath)
	p.parse()

	product = p.getProduct()
	assert u'Startet die Druckerwarteschlange auf dem Client neu / oder überhaupt.' == product.description


def testProductControlFileWithoutVersionUsesDefaults():
	filename = os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'file', 'opsi', 'control_without_versions')

	pcf = PackageControlFile(filename)

	product = pcf.getProduct()

	assert '1' == product.packageVersion
	assert '1.0' == product.productVersion


@pytest.fixture
def controlFileWithEmptyValues():
	filePath = os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'file', 'opsi', 'control_with_empty_property_values')

	with createTemporaryTestfile(filePath) as newFilePath:
		yield newFilePath


def testParsingProductControlFileContainingPropertyWithEmptyValues(controlFileWithEmptyValues):
	pcf = PackageControlFile(controlFileWithEmptyValues)

	properties = pcf.getProductProperties()
	assert len(properties) == 1

	testProperty = properties[0]
	assert testProperty.propertyId == 'important'
	assert testProperty.possibleValues == []
	assert testProperty.defaultValues == []
	assert testProperty.multiValue is False
	assert testProperty.editable is True
	assert testProperty.description == "Nothing is important."


def testGeneratingProductControlFileContainingPropertyWithEmptyValues(controlFileWithEmptyValues):
	pcf = PackageControlFile(controlFileWithEmptyValues)
	pcf.parse()
	pcf.generate()
	pcf.generate()  # should destroy nothing
	pcf.close()
	del pcf

	pcf = PackageControlFile(controlFileWithEmptyValues)
	properties = pcf.getProductProperties()
	assert len(properties) == 1

	testProperty = properties[0]
	assert testProperty.propertyId == 'important'
	assert testProperty.possibleValues == []
	assert testProperty.defaultValues == []
	assert testProperty.multiValue is False
	assert testProperty.editable is True
	assert testProperty.description == "Nothing is important."


@pytest.fixture
def specialCharacterControlFile():
	filePath = os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'file', 'opsi',
		'control_with_special_characters_in_property')

	with createTemporaryTestfile(filePath) as newFilePath:
		yield newFilePath


def testGeneratingProductControlFileContainingSpecialCharactersInProperty(specialCharacterControlFile):
	pcf = PackageControlFile(specialCharacterControlFile)
	pcf.parse()
	pcf.generate()
	pcf.generate()  # should destroy nothing
	pcf.close()
	del pcf

	pcf = PackageControlFile(specialCharacterControlFile)
	properties = pcf.getProductProperties()
	assert len(properties) == 1

	testProperty = properties[0]
	assert testProperty.propertyId == 'target_path'
	assert testProperty.possibleValues == ["C:\\temp\\my_target"]
	assert testProperty.defaultValues == ["C:\\temp\\my_target"]
	assert testProperty.multiValue is False
	assert testProperty.editable is True
	assert testProperty.description == "The target path"
