# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing certificate creation and renewal.
"""

import os
import shutil

import pytest

from OPSI.Types import forceHostId
from OPSI.Util import getfqdn, randomString
from OPSI.Util.Task.Certificate import (
	NoCertificateError, CertificateCreationError, UnreadableCertificateError,
	createCertificate, loadConfigurationFromCertificate, renewCertificate)


@pytest.fixture
def pathToTempFile(tempDir):
	yield os.path.join(tempDir, randomString(8))


def testCertificateFileExistsAfterCreation(pathToTempFile):
	assert not os.path.exists(pathToTempFile)

	createCertificate(pathToTempFile)
	assert os.path.exists(pathToTempFile)


@pytest.fixture
def customConfig():
	hostname = forceHostId(getfqdn())
	yield {
		'organizationalUnit': u'asdf',
		'expires': 3,
		'commonName': hostname,
		'country': u'ZZ',  # Top
		'state': u'HE',
		'locality': u'Breidenbach',
		'organization': u'Unittest',
		'emailAddress': u'no@address.internet',
		'serialNumber': 1010,
	}


def testCertificateWasCreatedWithConfigValues(pathToTempFile, customConfig):
	createCertificate(pathToTempFile, config=customConfig)
	loadedConfig = loadConfigurationFromCertificate(pathToTempFile)

	del customConfig['expires']  # written as date to config
	customConfig['serialNumber'] += 1  # incremented

	assert customConfig == loadedConfig


def testCertificateCreationWithoutValidExpireDateRaisesException(customConfig):
	customConfig['expires'] = u'hallo welt'

	with pytest.raises(CertificateCreationError):
		createCertificate(config=customConfig)


def testCertificateCreationWithForeignHostnameRaisesException(customConfig):
	customConfig['commonName'] = u'this-should-not-be-hostname'

	with pytest.raises(CertificateCreationError):
		createCertificate(config=customConfig)


@pytest.mark.parametrize("value", ['organizationalUnit', 'emailAddress'])
def testCertificateCreationWorksWithoutSomeValues(value, pathToTempFile, customConfig):
	del customConfig[value]
	createCertificate(pathToTempFile, config=customConfig)

	assert os.path.exists(pathToTempFile)


@pytest.mark.parametrize("value", [None, ''])
@pytest.mark.parametrize("key", ['organizationalUnit', 'emailAddress'])
def testCertificateCreationWorksWithoutSomeEmptyvalues(key, value, pathToTempFile, customConfig):
	customConfig[key] = value

	createCertificate(pathToTempFile, config=customConfig)

	assert os.path.exists(pathToTempFile)


def testLoadingCertificateConfigFromFile():
	certPath = getAbsolutePathToTestCert('example.pem')
	certparams = loadConfigurationFromCertificate(certPath)

	assert 'DE' == certparams["country"]
	assert 'RP' == certparams["state"]
	assert 'Mainz' == certparams["locality"]
	assert 'UIB' == certparams["organization"]
	assert 'test' == certparams["organizationalUnit"]
	assert 'niko-linux' == certparams["commonName"]
	assert 'info@uib.de' == certparams["emailAddress"]
	assert 18428462229954092504 == certparams["serialNumber"]


def testLoadingConfigurationFailsIfNoFileFound():
	filename = 'nofile'
	assert not os.path.exists(filename)
	with pytest.raises(NoCertificateError):
		loadConfigurationFromCertificate(filename)


@pytest.mark.parametrize("filename", ['invalid.pem', 'corrupt.pem'])
def testLoadingConfigurationFromInvalidFileRaisesError(filename):
	filePath = getAbsolutePathToTestCert(filename)

	with pytest.raises(UnreadableCertificateError):
		loadConfigurationFromCertificate(filePath)


def getAbsolutePathToTestCert(filename):
	return os.path.join(os.path.dirname(__file__),
						'testdata', 'util', 'task', 'certificate', filename)


def testCertificateRenewalFailsOnMissingFile():
	with pytest.raises(NoCertificateError):
		renewCertificate('nofile')


def testCertificateFileAfterRenewal(tempDir):
	exampleCertificate = getAbsolutePathToTestCert('example.pem')

	certificate_folder = tempDir
	shutil.copy(exampleCertificate, certificate_folder)
	certificate_path = os.path.join(certificate_folder, 'example.pem')
	assert os.path.exists(certificate_path)

	old_config = loadConfigurationFromCertificate(certificate_path)

	configForCreating = old_config
	configForCreating['commonName'] = forceHostId(getfqdn())
	renewCertificate(path=certificate_path, config=configForCreating)

	assert os.path.exists(certificate_path)
	backupFile = '{file}.bak'.format(file=certificate_path)
	assert os.path.exists(backupFile), u"Missing backup-file!"

	new_config = loadConfigurationFromCertificate(certificate_path)

	keysToCompare = ('organizationalUnit', 'commonName', 'country',
					 'state', 'locality', 'organization',
					 'emailAddress')

	for key in keysToCompare:
		assert old_config[key] == new_config[key], (
			u"Difference at key {0!r} between old and new: {1!r} vs. {2!r}".format(
				key, old_config[key], new_config[key]
			)
		)

	assert old_config['serialNumber'] != new_config['serialNumber']
