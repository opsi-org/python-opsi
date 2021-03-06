# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2017 uib GmbH <info@uib.de>

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
Testing service components.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import pytest
from OpenSSL.SSL import Context

from OPSI.Service import SSLContext

from .test_util import tempCertPath  # Fixture


@pytest.mark.parametrize("cipherList", (
    None,
    'TLSv1+HIGH:!SSLv2:RC4+MEDIUM:!aNULL:!eNULL:!3DES:@STRENGTH',
))
def testGettingSSLContext(tempCertPath, cipherList):
    sslContext = SSLContext(tempCertPath, tempCertPath, cipherList)
    context = sslContext.getContext()

    assert isinstance(context, Context)


def testCreatingSSLContextRequiresCertificatesToBePresent(tempCertPath):
    with pytest.raises(OSError):
        sslContext = SSLContext(tempCertPath, '')
        sslContext.getContext()

    with pytest.raises(OSError):
        sslContext = SSLContext('', tempCertPath)
        sslContext.getContext()
