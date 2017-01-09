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

from OpenSSL.SSL import Context

from OPSI.Service import SSLContext

from .test_util import tempCertPath  # Fixture


def testGettingSSLContext(tempCertPath):
    sslContext = SSLContext(tempCertPath, tempCertPath)
    context = sslContext.getContext()

    assert isinstance(context, Context)


@pytest.mark.parametrize("cipherList", (
    None
))
def testGettingSSLContextWithListOfAcceptedCiphers(tempCertPath, cipherList):
    sslContext = SSLContext(tempCertPath, tempCertPath, cipherList)
    context = sslContext.getContext()

    if cipherList:
        assert context.get_cipher_list() == cipherList
