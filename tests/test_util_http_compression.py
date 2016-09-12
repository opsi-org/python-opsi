#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2015-2016  uib GmbH <info@uib.de>

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
    ids=["unicode", "str"]
)
def text(request):
    yield request.param


def testDeflate(text):
    deflated = deflateEncode(text)
    assert deflated
    assert text != deflated

    newText = deflateDecode(deflated)
    assert text == newText


def testDeflateWithDifferentCompressionLevels(text, compressionLevel):
    deflated = deflateEncode(text, compressionLevel)

    assert deflated
    assert text != deflated

    newText = deflateDecode(deflated)
    assert text == newText


def testGzip(text):
    gzipped = gzipEncode(text)
    assert gzipped
    assert text[0] != gzipped[0]

    newText = gzipDecode(gzipped)
    assert text == newText


def testGzipWithDifferentCompressionLevels(text, compressionLevel):
    gzipped = gzipEncode(text, compressionLevel)
    assert gzipped
    assert text[0] != gzipped[0]

    newText = gzipDecode(gzipped)
    assert text == newText
