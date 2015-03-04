#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2015 uib GmbH <info@uib.de>

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

from __future__ import unicode_literals

import os
import tempfile
import unittest
from OPSI.Types import forceHostId
from OPSI.Util import getfqdn
from OPSI.Util.Task.Certificate import (NoCertificateError,
    CertificateCreationError, UnreadableCertificateError, createCertificate,
    loadConfigurationFromCertificate)


class CertificateCreationTestCase(unittest.TestCase):
    def setUp(self):
        self.certificate_path = tempfile.mkstemp()[1]

        createCertificate(self.certificate_path)

    def tearDown(self):
        if os.path.exists(self.certificate_path):
            os.remove(self.certificate_path)

        del self.certificate_path

    def testCertificateFileExists(self):
        self.assertTrue(os.path.exists(self.certificate_path))


class CertificateCreationWithConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.certificate_path = tempfile.mkstemp()[1]

        hostname = forceHostId(getfqdn())
        self.nonDefaultConfig = {
            'organizationalUnit': 'asdf',
            'expires': 3,
            'commonName': hostname,
            'country': 'ZZ',  # Top
            'state': 'HE',
            'locality': 'Breidenbach',
            'organization': 'Unittest',
            'emailAddress': 'no@address.internet',
            'serialNumber': 1010,
        }

    def tearDown(self):
        if os.path.exists(self.certificate_path):
            os.remove(self.certificate_path)

        del self.certificate_path
        del self.nonDefaultConfig

    def testCertificateWasCreatedWithConfigValues(self):
        createCertificate(self.certificate_path, config=self.nonDefaultConfig)
        loadedConfig = loadConfigurationFromCertificate(self.certificate_path)

        del self.nonDefaultConfig['expires']  # written as date to config
        self.nonDefaultConfig['serialNumber'] += 1  # incremented

        self.assertEquals(self.nonDefaultConfig, loadedConfig)

    def testCertificateCreationWithoutValidExpireDateRaisesException(self):
        self.assertRaises(CertificateCreationError, createCertificate, config={'expires': 'hallo welt'})

    def testCertificateCreationWithForeignHostnameRaisesException(self):
        self.nonDefaultConfig['commonName'] = 'this-should-not-be-hostname'
        self.assertRaises(CertificateCreationError, createCertificate, config=self.nonDefaultConfig)

    def testCertificateFileExists(self):
        self.assertTrue(os.path.exists(self.certificate_path))

    def testCertificateCreationWorksWithoutMail(self):
        del self.nonDefaultConfig['emailAddress']
        createCertificate(self.certificate_path, config=self.nonDefaultConfig)

    def testCertificateCreationWorksWithoutOU(self):
        del self.nonDefaultConfig['organizationalUnit']
        createCertificate(self.certificate_path, config=self.nonDefaultConfig)

    def testCertificateCreationWorksWithEmptyMail(self):
        del self.nonDefaultConfig['emailAddress']
        createCertificate(self.certificate_path, config=self.nonDefaultConfig)

    def testCertificateCreationWorksWithEmptyOU(self):
        del self.nonDefaultConfig['organizationalUnit']
        createCertificate(self.certificate_path, config=self.nonDefaultConfig)


class LoadConfigurationTestCase(unittest.TestCase):
    EXAMPLE_CERTIFICATE = os.path.join(os.path.dirname(__file__),
        'testdata', 'util', 'task', 'certificate', 'example.pem')

    def testLoadingFailsIfNoFileFound(self):
        filename = 'nofile'
        self.assertFalse(os.path.exists(filename))
        self.assertRaises(NoCertificateError, loadConfigurationFromCertificate, filename)

    def testLoadingFromFile(self):
        certparams = loadConfigurationFromCertificate(self.EXAMPLE_CERTIFICATE)

        self.assertEqual('DE', certparams["country"])
        self.assertEqual('RP', certparams["state"])
        self.assertEqual('Mainz', certparams["locality"])
        self.assertEqual('UIB', certparams["organization"])
        self.assertEqual('test', certparams["organizationalUnit"])
        self.assertEqual('niko-linux', certparams["commonName"])
        self.assertEqual('info@uib.de', certparams["emailAddress"])
        self.assertEqual(18428462229954092504, certparams["serialNumber"])


class LoadBrokenConfigurationTestCase(unittest.TestCase):
    def testLoadingFromCorruptFileWithValidBlockSignsRaisesError(self):
        corruptCertPath = os.path.join(os.path.dirname(__file__),
        'testdata', 'util', 'task', 'certificate', 'corrupt.pem')

        self.assertRaises(UnreadableCertificateError, loadConfigurationFromCertificate, corruptCertPath)

    def testLoadingFromInvalidFileRaisesError(self):
        corruptCertPath = os.path.join(os.path.dirname(__file__),
        'testdata', 'util', 'task', 'certificate', 'invalid.pem')

        self.assertRaises(UnreadableCertificateError, loadConfigurationFromCertificate, corruptCertPath)


if __name__ == '__main__':
    unittest.main()
