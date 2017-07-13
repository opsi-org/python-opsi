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

from OPSI.Util import findFiles, md5sum
from OPSI.Util.File.Opsi import (
	BackendDispatchConfigFile, OpsiConfFile, PackageContentFile,
	PackageControlFile)

from .helpers import createTemporaryTestfile, workInTemporaryDirectory


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
	assert len(properties) == 2

	if properties[0].propertyId == 'target_path':
		testProperty = properties.pop(0)
	else:
		testProperty = properties.pop()

	assert testProperty.propertyId == 'target_path'
	assert testProperty.description == "The target path"
	assert testProperty.multiValue is False
	assert testProperty.editable is True
	assert testProperty.possibleValues == ["C:\\temp\\my_target"]
	assert testProperty.defaultValues == ["C:\\temp\\my_target"]

	testProperty = properties.pop()
	assert testProperty.propertyId == 'adminaccounts'
	assert testProperty.description == "Windows account(s) to provision as administrators."
	assert testProperty.multiValue is False
	assert testProperty.editable is True
	assert testProperty.defaultValues == ["Administrator"]
	assert set(testProperty.possibleValues) == set(["Administrator", "domain.local\\Administrator", "BUILTIN\\ADMINISTRATORS"])


@pytest.fixture
def outsideFile():
	with workInTemporaryDirectory() as anotherDirectory:
		outsideFile = os.path.join(anotherDirectory, 'joan')
		with open(outsideFile, 'w') as externalFile:
			externalFile.write("Watson, are you here?")

		yield outsideFile


@pytest.fixture
def outsideDir():
	with workInTemporaryDirectory() as tmpDir:
		dirPath = os.path.join(tmpDir, 'dirOutside')
		os.mkdir(dirPath)

		yield dirPath


def testPackageContentFileCreation(outsideFile, outsideDir):
	with workInTemporaryDirectory() as tempDir:
		content = fillDirectory(tempDir)

		outsideLink = 'jlink'
		assert outsideLink not in content
		for filename in (f for f, t in content.items() if t == 'f'):
			os.symlink(outsideFile, os.path.join(tempDir, outsideLink))
			content[outsideLink] = 'f'
			break

		outsideDirLink = 'dlink'
		assert outsideDirLink not in content
		for dirname in (f for f, t in content.items() if t == 'd'):
			os.symlink(outsideDir, os.path.join(tempDir, outsideDirLink))
			content[outsideDirLink] = 'd'
			break

		clientDataFiles = findFiles(tempDir)

		filename = os.path.join(tempDir, 'test.files')
		contentFile = PackageContentFile(filename)
		contentFile.setProductClientDataDir(tempDir)
		contentFile.setClientDataFiles(clientDataFiles)
		contentFile.generate()

		assert os.path.exists(filename)
		assert os.path.getsize(filename) > 10, 'Generated file is empty!'

		# Manual parsing of the file contents to ensure that the
		# format matches our requirements.
		with open(filename) as generatedFile:
			for line in generatedFile:
				try:
					entry, path, size = line.split(' ', 2)

					path = path.strip("'")
					assert entry == content.pop(path), "Type mismatch!"

					if path == outsideLink:
						assert entry == 'f'
					elif path == outsideDirLink:
						assert entry == 'd'

					if entry == 'd':
						assert int(size.strip()) == 0
					elif entry == 'f':
						size, hashSum = size.split(' ', 1)

						assert os.path.getsize(path) == int(size)

						assert not hashSum.startswith("'")
						assert not hashSum.endswith("'")
						hashSum = hashSum.strip()
						assert md5sum(path) == hashSum
					elif entry == 'l':
						size, target = size.split(' ', 1)

						assert int(size) == 0

						target = target.strip()
						assert target.startswith("'")
						assert target.endswith("'")
						target = target.strip("'")
						assert target
					else:
						raise RuntimeError("Unexpected type {0!r}".format(entry))
				except Exception:
					print("Processing line {0!r} failed".format(line))
					raise

		assert not content, "Files not listed in content file: {0}".format(', '.join(content))


def fillDirectory(directory):
	assert os.path.exists(directory)

	directories = [
		('subdir', ),
		('subdir', 'sub1'),
	]

	files = [
		(('simplefile', ), 'I am an very simple file\nFor real!'),
		(('subdir', 'fileinsub1'), 'Subby one'),
		(('subdir', 'fileinsub2'), 'Subby two'),
		(('subdir', 'sub1', 'simplefile2'), 'Sub in a sub.\nThanks, no cheese!'),
	]

	links = [
		(('simplefile', ), ('simplelink', )),
		(('subdir', 'sub1', 'simplefile2'), ('goingdown', )),
	]

	content = {}

	for dirPath in directories:
		os.mkdir(os.path.join(directory, *dirPath))
		content[os.path.join(*dirPath)] = 'd'

	for filePath, text in files:
		with open(os.path.join(directory, *filePath), 'w') as fileHandle:
			fileHandle.write(text)

		content[os.path.join(*filePath)] = 'f'

	for source, name in links:
		os.symlink(os.path.join(directory, *source), os.path.join(directory, *name))
		content[os.path.join(*name)] = 'l'

	return content


def testParsingPackageContentFile(outsideFile, outsideDir):
	with workInTemporaryDirectory() as tempDir:
		content = fillDirectory(tempDir)

		outsideLink = 'jlink'
		assert outsideLink not in content
		for filename in (f for f, t in content.items() if t == 'f'):
			os.symlink(outsideFile, os.path.join(tempDir, outsideLink))
			content[outsideLink] = 'f'
			break

		outsideDirLink = 'dlink'
		assert outsideDirLink not in content
		for dirname in (f for f, t in content.items() if t == 'd'):
			os.symlink(outsideDir, os.path.join(tempDir, outsideDirLink))
			content[outsideDirLink] = 'd'
			break

		filename = os.path.join(tempDir, 'test.files')
		contentFile = PackageContentFile(filename)
		contentFile.setProductClientDataDir(tempDir)
		clientDataFiles = findFiles(tempDir)
		contentFile.setClientDataFiles(clientDataFiles)
		contentFile.generate()
		del contentFile

		# Checking the parsing feature of PackageContentFile
		readContentFile = PackageContentFile(filename)
		contents = readContentFile.parse()
		assert len(contents) == len(content)

		for filename, entry in contents.items():
			assert filename
			assert not filename.startswith("'")
			assert not filename.endswith("'")

			entryType = entry['type']
			assert entryType == content[filename]

			if entryType == 'd':
				assert entry['size'] == 0
				assert entry['md5sum'] == ''
				assert entry['target'] == ''
			elif entryType == 'f':
				assert entry['size'] > 0
				hashSum = entry['md5sum']
				assert hashSum
				assert not hashSum.startswith("'")
				assert not hashSum.endswith("'")
				assert entry['target'] == ''
			elif entryType == 'l':
				assert entry['size'] == 0
				assert not entry['md5sum']
				target = entry['target']
				assert target
				assert not target.startswith("'")
				assert not target.endswith("'")
			else:
				raise RuntimeError("Unexpected type in {0!r}".format(entry))
