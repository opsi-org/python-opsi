# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
Testing functionality for compression in an HTTP context.
"""

from OPSI.Util.HTTP import deflateEncode, deflateDecode
from OPSI.Util.HTTP import gzipEncode, gzipDecode

import pytest


@pytest.fixture(params=[1, 2, 3, 4, 5, 6, 7, 8, 9])
def compressionLevel(request):
	yield request.param


@pytest.fixture(
	params=["Mötörheäd!", "Das ist ein Test und so."],
	ids=["unicode", "str"],
	scope="session"
)
def text(request):
	yield request.param


@pytest.fixture(params=[
	(gzipEncode, gzipDecode),
	(deflateEncode, deflateDecode)
],
	ids=["gzip", "deflate"],
	scope="session",
)
def compressionFunctions(request):
	yield request.param


def testCompressionAndDecompression(compressionFunctions, text):
	encode, decode = compressionFunctions

	compressed = encode(text)
	assert compressed
	assert text != compressed

	newText = decode(compressed)
	assert text == newText.decode("utf-8")


def testCompressionWithDifferentLevels(compressionFunctions, text, compressionLevel):
	encode, decode = compressionFunctions
	compressed = encode(text, compressionLevel)

	assert compressed
	assert text != compressed

	newText = decode(compressed)
	assert text == newText.decode("utf-8")
