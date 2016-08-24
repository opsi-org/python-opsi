#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2016 uib GmbH <info@uib.de>

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
Testing cryptographic functionality of OPSI.Util.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import os.path

from OPSI.Util import randomString
from OPSI.Util import encryptWithPublicKeyFromX509CertificatePEMFile, decryptWithPrivateKeyFromPEMFile
from OPSI.Util.Task.Certificate import createCertificate

from .helpers import workInTemporaryDirectory

import pytest


@pytest.yield_fixture(scope='module')
def tempCertPath():
    with workInTemporaryDirectory() as tempDir:
        keyFile = os.path.join(tempDir, 'temp.pem')
        createCertificate(keyFile)

        yield keyFile


@pytest.yield_fixture(params=[1, 5, 32, 91, 256, 337, 512, 829, 3333])
def randomText(request):
    yield randomString(request.param)


def testEncryptingAndDecryptingTextWithCertificate(tempCertPath, randomText):
    pytest.importorskip("M2Crypto")  # Lazy import in the encrypt / decrypt functions

    encryptedText = encryptWithPublicKeyFromX509CertificatePEMFile(randomText, tempCertPath)
    assert encryptedText != randomText

    decryptedText = decryptWithPrivateKeyFromPEMFile(encryptedText, tempCertPath)
    assert decryptedText == randomText
