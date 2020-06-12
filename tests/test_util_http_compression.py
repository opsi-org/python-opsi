# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2019  uib GmbH <info@uib.de>

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
Testing functionality for compression in an HTTP context.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from OPSI.Util.HTTP import deflateEncode, deflateDecode
from OPSI.Util.HTTP import gzipEncode, gzipDecode

import pytest


@pytest.fixture(params=[1, 2, 3, 4, 5, 6, 7, 8, 9])
def compressionLevel(request):
	yield request.param


@pytest.fixture(
	params=[u"Mötörheäd!", "Das ist ein Test und so."],
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
	assert text == newText


def testCompressionWithDifferentLevels(compressionFunctions, text, compressionLevel):
	encode, decode = compressionFunctions
	compressed = encode(text, compressionLevel)

	assert compressed
	assert text != compressed

	newText = decode(compressed)
	assert text == newText
