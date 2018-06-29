# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2018 uib GmbH <info@uib.de>

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
Testing functionality of OPSI.Util.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

from __future__ import absolute_import

import codecs
import os
import os.path
import shutil
from itertools import combinations_with_replacement

from OPSI.Util import librsyncDeltaFile, librsyncSignature, librsyncPatchFile

import pytest


@pytest.fixture
def librsyncTestfile():
    return os.path.join(
        os.path.dirname(__file__),
        'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
    )


def testLibrsyncSignatureBase64Encoded(librsyncTestfile):
    assert 'cnMBNgAACAAAAAAI/6410IBmvH1GKbBN\n' == librsyncSignature(librsyncTestfile)


def testLibrsyncSignatureCreation(librsyncTestfile):
    signature = librsyncSignature(librsyncTestfile, base64Encoded=False)
    assert 'rs\x016\x00\x00\x08\x00\x00\x00\x00\x08\xff\xae5\xd0\x80f\xbc}F)\xb0M' == signature


def testLibrsyncDeltaFileCreation(librsyncTestfile, tempDir):
    signature = librsyncSignature(librsyncTestfile, base64Encoded=False)
    deltafile = os.path.join(tempDir, 'delta')

    librsyncDeltaFile(librsyncTestfile, signature.strip(), deltafile)
    assert os.path.exists(deltafile), "No delta file was created"

    expectedDelta = 'rs\x026F\x00\x04\x8a\x00'
    with open(deltafile, "r") as f:
        assert expectedDelta == f.read()


def testLibrsyncPatchFileDoesNotAlterIfUnneeded(librsyncTestfile, tempDir):
    baseFile = librsyncTestfile
    signature = librsyncSignature(baseFile, False)

    deltaFile = os.path.join(tempDir, 'base.delta')
    librsyncDeltaFile(baseFile, signature, deltaFile)

    assert os.path.exists(deltaFile)
    expectedDelta = "rs\x026F\x00\x04\x8a\x00"
    with open(deltaFile, "rb") as f:
        assert expectedDelta == f.read()

    newFile = os.path.join(tempDir, 'newFile.txt')
    librsyncPatchFile(baseFile, deltaFile, newFile)
    assert os.path.exists(newFile)

    with open(newFile, "r") as newF:
        with open(baseFile, "r") as baseF:
            assert baseF.readlines() == newF.readlines()


def testLibrsyncPatchFileCreatesNewFileBasedOnDelta(librsyncTestfile, tempDir):
    baseFile = librsyncTestfile
    signature = librsyncSignature(baseFile, False)

    newFile = os.path.join(tempDir, 'oldnew.txt')
    shutil.copy(baseFile, newFile)

    additionalText = u"Und diese Zeile hier macht den Unterschied."

    with codecs.open(newFile, 'a', 'utf-8') as nf:
        nf.write("\n\n{0}\n".format(additionalText))

    deltaFileForNewFile = os.path.join(tempDir, 'newDelta.delta')
    librsyncDeltaFile(newFile, signature, deltaFileForNewFile)
    expectedDelta = (
        'rs\x026B\x04\xb8Die NASA konnte wieder ein Funksignal der '
        'Sonde New Horizons empfangen. Damit scheint sicher, dass '
        'das Man\xc3\xb6ver ein Erfolg war und nun jede Menge Daten '
        'zu erwarten sind. Bis die alle auf der Erde sind, wird es '
        'aber dauern.\n\nDie NASA feiert eine "historische Nacht": '
        'Die Sonde New Horizons ist am Zwergplaneten Pluto '
        'vorbeigeflogen und hat kurz vor drei Uhr MESZ wieder Kontakt '
        'mit der Erde aufgenommen. Jubel, rotwei\xc3\x9fblaue '
        'F\xc3\xa4hnchen und stehende Ovationen pr\xc3\xa4gten die '
        'Stimmung im John Hopkins Labor in Maryland. Digital stellten '
        'sich prominente Gratulanten ein, von Stephen Hawking mit '
        'einer Videobotschaft bis zu US-Pr\xc3\xa4sident Barack Obama '
        'per Twitter.\n\n"Hallo Welt"\n\nDas erste Funksignal New '
        'Horizons nach dem Vorbeiflug am Pluto brachte noch keine '
        'wissenschaftlichen Ergebnisse oder neue Fotos, sondern '
        'Telemetriedaten der Sonde selbst. Das war so geplant. '
        'Aus diesen Informationen geht hervor, dass es New Horizons '
        'gut geht, dass sie ihren Kurs h\xc3\xa4lt und die '
        'vorausberechnete Menge an Speichersektoren belegt ist. '
        'Daraus schlie\xc3\x9fen die Verantwortlichen der NASA, dass '
        'auch tats\xc3\xa4chlich wissenschaftliche Informationen im '
        'geplanten Ausma\xc3\x9f gesammelt wurden.\n\nUnd diese Zeile '
        'hier macht den Unterschied.\n\x00')

    with open(deltaFileForNewFile, "rb") as f:
        assert expectedDelta == f.read()

    fileBasedOnDelta = os.path.join(tempDir, 'newnew.txt')
    librsyncPatchFile(baseFile, deltaFileForNewFile, fileBasedOnDelta)
    with open(newFile, "r") as newF:
        with open(fileBasedOnDelta, "r") as newF2:
            assert newF.readlines() == newF2.readlines()

    with codecs.open(fileBasedOnDelta, "r", 'utf-8') as newF2:
        assert any(additionalText in line for line in newF2)


@pytest.mark.parametrize("old, delta, new", list(combinations_with_replacement(('foo', 'bar'), 3)))
def testLibrsyncPatchFileAvoidsPatchingSameFile(old, delta, new):
    with pytest.raises(ValueError):
        librsyncPatchFile(old, delta, new)
