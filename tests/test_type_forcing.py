#!/usr/bin/env python
#-*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2016 uib GmbH <info@uib.de>

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
Testing type forcing methods.

:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import datetime
import time
import unittest

from OPSI.Object import OpsiClient, Host, ProductOnClient
from OPSI.Types import (forceObjectClass, forceUnicode, forceUnicodeList,
	forceList, forceBool, forceBoolList, forceInt, forceOct, forceIPAddress,
	forceOpsiTimestamp, forceHardwareAddress, forceHostId, forceNetworkAddress,
	forceUrl, forceProductId, forcePackageVersion,forceFilename, forceTime,
	forceProductVersion, forceOpsiHostKey,forceInstallationStatus,
	forceActionRequest, forceActionProgress,forceLanguageCode, forceIntList,
	forceArchitecture, forceEmailAddress, forceUnicodeLowerList,
	forceProductType, forceDict, forceUniqueList, args, forceFqdn,
	forceGroupType, forceFloat)

import pytest


class ForceObjectClassJSONTestCase(unittest.TestCase):
	def setUp(self):
		self.object = OpsiClient(
			id='test1.test.invalid',
			description='Test client 1',
			notes='Notes ...',
			hardwareAddress='00:01:02:03:04:05',
			ipAddress='192.168.1.100',
			lastSeen='2009-01-01 00:00:00',
			opsiHostKey='45656789789012789012345612340123'
		)

		self.json = self.object.toJson()

	def tearDown(self):
		del self.json
		del self.object

	def testForceObjectClassToHostFromJSON(self):
		self.assertTrue(isinstance(forceObjectClass(self.json, Host), Host))

	def testForceObjectClassToOpsiClientFromJSON(self):
		self.assertTrue(isinstance(forceObjectClass(self.json, OpsiClient), OpsiClient))

	def testForcingObjectClassFromJSON(self):
		json = {
			"clientId": "dolly.janus.vater",
			"actionRequest": "setup",
			"productType": "LocalbootProduct",
			"type": "ProductOnClient",
			"productId": "hoer_auf_deinen_vater"
		}

		poc = forceObjectClass(json, ProductOnClient)

		self.assertTrue(isinstance(poc, ProductOnClient))

	def testForcingObjectClassFromJSONHasGoodErrorDescription(self):
		incompleteJson = {
			"clientId": "Nellie*",
			"actionRequest": "setup",
			"productType": "LocalbootProduct",
			"type": "ProductOnClient"
		}

		try:
			forceObjectClass(incompleteJson, ProductOnClient)
			self.fail("No error from incomplete json.")
		except ValueError as error:
			self.assertTrue("Missing required argument(s): 'productId'" in str(error))

		incompleteJson['type'] = "NotValid"
		try:
			forceObjectClass(incompleteJson, ProductOnClient)
			self.fail("No error from invalid type.")
		except ValueError as error:
			self.assertTrue("Invalild object type: NotValid" in str(error))


class ForceObjectClassHashTestCase(unittest.TestCase):
	def setUp(self):
		self.object = OpsiClient(
			id='test1.test.invalid',
			description='Test client 1',
			notes='Notes ...',
			hardwareAddress='00:01:02:03:04:05',
			ipAddress='192.168.1.100',
			lastSeen='2009-01-01 00:00:00',
			opsiHostKey='45656789789012789012345612340123'
		)

		self.hash = self.object.toHash()

	def tearDown(self):
		del self.hash
		del self.object

	def testForceObjectClassToHostFromHash(self):
		self.assertTrue(isinstance(forceObjectClass(self.hash, Host), Host))

	def testForceObjectClassToOpsiClientFromHash(self):
		self.assertTrue(isinstance(forceObjectClass(self.hash, OpsiClient), OpsiClient))


def funkyGenerator():
	yield "y"
	yield "u"
	yield "so"
	yield "funky"


@pytest.mark.parametrize("input, expected", [
	("x", ['x']),
	("xy", ['xy']),
	(None, [None]),
	((0, 1), [0, 1]),
	(('x', 'a'), ['x', 'a']),
	(['x', 'a'], ['x', 'a']),
	(funkyGenerator(), ['y', 'u', 'so', 'funky']),
])
def testForceList(input, expected):
	result = forceList(input)
	assert isinstance(result, list)
	assert expected == result


def testForceListConvertingSet():
	inputset = set('abc')
	resultList = forceList(inputset)

	assert len(inputset) == len(resultList)

	for element in inputset:
		assert element in resultList


class ForceUnicodeTestCase(unittest.TestCase):
	def testForcingResultsInUnicode(self):
		self.assertTrue(isinstance(forceUnicode('x'), unicode))


class ForceUnicodeListTestCase(unittest.TestCase):
	def testForcingResultsInUnicode(self):
		for i in forceUnicodeList([None, 1, 'x', u'y']):
			self.assertTrue(isinstance(i, unicode))


class ForceUnicodeLowerListTestCase(unittest.TestCase):
	def testForcingResultsInLowercase(self):
		self.assertEqual(forceUnicodeLowerList(['X', u'YES']), ['x', 'yes'])

	def testForcingResultsInUnicode(self):
		for i in forceUnicodeLowerList([None, 1, 'X', u'y']):
			self.assertTrue(isinstance(i, unicode))


class ForceBoolTestCase(unittest.TestCase):
	"""
	Testing if forceBool works. Always should work case-insensitive.
	"""
	def testOnOff(self):
		self.assertTrue(forceBool('on'))
		self.assertFalse(forceBool('OFF'))

	def testYesNo(self):
		self.assertTrue(forceBool('YeS'))
		self.assertFalse(forceBool('no'))

	def testOneZero(self):
		self.assertTrue(forceBool(1))
		self.assertTrue(forceBool('1'))
		self.assertFalse(forceBool(0))
		self.assertFalse(forceBool('0'))

	def testXMarksTheSpot(self):
		self.assertTrue(forceBool(u'x'))

	def testBoolTypes(self):
		self.assertTrue(forceBool(True))
		self.assertFalse(forceBool(False))

	def testTrueAndFalseAsStrings(self):
		self.assertTrue(forceBool("TRUE"))
		self.assertTrue(forceBool("true"))  # JSON style
		self.assertFalse(forceBool("FALSE"))
		self.assertFalse(forceBool("false"))  # JSON style

class ForceBoolListTestCase(unittest.TestCase):
	def testPositiveList(self):
		for i in forceBoolList([1, 'yes', 'on', '1', True]):
			self.assertTrue(i)

	def testMethod(self):
		for i in forceBoolList([None, 'no', 'false', '0', False]):
			self.assertFalse(i)


class ForceIntTestCase(unittest.TestCase):
	def testWithString(self):
		self.assertEquals(forceInt('100'), 100)

	def testWithNegativeValueInString(self):
		self.assertEquals(forceInt('-100'), -100)

	def testWithLongValue(self):
		self.assertEquals(forceInt(long(1000000000000000)), 1000000000000000)

	def testRaisingValueError(self):
		self.assertRaises(ValueError, forceInt, 'abc')


class ForceIntListTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertEquals(forceIntList(['100', 1, u'2']), [100, 1 , 2])


class ForceOctTestCase(unittest.TestCase):
	def testForcingDoesNotChangeValue(self):
		self.assertEquals(forceOct(0o666), 0o666)
		self.assertEquals(forceOct(0o750), 0o750)

	def testForcingString(self):
		self.assertEquals(forceOct('666'), 0o666)

	def testForcingStringWithLeadingZero(self):
		self.assertEquals(forceOct('0666'), 0o666)

	def testRaisingErrors(self):
		self.assertRaises(ValueError, forceOct, 'abc')
		self.assertRaises(ValueError, forceOct, '8')


class ForceOpsiTimeStampTestCase(unittest.TestCase):
	def testForcingReturnsString(self):
		self.assertEquals(forceOpsiTimestamp('20000202111213'), u'2000-02-02 11:12:13')

	def testResultIsUnicode(self):
		self.assertTrue(isinstance(forceOpsiTimestamp('2000-02-02 11:12:13'), unicode))

	def testRaisingErrorsOnWrongInput(self):
		self.assertRaises(ValueError, forceOpsiTimestamp, 'abc')

	def testForcingWithAnEmptyValue(self):
		self.assertEqual(forceOpsiTimestamp(None), '0000-00-00 00:00:00')

	def testForcingWithDatetime(self):
		self.assertEqual(forceOpsiTimestamp(datetime.datetime(2013, 9, 11, 10, 54, 23)), '2013-09-11 10:54:23')
		self.assertEqual(forceOpsiTimestamp(datetime.datetime(2013, 9, 11, 10, 54, 23, 123123)), '2013-09-11 10:54:23')

	def testForcingEmptyValue(self):
		self.assertEquals(u'0000-00-00 00:00:00', forceOpsiTimestamp(None))
		self.assertEquals(u'0000-00-00 00:00:00', forceOpsiTimestamp(0))
		self.assertEquals(u'0000-00-00 00:00:00', forceOpsiTimestamp(''))


class ForceHostIdTestCase(unittest.TestCase):
	def testForcingWithValidId(self):
		self.assertEquals(forceHostId(u'client.test.invalid'), u'client.test.invalid')
		self.assertTrue(forceHostId(u'client.test.invalid'), u'client.test.invalid')

	def testInvalidHOstIdsRaiseExceptions(self):
		self.assertRaises(ValueError, forceHostId, 'abc')
		self.assertRaises(ValueError, forceHostId, 'abc.def')
		self.assertRaises(ValueError, forceHostId, '.test.invalid')
		self.assertRaises(ValueError, forceHostId, 'abc.uib.x')


class ForceHardwareAddressTestCase(unittest.TestCase):
	def testForcingReturnsAddressSeperatedByColons(self):
		self.assertEquals(forceHardwareAddress('12345678ABCD'), u'12:34:56:78:ab:cd')
		self.assertEquals(forceHardwareAddress('12:34:56:78:ab:cd'), u'12:34:56:78:ab:cd')

	def testForcingReturnsLowercaseLetters(self):
		self.assertEquals(forceHardwareAddress('12-34-56-78-Ab-cD'), u'12:34:56:78:ab:cd')
		self.assertEquals(forceHardwareAddress('12-34-56:78AB-CD'), u'12:34:56:78:ab:cd')

	def testForcingResultsInUnicode(self):
		self.assertTrue(isinstance(forceHardwareAddress('12345678ABCD'), unicode))

	def testForcingInvalidAddressesRaiseExceptions(self):
		self.assertRaises(ValueError, forceHardwareAddress, '12345678abc')
		self.assertRaises(ValueError, forceHardwareAddress, '12345678abcdef')
		self.assertRaises(ValueError, forceHardwareAddress, '1-2-3-4-5-6-7')
		self.assertRaises(ValueError, forceHardwareAddress, None)
		self.assertRaises(ValueError, forceHardwareAddress, True)

	def testForcingEmptyStringReturnsEmptyString(self):
		self.assertEquals("", forceHardwareAddress(""))


@pytest.mark.parametrize("input, expected", [
	('1.1.1.1', u'1.1.1.1'),
	('192.168.101.1', u'192.168.101.1'),
	(u'192.168.101.1', u'192.168.101.1'),
])
def testForceIPAddress(input, expected):
	output = forceIPAddress(input)
	assert expected == output
	assert isinstance(output, unicode)


@pytest.mark.parametrize("malformed_input", [
	'1922.1.1.1',
	None,
	True,
	'1.1.1.1.',
	'2.2.2.2.2',
	'a.2.3.4',
])
def testForceIPAddressFailsOnInvalidInput(malformed_input):
	with pytest.raises(ValueError):
		forceIPAddress(input)


class ForceNetworkAddressTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertEquals(forceNetworkAddress('192.168.0.0/16'), u'192.168.0.0/16')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceNetworkAddress('10.10.10.10/32'), unicode))

	def testForcingWithInvalidAddressesRaisesExceptions(self):
		self.assertRaises(ValueError, forceNetworkAddress, '192.168.101.1')
		self.assertRaises(ValueError, forceNetworkAddress, '192.1.1.1/40')
		self.assertRaises(ValueError, forceNetworkAddress, None)
		self.assertRaises(ValueError, forceNetworkAddress, True)
		self.assertRaises(ValueError, forceNetworkAddress, '10.10.1/24')
		self.assertRaises(ValueError, forceNetworkAddress, 'a.2.3.4/0')


class ForceUrlTestCase(unittest.TestCase):
	def testForcing(self):
		self.assertTrue(forceUrl('file:///'), 'file:///')
		self.assertTrue(forceUrl('file:///path/to/file'), 'file:///path/to/file')
		self.assertTrue(forceUrl('smb://server/path'), 'smb://server/path')
		self.assertTrue(forceUrl('https://x:y@server.domain.tld:4447/resource'), 'https://x:y@server.domain.tld:4447/resource')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceUrl('file:///'), unicode))
		self.assertTrue(isinstance(forceUrl('file:///path/to/file'), unicode))
		self.assertTrue(isinstance(forceUrl('smb://server/path'), unicode))
		self.assertTrue(isinstance(forceUrl('https://x:y@server.domain.tld:4447/resource'), unicode))

	def testForcingWithInvalidURLsRaisesExceptions(self):
		self.assertRaises(ValueError, forceUrl, 'abc')
		self.assertRaises(ValueError, forceUrl, '/abc')
		self.assertRaises(ValueError, forceUrl, 'http//server')
		self.assertRaises(ValueError, forceUrl, 1)
		self.assertRaises(ValueError, forceUrl, True)
		self.assertRaises(ValueError, forceUrl, None)

	def testForcingDoesNotForceLowercase(self):
		"""
		URLs must not be force lowercase because they could include an
		username / password combination for an proxy.
		"""
		self.assertTrue(forceUrl('https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource'), 'https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource')
		self.assertTrue(forceUrl('https://X:Y@server.domain.tld:4447/resource'), 'https://X:Y@server.domain.tld:4447/resource')


class ForceOpsiHostKeyTestCase(unittest.TestCase):
	def testForcingReturnsLowercase(self):
		self.assertEquals(forceOpsiHostKey('abCdeF78901234567890123456789012'), 'abcdef78901234567890123456789012')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceOpsiHostKey('12345678901234567890123456789012'), unicode))

	def testForcingWithInvalidHostKeysRaisesExceptions(self):
		self.assertRaises(ValueError, forceOpsiHostKey, 'abCdeF7890123456789012345678901')
		self.assertRaises(ValueError, forceOpsiHostKey, 'abCdeF78901234567890123456789012b')
		self.assertRaises(ValueError, forceOpsiHostKey, 'GbCdeF78901234567890123456789012')


class ForceProductVersionTestCase(unittest.TestCase):
	def testForcing(self):
		forceProductVersion('1.0') == '1.0'

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceProductVersion('1.0'), unicode))

	def testProductVersionDoesNotContainUppercase(self):
		self.assertRaises(ValueError, forceProductVersion, 'A1.0')


class ForcePackageVersionTestCase(unittest.TestCase):
	def testMethod(self):
		self.assertEquals(forcePackageVersion(1), '1')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forcePackageVersion('8'), unicode))

	def testPackageVersionDoesNotContainUppercase(self):
		self.assertRaises(ValueError, forcePackageVersion, 'A')


class ForceProductIdTestCase(unittest.TestCase):
	def testMethod(self):
		self.assertEquals(forceProductId('testProduct1'), 'testproduct1')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceProductId('test-Product-1'), unicode))

	def testForcingWithInvalidProductIdRaisesExceptions(self):
		self.assertRaises(ValueError, forceProductId, u'äöü')
		self.assertRaises(ValueError, forceProductId, 'product test')


class ForceFilenameTestCase(unittest.TestCase):
	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceFilename('/tmp/test.txt'), unicode))

	def testForcingFilename(self):
		self.assertEquals(forceFilename('c:\\tmp\\test.txt'), u'c:\\tmp\\test.txt')


class ForceInstallationStatusTestCase(unittest.TestCase):
	def testForcingAcceptsOnlyValidStatus(self):
		self.assertEquals(forceInstallationStatus('installed'), 'installed')
		self.assertEquals(forceInstallationStatus('not_installed'), 'not_installed')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceInstallationStatus('installed'), unicode))
		self.assertTrue(isinstance(forceInstallationStatus('not_installed'), unicode))

	def testForcingWithInvalidStatusRaisesExceptions(self):
		self.assertRaises(ValueError, forceInstallationStatus, 'none')
		self.assertRaises(ValueError, forceInstallationStatus, 'abc')


class ForceActionRequestTestCase(unittest.TestCase):
	def testForcingWithInvalidStatusRaisesExceptions(self):
		self.assertRaises(ValueError, forceActionRequest, 'installed')

	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceActionRequest('setup'), unicode))

	def testForcingReturnsLowercase(self):
		self.assertEquals(forceActionRequest('setup'), str('setup').lower())
		self.assertEquals(forceActionRequest('uninstall'), str('uninstall').lower())
		self.assertEquals(forceActionRequest('update'), str('update').lower())
		self.assertEquals(forceActionRequest('once'), str('once').lower())
		self.assertEquals(forceActionRequest('always'), str('always').lower())
		self.assertEquals(forceActionRequest('none'), str('none').lower())
		self.assertEquals(forceActionRequest(None), str(None).lower())

	def testForcingUndefinedReturnsNone(self):
		self.assertEquals(None, forceActionRequest("undefined"))


class ForceActionProgressTestCase(unittest.TestCase):
	def testForcingReturnsUnicode(self):
		self.assertTrue(isinstance(forceActionProgress('installing 50%'), unicode))

	def testForcing(self):
		self.assertEquals(forceActionProgress('installing 50%'), u'installing 50%')


class ForceLanguageCodeTestCase(unittest.TestCase):
	def testCasingGetsAdjusted(self):
		self.assertEquals(forceLanguageCode('xx-xxxx-xx'), u'xx-Xxxx-XX')
		self.assertEquals(forceLanguageCode('yy_yy'), u'yy-YY')
		self.assertEquals(forceLanguageCode('zz_ZZZZ'), u'zz-Zzzz')

	def testForcing(self):
		self.assertEquals(forceLanguageCode('dE'), u'de')
		self.assertEquals(forceLanguageCode('en-us'), u'en-US')

	def testForcingWithWrongCodeSetupRaisesExceptions(self):
		self.assertRaises(ValueError, forceLanguageCode, 'de-DEU')


class ForceArchitectureTestCase(unittest.TestCase):
	def testForcingReturnsLowercase(self):
		self.assertEquals(forceArchitecture('X86'), u'x86')
		self.assertEquals(forceArchitecture('X64'), u'x64')


class ForceTimeTestCase(unittest.TestCase):
	def testForcingFailsWithInvalidTime(self):
		self.assertRaises(ValueError, forceTime, 'Hello World!')

	def testForcingWorksWithVariousTypes(self):
		self.assertTrue(isinstance(forceTime(time.time()), time.struct_time))
		self.assertTrue(isinstance(forceTime(time.localtime()), time.struct_time))
		self.assertTrue(isinstance(forceTime(datetime.datetime.now()), time.struct_time))


class ForceEmailAddressTestCase(unittest.TestCase):
	def testForcingRequiresValidMailAddress(self):
		self.assertRaises(ValueError, forceEmailAddress, 'infouib.de')

	def testForcing(self):
		self.assertEquals(forceEmailAddress('info@uib.de'), u'info@uib.de')


class ForceProductTypeTestCase(unittest.TestCase):
	def testRaisingExceptionOnUnknownType(self):
		self.assertRaises(ValueError, forceProductType, 'TrolololoProduct')

	def testForcingToLocalbootProduct(self):
		self.assertEquals(forceProductType('LocalBootProduct'), 'LocalbootProduct')
		self.assertEquals(forceProductType('LOCALBOOT'), 'LocalbootProduct')

	def testForcingToNetbootProduct(self):
		self.assertEquals(forceProductType('NetbOOtProduct'), 'NetbootProduct')
		self.assertEquals(forceProductType('nETbOOT'), 'NetbootProduct')


@pytest.mark.parametrize("input, expected", [
	(None, {}),
	({'a': 1}, {'a': 1}),
])
def testForceDictReturnsDict(input, expected):
	assert forceDict(input) == expected

@pytest.mark.parametrize("input", ['asdg', ['asdfg', 'asd']])
def testForceDictFailsIfConversionImpossible(input):
	with pytest.raises(ValueError):
		forceDict(input)


class ForceUniqueListTestCase(unittest.TestCase):
	def testAfterForcingItemsInListAreUnique(self):
		self.assertEqual([1], forceUniqueList([1,1]))
		self.assertEqual([1,2,3], forceUniqueList((1,2,2,3)))

	def testForcingDoesNotChangeOrder(self):
		self.assertEqual([2,1,3,5,4], forceUniqueList([2,2,1,3,5,4,1]))


class ArgsDecoratorTestCase(unittest.TestCase):
	def testDecoratorArgumentsDefaultToNone(self):

		@args("somearg", "someOtherArg")
		class SomeClass(object):
			def __init__(self, **kwargs):
				pass

		someObj = SomeClass()

		self.assertEquals(None, someObj.somearg)
		self.assertEquals(None, someObj.someOtherArg)

	def testDecoratorTakesKeywordArguments(self):

		@args("somearg", someOtherArg=forceInt)
		class SomeOtherClass(object):
			def __init__(self, **kwargs):
				pass

		someOtherObj = SomeOtherClass(someOtherArg="5")

		self.assertEquals(None, someOtherObj.somearg, "Expected somearg to be None, but got %s instead" % someOtherObj.somearg)
		self.assertEquals(5, someOtherObj.someOtherArg, "Expected someOtherArg to be %d, but got %s instead." %(5, someOtherObj.someOtherArg))

	def testDecoratorCreatesPrivateArgs(self):

		@args("_somearg", "_someOtherArg")
		class SomeClass(object):
			def __init__(self, **kwargs):
				pass

		someObj = SomeClass(somearg=5)

		self.assertEquals(5, someObj._somearg, "Expected somearg to be %d, but got %s instead" % (5, someObj._somearg))
		self.assertEquals(None, someObj._someOtherArg, "Expected someOtherArg to be None, but got %s instead" % someObj._someOtherArg)



def testForceFqdnRemovesTrailingDot():
	assert 'abc.example.local' == forceFqdn('abc.example.local.')


def testForceFqdnRequiresHostnameRootZoneAndTopLevelDomain():
	with pytest.raises(ValueError):
		forceFqdn('hostname.tld')

	forceFqdn('hostname.rootzone.tld')


@pytest.mark.parametrize("domain", [
	'BLA.domain.invalid',
	'bla.doMAIN.invalid',
	'bla.domain.iNVAlid'])
def testForceFqdnAlwaysReturnsLowercase(domain):
	assert 'bla.domain.invalid' == forceFqdn(domain)


@pytest.mark.parametrize("input", ['asdf', None])
def testForceGroupFailsOnInvalidInput(input):
	with pytest.raises(ValueError):
		forceGroupType(input)


@pytest.mark.parametrize("input, expected", [
	('hostGROUP', 'HostGroup'),
	('HostgROUp', 'HostGroup'),
	('PrOdUcTgRoUp', 'ProductGroup'),
])
def testForceGroupTypeStandardisesCase(input, expected):
	assert forceGroupType(input) == expected


@pytest.mark.parametrize("input, expected", [
	(1, 1.0),
	(1.3, 1.3),
	("1", 1.0),
	("1.3", 1.3),
	("    1.4   ", 1.4),
])
def testForceFloat(input, expected):
	assert expected == forceFloat(input)


@pytest.mark.parametrize("invalidInput", [
	{"abc": 123},
	['a', 'b'],
	"No float",
	"text",
])
def testForceFloatFailsWithInvalidInput(invalidInput):
	with pytest.raises(ValueError):
		forceFloat(invalidInput)


if __name__ == '__main__':
	unittest.main()
