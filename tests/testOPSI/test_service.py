# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing service components.
"""

import pytest
from OpenSSL.SSL import Context

from OPSI.Service import SSLContext

from .test_util import tempCertPath  # Fixture


@pytest.mark.parametrize("cipherList", (
	None,
	b'TLSv1+HIGH:!SSLv2:RC4+MEDIUM:!aNULL:!eNULL:!3DES:@STRENGTH',
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
