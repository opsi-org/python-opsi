#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2017 uib GmbH <info@uib.de>

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
import random
import re
import os
import os.path
import shutil
import sys
from collections import defaultdict
from contextlib import contextmanager

from OPSI.Object import LocalbootProduct, OpsiClient
from OPSI.Util import (blowfishDecrypt, blowfishEncrypt, chunk, compareVersions,
    decryptWithPrivateKeyFromPEMFile,
    encryptWithPublicKeyFromX509CertificatePEMFile, findFiles, flattenSequence,
    formatFileSize, fromJson, generateOpsiHostKey, getfqdn, getGlobalConfig,
    ipAddressInNetwork, isRegularExpressionPattern, librsyncDeltaFile,
    librsyncSignature, librsyncPatchFile, md5sum, objectToBeautifiedText,
    objectToHtml, randomString, removeUnit, toJson)
from OPSI.Util import BlowfishError
from OPSI.Util.Task.Certificate import createCertificate

from .helpers import (fakeGlobalConf, patchAddress, patchEnvironmentVariables,
    unittest, workInTemporaryDirectory)

import pytest

try:
    from itertools import combinations_with_replacement
except ImportError:  # Python 2.6...
    # We define our own fallback by copying what is written in the
    # documentation at https://docs.python.org/2.7/library/itertools.html#itertools.combinations_with_replacement
    from itertools import product

    def combinations_with_replacement(iterable, r):
        pool = tuple(iterable)
        n = len(pool)
        for indices in product(range(n), repeat=r):
            if sorted(indices) == list(indices):
                yield tuple(pool[i] for i in indices)



@pytest.mark.parametrize("ip, network",[
    ('10.10.1.1', '10.10.0.0/16'),
    ('10.10.1.1', '10.10.0.0/23'),
    pytest.mark.xfail(('10.10.1.1', '10.10.0.0/24')),
    pytest.mark.xfail(('10.10.1.1', '10.10.0.0/25')),
])
def testNetworkWithSlashInNotation(ip, network):
    assert ipAddressInNetwork(ip, network)


def testIpAddressInNetworkWithEmptyNetworkMask():
    assert ipAddressInNetwork('10.10.1.1', '0.0.0.0/0')


def testIpAddressInNetworkWithFullNetmask():
    assert ipAddressInNetwork('10.10.1.1', '10.10.0.0/255.240.0.0')


class ProductFactory(object):
    productVersions = ('1.0', '2', 'xxx', '3.1', '4')
    packageVersions = ('1', '2', 'y', '3', '10', 11, 22)
    licenseRequirements = (None, True, False)
    setupScripts = ('setup.ins', None)
    updateScripts = ('update.ins', None)
    uninstallScripts = ('uninstall.ins', None)
    alwaysScripts = ('always.ins', None)
    onceScripts = ('once.ins', None)
    priorities = (-100, -90, -30, 0, 30, 40, 60, 99)
    descriptions = ['Test product', 'Some product', '--------', '', None]
    advices = ('Nothing', 'Be careful', '--------', '', None)

    @classmethod
    def generateLocalbootProduct(self, index=0):
        return LocalbootProduct(
            id='product{0}'.format(index),
            productVersion=random.choice(self.productVersions),
            packageVersion=random.choice(self.packageVersions),
            name='Product {0}'.format(index),
            licenseRequired=random.choice(self.licenseRequirements),
            setupScript=random.choice(self.setupScripts),
            uninstallScript=random.choice(self.uninstallScripts),
            updateScript=random.choice(self.updateScripts),
            alwaysScript=random.choice(self.alwaysScripts),
            onceScript=random.choice(self.onceScripts),
            priority=random.choice(self.priorities),
            description=random.choice(self.descriptions),
            advice=random.choice(self.advices),
            changelog=None,
            windowsSoftwareIds=None
        )


class ObjectToHTMLTestCase(unittest.TestCase):
    def testWorkingWithManyObjectsMustNotFail(self):
        obj = [
            ProductFactory.generateLocalbootProduct(i)
            for i in range(1024)
        ]

        objectToHtml(obj)

    def testWorkingWithGeneratorObjectsMustNotFail(self):
        generator = (
            ProductFactory.generateLocalbootProduct(i)
            for i in range(128)
        )

        objectToHtml(generator)

        text = objectToHtml(ProductFactory.generateLocalbootProduct(i)
                            for i in range(2))

        self.assertTrue(text.strip().startswith('['))
        self.assertTrue(text.strip().endswith(']'))

    def testCheckingOutput(self):
        product = LocalbootProduct(
            id='htmltestproduct',
            productVersion='3.1',
            packageVersion='1',
            name='Product HTML Test',
            licenseRequired=False,
            setupScript='setup.ins',
            uninstallScript='uninstall.ins',
            updateScript='update.ins',
            alwaysScript='always.ins',
            onceScript='once.ins',
            priority=0,
            description="asdf",
            advice="lolnope",
            changelog=None,
            windowsSoftwareIds=None
        )

        expected = u'{<div style="padding-left: 3em;"><font class="json_key">"onceScript"</font>: "once.ins",<br />\n<font class="json_key">"windowsSoftwareIds"</font>: null,<br />\n<font class="json_key">"description"</font>: "asdf",<br />\n<font class="json_key">"advice"</font>: "lolnope",<br />\n<font class="json_key">"alwaysScript"</font>: "always.ins",<br />\n<font class="json_key">"updateScript"</font>: "update.ins",<br />\n<font class="json_key">"productClassIds"</font>: null,<br />\n<font class="json_key">"id"</font>: "htmltestproduct",<br />\n<font class="json_key">"licenseRequired"</font>: false,<br />\n<font class="json_key">"ident"</font>: "htmltestproduct;3.1;1",<br />\n<font class="json_key">"name"</font>: "Product&nbsp;HTML&nbsp;Test",<br />\n<font class="json_key">"changelog"</font>: null,<br />\n<font class="json_key">"customScript"</font>: null,<br />\n<font class="json_key">"uninstallScript"</font>: "uninstall.ins",<br />\n<font class="json_key">"userLoginScript"</font>: null,<br />\n<font class="json_key">"priority"</font>: 0,<br />\n<font class="json_key">"productVersion"</font>: "3.1",<br />\n<font class="json_key">"packageVersion"</font>: "1",<br />\n<font class="json_key">"type"</font>: "LocalbootProduct",<br />\n<font class="json_key">"setupScript"</font>: "setup.ins"</div>}'
        self.assertEquals(expected, objectToHtml(product))


class ObjectToBeautifiedTextTestCase(unittest.TestCase):
    def testWorkingWithManyObjectsMustNotFail(self):
        obj = [
            ProductFactory.generateLocalbootProduct(i)
            for i in range(10240)
        ]

        objectToBeautifiedText(obj)

    def testWorkingWithGeneratorObjectsMustNotFail(self):
        generator = (
            ProductFactory.generateLocalbootProduct(i)
            for i in range(128)
        )

        objectToBeautifiedText(generator)

        text = objectToBeautifiedText(ProductFactory.generateLocalbootProduct(i)
                                        for i in range(2))

        self.assertTrue(text.strip().startswith('['))
        self.assertTrue(text.strip().endswith(']'))

        objects = fromJson(text)
        self.assertEquals(2, len(objects))
        for generator in objects:
            self.assertTrue(isinstance(generator, LocalbootProduct))

    def testCheckingOutput(self):
        product = LocalbootProduct(
            id='htmltestproduct',
            productVersion='3.1',
            packageVersion='1',
            name='Product HTML Test',
            licenseRequired=False,
            setupScript='setup.ins',
            uninstallScript='uninstall.ins',
            updateScript='update.ins',
            alwaysScript='always.ins',
            onceScript='once.ins',
            priority=0,
            description="asdf",
            advice="lolnope",
            changelog=None,
            windowsSoftwareIds=None
        )

        expected = u"""\
[
    {
    "onceScript" : "once.ins",
    "windowsSoftwareIds" : null,
    "description" : "asdf",
    "advice" : "lolnope",
    "alwaysScript" : "always.ins",
    "updateScript" : "update.ins",
    "productClassIds" : null,
    "id" : "htmltestproduct",
    "licenseRequired" : false,
    "ident" : "htmltestproduct;3.1;1",
    "name" : "Product HTML Test",
    "changelog" : null,
    "customScript" : null,
    "uninstallScript" : "uninstall.ins",
    "userLoginScript" : null,
    "priority" : 0,
    "productVersion" : "3.1",
    "packageVersion" : "1",
    "type" : "LocalbootProduct",
    "setupScript" : "setup.ins"
    },
    {
    "onceScript" : "once.ins",
    "windowsSoftwareIds" : null,
    "description" : "asdf",
    "advice" : "lolnope",
    "alwaysScript" : "always.ins",
    "updateScript" : "update.ins",
    "productClassIds" : null,
    "id" : "htmltestproduct",
    "licenseRequired" : false,
    "ident" : "htmltestproduct;3.1;1",
    "name" : "Product HTML Test",
    "changelog" : null,
    "customScript" : null,
    "uninstallScript" : "uninstall.ins",
    "userLoginScript" : null,
    "priority" : 0,
    "productVersion" : "3.1",
    "packageVersion" : "1",
    "type" : "LocalbootProduct",
    "setupScript" : "setup.ins"
    }
]\
"""
        self.maxDiff = None
        self.assertEquals(expected, objectToBeautifiedText([product, product]))

    def testFormattingEmptyList(self):
        self.assertEquals('[\n]', objectToBeautifiedText([]))

    def testFormattingListOfEmptyLists(self):
        expected = u"""\
[
    [
    ],
    [
    ]
]\
"""
        self.assertEquals(expected, objectToBeautifiedText([[],[]]))

    def testFormattingEmptyDict(self):
        self.assertEquals('{\n}', objectToBeautifiedText({}))

        expected = u"""\
    {
    }\
"""
        self.assertEquals(expected, objectToBeautifiedText({}, level=1))

    def testFormattingDefaultDict(self):
        normalDict = {u'lastStateChange': u'', u'actionRequest': u'none', u'productVersion': u'', u'productActionProgress': u'', u'packageVersion': u'', u'installationStatus': u'not_installed', u'productId': u'thunderbird'}
        defaultDict = defaultdict(lambda x: u'')

        for key, value in normalDict.items():
            defaultDict[key] = value

        normal = objectToBeautifiedText(normalDict)
        default = objectToBeautifiedText(defaultDict)

        self.assertEquals(normal, default)

    def testWorkingWithSet(self):
        # Exactly one product because set is unordered.
        obj = set([
            LocalbootProduct(
                id='htmltestproduct',
                productVersion='3.1',
                packageVersion='1',
                name='Product HTML Test',
                licenseRequired=False,
                setupScript='setup.ins',
                uninstallScript='uninstall.ins',
                updateScript='update.ins',
                alwaysScript='always.ins',
                onceScript='once.ins',
                priority=0,
                description="asdf",
                advice="lolnope",
                changelog=None,
                windowsSoftwareIds=None
            )
        ])

        expected = """\
[
    {
    "onceScript" : "once.ins",
    "windowsSoftwareIds" : null,
    "description" : "asdf",
    "advice" : "lolnope",
    "alwaysScript" : "always.ins",
    "updateScript" : "update.ins",
    "productClassIds" : null,
    "id" : "htmltestproduct",
    "licenseRequired" : false,
    "ident" : "htmltestproduct;3.1;1",
    "name" : "Product HTML Test",
    "changelog" : null,
    "customScript" : null,
    "uninstallScript" : "uninstall.ins",
    "userLoginScript" : null,
    "priority" : 0,
    "productVersion" : "3.1",
    "packageVersion" : "1",
    "type" : "LocalbootProduct",
    "setupScript" : "setup.ins"
    }
]\
"""

        self.assertEquals(expected, objectToBeautifiedText(obj))


def testRandomStringBuildsStringOutOfGivenCharacters():
    assert 5*'a' == randomString(5, characters='a')


@pytest.mark.parametrize("length", [10, 1, 0])
def testRandomStringHasExpectedLength(length):
    result = randomString(length)
    assert length == len(result)
    assert length == len(result.strip())


def _dummyGeneratorFunc():
    yield 3
    yield 4
    yield [5]


@pytest.mark.parametrize("sequence, out", [
    ((1, [2]), [1, 2]),
    ((1, [2, (3, )]), [1, 2, 3]),
    (((1, ), (2, ), 3), [1, 2, 3]),
    (set([1, 2, 3]), [1, 2, 3]),
    ([1, set([2, ]), 3, 4, set([5])], [1, 2, 3, 4, 5]),
    ((x for x in range(1, 6)), [1, 2, 3, 4, 5]),
    ([1, 2, _dummyGeneratorFunc()], [1, 2, 3, 4, 5])
])
def testFlattenSequence(sequence, out):
    assert out == flattenSequence(sequence)


@pytest.mark.parametrize("kwargs", [{}, {"forcePython": True}])
def testGenerateOpsiHostKeyIs32CharsLong(kwargs):
    assert 32 == len(generateOpsiHostKey(kwargs))


@pytest.mark.parametrize("testInput, expected", [
    (123, '123'),
    (1234, '1K'),
    (1234567, '1M'),
    (314572800, '300M'),
    (1234567890, '1G'),
    (1234567890000, '1T'),
])
def testFormatFileSize(testInput, expected):
    assert expected == formatFileSize(testInput)


@pytest.mark.parametrize("testFile, expectedHash", [
    (os.path.join(os.path.dirname(__file__), 'testdata', 'util', 'dhcpd', 'dhcpd_1.conf'), '5f345ca76574c528903c1022b05acb4c'),
])
def testCreatingMd5sum(testFile, expectedHash):
    assert expectedHash == md5sum(testFile)


class ChunkingTestCase(unittest.TestCase):
    def testChunkingList(self):
        base = list(range(10))

        chunks = chunk(base, size=3)
        self.assertEquals((0, 1, 2), next(chunks))
        self.assertEquals((3, 4, 5), next(chunks))
        self.assertEquals((6, 7, 8), next(chunks))
        self.assertEquals((9, ), next(chunks))
        self.assertRaises(StopIteration, next, chunks)

    def testChunkingGenerator(self):
        def gen():
            yield 0
            yield 1
            yield 2
            yield 3
            yield 4
            yield 5
            yield 6
            yield 7
            yield 8
            yield 9

        chunks = chunk(gen(), size=3)
        self.assertEquals((0, 1, 2), next(chunks))
        self.assertEquals((3, 4, 5), next(chunks))
        self.assertEquals((6, 7, 8), next(chunks))
        self.assertEquals((9, ), next(chunks))
        self.assertRaises(StopIteration, next, chunks)

    def testChunkingGeneratorWithDifferentSize(self):
        def gen():
            yield 0
            yield 1
            yield 2
            yield 3
            yield 4
            yield 5
            yield 6
            yield 7
            yield 8
            yield 9

        chunks = chunk(gen(), size=5)
        self.assertEquals((0, 1, 2, 3, 4), next(chunks))
        self.assertEquals((5, 6, 7, 8, 9), next(chunks))
        self.assertRaises(StopIteration, next, chunks)


class LibrsyncTestCase(unittest.TestCase):

    def testLibrsyncSignatureBase64Encoded(self):
        testFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
        )
        self.assertEqual('cnMBNgAACAAAAAAI/6410IBmvH1GKbBN\n', librsyncSignature(testFile))

    def testLibrsyncSignature(self):
        testFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
        )
        signature = librsyncSignature(testFile, base64Encoded=False)
        self.assertEqual('rs\x016\x00\x00\x08\x00\x00\x00\x00\x08\xff\xae5\xd0\x80f\xbc}F)\xb0M', signature)

    def testLibrsyncDeltaFile(self):
        testFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
        )

        signature = librsyncSignature(testFile, base64Encoded=False)

        with workInTemporaryDirectory() as tempDir:
            deltafile = os.path.join(tempDir, 'delta')

            librsyncDeltaFile(testFile, signature.strip(), deltafile)
            self.assertTrue(os.path.exists(deltafile), "No delta file was created")

            expectedDelta = 'rs\x026F\x00\x04\x8a\x00'
            with open(deltafile, "r") as f:
                self.assertEqual(expectedDelta, f.read())

    def testLibrsyncPatchFileDoesNotAlterIfUnneeded(self):
        baseFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
        )

        signature = librsyncSignature(baseFile, False)

        with workInTemporaryDirectory() as tempDir:
            deltaFile = os.path.join(tempDir, 'base.delta')
            librsyncDeltaFile(baseFile, signature, deltaFile)

            self.assertTrue(os.path.exists(deltaFile))
            expectedDelta = "rs\x026F\x00\x04\x8a\x00"
            with open(deltaFile, "rb") as f:
                self.assertEqual(expectedDelta, f.read())

            newFile = os.path.join(tempDir, 'newFile.txt')
            librsyncPatchFile(baseFile, deltaFile, newFile)
            self.assertTrue(os.path.exists(newFile))

            with open(newFile, "r") as newF:
                with open(baseFile, "r") as baseF:
                    self.assertEqual(baseF.readlines(), newF.readlines())

    def testLibrsyncPatchFileCreatesNewFileBasedOnDelta(self):
        baseFile = os.path.join(
            os.path.dirname(__file__),
            'testdata', 'util', 'syncFiles', 'librsyncSignature.txt'
        )

        signature = librsyncSignature(baseFile, False)

        with workInTemporaryDirectory() as tempDir:
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
                self.assertEqual(expectedDelta, f.read())

            fileBasedOnDelta = os.path.join(tempDir, 'newnew.txt')
            librsyncPatchFile(baseFile, deltaFileForNewFile, fileBasedOnDelta)
            with open(newFile, "r") as newF:
                with open(fileBasedOnDelta, "r") as newF2:
                    self.assertEqual(newF.readlines(), newF2.readlines())

            with codecs.open(fileBasedOnDelta, "r", 'utf-8') as newF2:
                for line in newF2:
                    if additionalText in line:
                        break
                else:
                    self.fail("Missing additional text in new file.")


@pytest.mark.parametrize("old, delta, new", list(combinations_with_replacement(('foo', 'bar'), 3)))
def testLibrsyncPatchFileAvoidsPatchingSameFile(old, delta, new):
    with pytest.raises(ValueError):
        librsyncPatchFile(old, delta, new)


def testComparingVersionsOfSameSize():
    assert compareVersions('1.0', '<', '2.0')


@pytest.mark.parametrize("v1, operator, v2", [
    ('1.0', '', '1.0'),
    pytest.mark.xfail(('1', '', '2')),
])
def testComparingWithoutGivingOperatorDefaultsToEqual(v1, operator, v2):
    assert compareVersions(v1, operator, v2)


def testComparingWithOneEqualitySignWork():
    assert compareVersions('1.0', '=', '1.0')


@pytest.mark.parametrize("operator", ['asdf', '+-', '<>', '!='])
def testUsingUnknownOperatorFails(operator):
    with pytest.raises(Exception):
        compareVersions('1', operator, '2')


@pytest.mark.parametrize("v1, operator, v2", [
    ('1.0~20131212', '<', '2.0~20120101'),
    ('1.0~20131212', '==', '1.0~20120101'),
])
def testIgnoringVersionsWithWaveInThem(v1, operator, v2):
    assert compareVersions(v1, operator, v2)


@pytest.mark.parametrize("v1, operator, v2", [
    ('abc-1.2.3-4', '==', '1.2.3-4'),
    ('1.2.3-4', '==', 'abc-1.2.3-4')
])
def testUsingInvalidVersionStringsFails(v1, operator, v2):
    with pytest.raises(Exception):
        compareVersions(v1, operator, v2)


@pytest.mark.parametrize("v1, operator, v2", [
    ('1.0.a', '<', '1.0.b'),
    ('a.b', '>', 'a.a'),
])
def testComparingWorksWithLettersInVersionString(v1, operator, v2):
    assert compareVersions(v1, operator, v2)


@pytest.mark.parametrize("v1, operator, v2", [
    ('1.1.0.1', '>', '1.1'),
    ('1.1', '<', '1.1.0.1'),
])
def testComparisonsWithDifferntDepthsAreMadeTheSameDepth(v1, operator, v2):
    assert compareVersions(v1, operator, v2)


@pytest.mark.parametrize("v1, operator, v2", [
    ('1-2', '<', '1-3'),
    ('1-2.0', '<', '1-2.1')
])
def testPackageVersionsAreComparedAswell(v1, operator, v2):
    assert compareVersions(v1, operator, v2)


class GetGlobalConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.testFile = os.path.join(
            os.path.dirname(__file__), 'testdata', 'util', 'fake_global.conf'
        )

    def tearDown(self):
        del self.testFile

    def testCommentsAreIgnored(self):
        self.assertEqual("no", getGlobalConfig('comment', self.testFile))

    def testLinesNeedAssignments(self):
        self.assertEqual(None, getGlobalConfig('this', self.testFile))

    def testReadingValues(self):
        self.assertEqual("value", getGlobalConfig('keyword', self.testFile))
        self.assertEqual(
            "this works too",
            getGlobalConfig('value with spaces', self.testFile)
        )
        self.assertEqual(
            "we even can include a = and it works",
            getGlobalConfig('advanced value', self.testFile)
        )

    def testFileNotFoundExitsGracefully(self):
        self.assertEqual(None, getGlobalConfig('dontCare', 'nonexistingFile'))


@pytest.mark.parametrize("value", [
    re.compile("ABC"),
    pytest.mark.xfail("no pattern"),
    pytest.mark.xfail("SRE_Pattern"),
])
def testIfObjectIsRegExObject(value):
    assert isRegularExpressionPattern(value)


@pytest.mark.parametrize("value, expected", [
    (2, 2),
    ('2', 2),
])
def testRemoveUnitDoesNotFailWithoutUnit(value, expected):
    assert expected == removeUnit(value)


@pytest.mark.parametrize("value, expected", [
    ('2MB', 2097152),  # 2048 * 1024
    ('2.4MB', 2516582.4),  # (2048 * 1.2) * 1024),
    ('3GB', 3221225472),
    ('4Kb', 4096),
])
def testRemovingUnitFromValue(value, expected):
        assert expected == removeUnit(value)


class GetFQDNTestCase(unittest.TestCase):

    def testGettingFQDN(self):
        fqdn = "opsi.fqdntestcase.invalid"

        with patchAddress(fqdn=fqdn):
            self.assertEqual(fqdn, getfqdn())

    def testGettingFQDNFromGlobalConfig(self):
        with patchAddress(fqdn="nomatch.opsi.invalid"):
            fqdn = "opsi.test.invalid"
            with fakeGlobalConf(fqdn=fqdn) as configPath:
                self.assertEqual(fqdn, getfqdn(conf=configPath))

    def testGettingFQDNIfConfigMissing(self):
        fqdn = "opsi.fqdntestcase.invalid"

        configFilePath = randomString(32)
        while os.path.exists(configFilePath):
            configFilePath = randomString(32)

        with patchAddress(fqdn=fqdn):
            self.assertEqual(fqdn, getfqdn(conf=configFilePath))

    def testGettingFQDNIfConfigEmpty(self):
        with workInTemporaryDirectory() as tempDir:
            fqdn = "opsi.fqdntestcase.invalid"
            with patchAddress(fqdn=fqdn):
                confPath = os.path.join(tempDir, randomString(8))
                with open(confPath, 'w'):
                    pass

                self.assertEqual(fqdn, getfqdn(conf=confPath))

    def testGettingFQDNFromEnvironment(self):
        fqdn = "opsi.fqdntestcase.invalid"
        with patchAddress(fqdn="nomatch.uib.local"):
            with patchEnvironmentVariables(OPSI_HOSTNAME=fqdn):
                self.assertEqual(fqdn, getfqdn())

    def testGetFQDNByIPAddress(self):
        fqdn = "opsi.fqdntestcase.invalid"
        address = '127.0.0.1'

        with patchAddress(fqdn=fqdn, address=address):
            self.assertEqual(fqdn, getfqdn(name=address))


class JSONSerialisiationTestCase(unittest.TestCase):
    def testSerialisingSet(self):
        inputSet = set([u'opsi-client-agent', u'mshotfix', u'firefox'])
        output = toJson(inputSet)

        self.assertEquals(set(fromJson(output)), inputSet)

    def testSerialisingList(self):
        inputValues = ['a', 'b', 'c', 4, 5]
        output = toJson(inputValues)

        self.assertEquals(inputValues, fromJson(output))
        self.assertEquals(u'["a", "b", "c", 4, 5]', output)

    @unittest.skipIf(sys.version_info < (2, 7), "Python 2.6 is unprecise with floats")
    def testSerialisingListWithFLoat(self):
        inputValues = ['a', 'b', 'c', 4, 5.6]
        output = toJson(inputValues)

        self.assertEquals(inputValues, fromJson(output))
        self.assertEquals(u'["a", "b", "c", 4, 5.6]', output)

    def testSerialisingListInList(self):
        inputValues = ['a', 'b', 'c', [4, 5, ['f']]]
        self.assertEquals(u'["a", "b", "c", [4, 5, ["f"]]]', toJson(inputValues))

    @unittest.skipIf(sys.version_info < (2, 7), "Python 2.6 is unprecise with floats")
    def testSerialisingListInListWithFloat(self):
        inputValues = ['a', 'b', 'c', [4, 5.6, ['f']]]
        self.assertEquals(u'["a", "b", "c", [4, 5.6, ["f"]]]', toJson(inputValues))

    def testSerialisingSetInList(self):
        inputValues = ['a', 'b', set('c'), 4, 5]
        self.assertEquals(u'["a", "b", ["c"], 4, 5]', toJson(inputValues))

    @unittest.skipIf(sys.version_info < (2, 7), "Python 2.6 is unprecise with floats")
    def testSerialisingSetInListWithFloat(self):
        inputValues = ['a', 'b', set('c'), 4, 5.6]
        self.assertEquals(u'["a", "b", ["c"], 4, 5.6]', toJson(inputValues))

    def testSerialisingDictsInList(self):
        inputValues = [
            {'a': 'b', 'c': 1},
            {'a': 'b', 'c': 1},
        ]
        output = toJson(inputValues)

        self.assertEquals(u'[{"a": "b", "c": 1}, {"a": "b", "c": 1}]', output)

    @unittest.skipIf(sys.version_info < (2, 7), "Python 2.6 is unprecise with floats")
    def testSerialisingDictsInListWithFloat(self):
        inputValues = [
            {'a': 'b', 'c': 1, 'e': 2.3},
            {'g': 'h', 'i': 4, 'k': 5.6},
        ]
        output = toJson(inputValues)

        self.assertEquals(u'[{"a": "b", "c": 1, "e": 2.3}, {"i": 4, "k": 5.6, "g": "h"}]', output)

    def testSerialisingDict(self):
        inputValues = {'a': 'b', 'c': 1, 'e': 2}
        self.assertEquals(u'{"a": "b", "c": 1, "e": 2}', toJson(inputValues))
        self.assertEquals(inputValues, fromJson(toJson(inputValues)))

        if sys.version_info >= (2, 7):
            # 2.6 does display 5.6 something like this: 5.599999999999991
            inputValues = {'a': 'b', 'c': 1, 'e': 2.3}
            self.assertEquals(u'{"a": "b", "c": 1, "e": 2.3}', toJson(inputValues))

    def testUnserialisableThingsFail(self):
        class Foo(object):
            pass

        self.assertRaises(TypeError, toJson, Foo())

    def testDeserialisationWithObjectCreation(self):
        json = """[
    {
    "ident" : "baert.niko.uib.local",
    "description" : "",
    "created" : "2014-08-29 10:41:27",
    "inventoryNumber" : "loel",
    "ipAddress" : null,
    "notes" : "",
    "oneTimePassword" : null,
    "lastSeen" : "2014-08-29 10:41:27",
    "hardwareAddress" : null,
    "opsiHostKey" : "7dc2b49c20d545bdbfad9a326380cea3",
    "type" : "OpsiClient",
    "id" : "baert.niko.uib.local"
    }
]"""

        result = fromJson(json, preventObjectCreation=False)

        self.assertTrue(isinstance(result, list))
        self.assertEquals(1, len(result))

        obj = result[0]
        self.assertTrue(isinstance(obj, OpsiClient))

    def testDeserialisationWithoutObjectCreation(self):
        json = """[
    {
    "ident" : "baert.niko.uib.local",
    "description" : "",
    "created" : "2014-08-29 10:41:27",
    "inventoryNumber" : "loel",
    "ipAddress" : null,
    "notes" : "",
    "oneTimePassword" : null,
    "lastSeen" : "2014-08-29 10:41:27",
    "hardwareAddress" : null,
    "opsiHostKey" : "7dc2b49c20d545bdbfad9a326380cea3",
    "type" : "OpsiClient",
    "id" : "baert.niko.uib.local"
    }
]"""

        result = fromJson(json, preventObjectCreation=True)

        self.assertTrue(isinstance(result, list))
        self.assertEquals(1, len(result))

        obj = result[0]
        self.assertTrue(isinstance(obj, dict))
        self.assertTrue('ident' in obj)

    def testDeserialisationWithExplicitTypeSetting(self):
        "It must be possible to set an type."

        json = """
    {
    "ident" : "baert.niko.uib.local",
    "description" : "",
    "created" : "2014-08-29 10:41:27",
    "inventoryNumber" : "loel",
    "ipAddress" : null,
    "notes" : "",
    "oneTimePassword" : null,
    "lastSeen" : "2014-08-29 10:41:27",
    "hardwareAddress" : null,
    "opsiHostKey" : "7dc2b49c20d545bdbfad9a326380cea3",
    "id" : "baert.niko.uib.local"
    }
"""

        obj = fromJson(json, objectType="OpsiClient", preventObjectCreation=False)

        self.assertTrue(isinstance(obj, OpsiClient))

    def testDeserialisationWithExplicitTypeSettingWorksOnUnknown(self):
        "Setting invalid types must not fail but return the input instead."

        json = """
    {
    "ident" : "baert.niko.uib.local",
    "description" : "",
    "created" : "2014-08-29 10:41:27",
    "inventoryNumber" : "loel",
    "ipAddress" : null,
    "notes" : "",
    "oneTimePassword" : null,
    "lastSeen" : "2014-08-29 10:41:27",
    "hardwareAddress" : null,
    "opsiHostKey" : "7dc2b49c20d545bdbfad9a326380cea3",
    "id" : "baert.niko.uib.local"
    }
"""

        obj = fromJson(json, objectType="NotYourType", preventObjectCreation=False)

        self.assertTrue(isinstance(obj, dict))
        self.assertEquals("baert.niko.uib.local", obj['ident'])

    def testSerialisingGeneratorFunction(self):
        def gen():
            yield 1
            yield 2
            yield 3
            yield u"a"

        obj = toJson(gen())

        self.assertEquals(u'[1, 2, 3, "a"]', obj)

    def testSerialisingTuples(self):
        values = (1, 2, 3, 4)
        self.assertEquals('[1, 2, 3, 4]', toJson(values))


class FindFilesTestCase(unittest.TestCase):

    def testEmptyDirectory(self):
        with workInTemporaryDirectory() as tempDir:
            self.assertEquals([], findFiles(tempDir))

    def testFindingFolders(self):
        expectedFolders = ['top1', 'top2', os.path.join('top1', 'sub11')]

        with preparedDemoFolders() as demoFolder:
            folders = findFiles(demoFolder)
            for folder in expectedFolders:
                assert folder in folders


@contextmanager
def preparedDemoFolders():
    directories = (
        'top1',
        'top2',
        os.path.join('top1', 'sub11')
    )

    with workInTemporaryDirectory() as tempDir:
        for dirname in directories:
            os.mkdir(os.path.join(tempDir, dirname))

        yield tempDir


@pytest.fixture(scope='module')
def tempCertPath():
    with workInTemporaryDirectory() as tempDir:
        keyFile = os.path.join(tempDir, 'temp.pem')
        createCertificate(keyFile)

        yield keyFile


@pytest.fixture(params=[1, 5, 91, 256, 337, 512, 829, 3333])
def randomText(request):
    yield randomString(request.param)


def testEncryptingAndDecryptingTextWithCertificate(tempCertPath, randomText):
    pytest.importorskip("M2Crypto")  # Lazy import in the encrypt / decrypt functions

    encryptedText = encryptWithPublicKeyFromX509CertificatePEMFile(randomText, tempCertPath)
    assert encryptedText != randomText

    decryptedText = decryptWithPrivateKeyFromPEMFile(encryptedText, tempCertPath)
    assert decryptedText == randomText


@pytest.mark.parametrize("text", [u'this is some random string we want to test'])
@pytest.mark.parametrize("key", [u'575bf0d0b557dd9184ae41e7ff58ead0'])
def testBlowfishEncryption(text, key):
    encodedText = blowfishEncrypt(key, text)
    assert encodedText != text

    decodedText = blowfishDecrypt(key, encodedText)
    assert text == decodedText


@pytest.mark.parametrize("text", [u'this is some random string we want to test'])
@pytest.mark.parametrize("key", [u'575bf0d0b557dd9184ae41e7ff58ead0'])
def testBlowfishEncryptionFailures(text, key):
    encodedText = blowfishEncrypt(key, text)
    assert encodedText != text

    with pytest.raises(BlowfishError):
        blowfishDecrypt(key + 'f00b4', encodedText)
