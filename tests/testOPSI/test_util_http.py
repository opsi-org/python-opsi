# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing various HTTP utilities.
"""

from OPSI.Util.HTTP import createBasicAuthHeader
from OPSI.Util.HTTP import HTTPSConnectionPool

import pytest


@pytest.mark.parametrize("username, password, expectedResult", [
	("hans", "wurst", b"Basic aGFuczp3dXJzdA=="),
	("pcpatch", "notarealpw", b"Basic cGNwYXRjaDpub3RhcmVhbHB3"),
])
def testCreateBasicAuthHeader(username, password, expectedResult):
	assert expectedResult == createBasicAuthHeader(username, password)

def test_peer_cert():
	pool = HTTPSConnectionPool(
		host='download.uib.de',
		port=443,
		connectTimeout=5
	)
	resp = pool.urlopen('GET', url='/index.html', body=None, headers={"accept": "text/html", "user-agent": "test"})
	assert pool.getPeerCertificate(asPem=True).startswith(b"-----BEGIN CERTIFICATE----")
