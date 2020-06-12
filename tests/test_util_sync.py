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

import codecs
import os
import os.path
import shutil
import random
import string
from itertools import combinations_with_replacement

import pytest

importFailed = False
from OPSI.Util.Sync import librsyncDeltaFile, librsyncSignature, librsyncPatchFile


@pytest.fixture
def librsyncTestfile():
	return os.path.join(
		os.path.dirname(__file__),
		'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
	)


@pytest.mark.skipif(importFailed, reason="Import failed.")
def testLibrsyncSignatureBase64Encoded(librsyncTestfile):
	assert b'cnMBNgAACAAAAAAI/6410IBmvH1GKbBN\n' == librsyncSignature(librsyncTestfile)


@pytest.mark.skipif(importFailed, reason="Import failed.")
def testLibrsyncSignatureCreation(librsyncTestfile):
	signature = librsyncSignature(librsyncTestfile, base64Encoded=False)
	assert b'rs\x016\x00\x00\x08\x00\x00\x00\x00\x08\xff\xae5\xd0\x80f\xbc}F)\xb0M' == signature


@pytest.mark.skipif(importFailed, reason="Import failed.")
def testLibrsyncDeltaFileCreation(librsyncTestfile, tempDir):
	deltafile = os.path.join(tempDir, 'delta')
	oldfile = os.path.join(tempDir, 'old')
	with open(oldfile, "wb") as f:
		f.write(b"olddata")
	signature = librsyncSignature(oldfile, base64Encoded=False)
	
	librsyncDeltaFile(librsyncTestfile, signature.strip(), deltafile)
	assert os.path.exists(deltafile), "No delta file was created"

	expectedDelta = b"rs\x026B\x04\x8a"
	with open(librsyncTestfile, "rb") as f:
		expectedDelta += f.read()
	expectedDelta += b"\x00"
	
	with open(deltafile, "rb") as f:
		assert expectedDelta == f.read()

@pytest.mark.skipif(importFailed, reason="Import failed.")
def testLibrsyncDeltaSize(librsyncTestfile, tempDir):
	baseFile = os.path.join(tempDir, 'base')
	oldfile = os.path.join(tempDir, 'old')
	deltaFile = os.path.join(tempDir, 'base.delta')
	size = 1 * 1024 * 1024 # 1MiB

	data = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
	with open(baseFile, "w") as f:
		f.write(data)
	with open(oldfile, "w") as f:
		f.write(data[:int(size/2)])
	
	signature = librsyncSignature(oldfile, False)
	librsyncDeltaFile(baseFile, signature, deltaFile)
	delta_size = os.path.getsize(deltaFile)
	assert delta_size == 524398

@pytest.mark.skipif(importFailed, reason="Import failed.")
def testLibrsyncPatchFileDoesNotAlterIfUnneeded(librsyncTestfile, tempDir):
	baseFile = librsyncTestfile
	oldfile = os.path.join(tempDir, 'old')
	deltaFile = os.path.join(tempDir, 'base.delta')

	shutil.copy(baseFile, oldfile)
	signature = librsyncSignature(oldfile, False)
	librsyncDeltaFile(baseFile, signature, deltaFile)

	assert os.path.exists(deltaFile)
	expectedDelta = b"rs\x026F\x00\x04\x8a\x00"
	with open(deltaFile, "rb") as f:
		assert expectedDelta == f.read()
	
	newfile = os.path.join(tempDir, 'newFile.txt')
	librsyncPatchFile(oldfile, deltaFile, newfile)
	assert os.path.exists(newfile)

	with open(newfile, "rb") as newF:
		with open(baseFile, "rb") as baseF:
			assert baseF.readlines() == newF.readlines()


@pytest.mark.skipif(importFailed, reason="Import failed.")
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
		b'rs\x026B\x04\xb8Die NASA konnte wieder ein Funksignal der '
		b'Sonde New Horizons empfangen. Damit scheint sicher, dass '
		b'das Man\xc3\xb6ver ein Erfolg war und nun jede Menge Daten '
		b'zu erwarten sind. Bis die alle auf der Erde sind, wird es '
		b'aber dauern.\n\nDie NASA feiert eine "historische Nacht": '
		b'Die Sonde New Horizons ist am Zwergplaneten Pluto '
		b'vorbeigeflogen und hat kurz vor drei Uhr MESZ wieder Kontakt '
		b'mit der Erde aufgenommen. Jubel, rotwei\xc3\x9fblaue '
		b'F\xc3\xa4hnchen und stehende Ovationen pr\xc3\xa4gten die '
		b'Stimmung im John Hopkins Labor in Maryland. Digital stellten '
		b'sich prominente Gratulanten ein, von Stephen Hawking mit '
		b'einer Videobotschaft bis zu US-Pr\xc3\xa4sident Barack Obama '
		b'per Twitter.\n\n"Hallo Welt"\n\nDas erste Funksignal New '
		b'Horizons nach dem Vorbeiflug am Pluto brachte noch keine '
		b'wissenschaftlichen Ergebnisse oder neue Fotos, sondern '
		b'Telemetriedaten der Sonde selbst. Das war so geplant. '
		b'Aus diesen Informationen geht hervor, dass es New Horizons '
		b'gut geht, dass sie ihren Kurs h\xc3\xa4lt und die '
		b'vorausberechnete Menge an Speichersektoren belegt ist. '
		b'Daraus schlie\xc3\x9fen die Verantwortlichen der NASA, dass '
		b'auch tats\xc3\xa4chlich wissenschaftliche Informationen im '
		b'geplanten Ausma\xc3\x9f gesammelt wurden.\n\nUnd diese Zeile '
		b'hier macht den Unterschied.\n\x00')

	with open(deltaFileForNewFile, "rb") as f:
		assert expectedDelta == f.read()

	fileBasedOnDelta = os.path.join(tempDir, 'newnew.txt')
	librsyncPatchFile(baseFile, deltaFileForNewFile, fileBasedOnDelta)
	with open(newFile, "r") as newF:
		with open(fileBasedOnDelta, "r") as newF2:
			assert newF.readlines() == newF2.readlines()

	with codecs.open(fileBasedOnDelta, "r", 'utf-8') as newF2:
		assert any(additionalText in line for line in newF2)


@pytest.mark.skipif(importFailed, reason="Import failed.")
@pytest.mark.parametrize("old, delta, new", list(combinations_with_replacement(('foo', 'bar'), 3)))
def testLibrsyncPatchFileAvoidsPatchingSameFile(old, delta, new):
	with pytest.raises(ValueError):
		librsyncPatchFile(old, delta, new)
