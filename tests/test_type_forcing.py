# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2013-2019 uib GmbH <info@uib.de>

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

import pytest

from OPSI.Object import OpsiClient, Host, ProductOnClient
from OPSI.Types import (args, forceActionRequest, forceActionProgress,
	forceArchitecture, forceBool, forceDict, forceBoolList, forceEmailAddress,
	forceFilename, forceFloat, forceFqdn, forceGroupType, forceHardwareAddress,
	forceHostId, forceInstallationStatus, forceInt, forceIntList, forceIPAddress,
	forceNetworkAddress, forceLanguageCode, forceList, forceObjectClass,
	forceOct, forceOpsiHostKey, forceOpsiTimestamp,	forcePackageVersion,
	forceProductId, forceProductType, forceProductVersion, forceTime,
	forceUnicode, forceUnicodeList, forceUnicodeLowerList, forceUniqueList,
	forceUrl)


@pytest.fixture
def opsiClient():
	return OpsiClient(
		id='test1.test.invalid',
		description='Test client 1',
		notes='Notes ...',
		hardwareAddress='00:01:02:03:04:05',
		ipAddress='192.168.1.100',
		lastSeen='2009-01-01 00:00:00',
		opsiHostKey='45656789789012789012345612340123'
	)


@pytest.mark.parametrize("klass", [Host, OpsiClient])
def testForceObjectClassToHostFromJSON(opsiClient, klass):
	assert isinstance(forceObjectClass(opsiClient.toJson(), klass), klass)


def testForcingObjectClassFromProductOnClientJSON():
	json = {
		"clientId": "dolly.janus.vater",
		"actionRequest": "setup",
		"productType": "LocalbootProduct",
		"type": "ProductOnClient",
		"productId": "hoer_auf_deinen_vater"
	}

	poc = forceObjectClass(json, ProductOnClient)

	assert isinstance(poc, ProductOnClient)


def testForcingObjectClassFromJSONHasGoodErrorDescription():
	incompleteJson = {
		"clientId": "Nellie*",
		"actionRequest": "setup",
		"productType": "LocalbootProduct",
		"type": "ProductOnClient"
	}

	try:
		forceObjectClass(incompleteJson, ProductOnClient)
		pytest.fail("No error from incomplete json.")
	except ValueError as error:
		assert "missing 1 required positional argument: 'productId'" in str(error)

	incompleteJson['type'] = "NotValid"
	try:
		forceObjectClass(incompleteJson, ProductOnClient)
		pytest.fail("No error from invalid type.")
	except ValueError as error:
		assert "Invalild object type: NotValid" in str(error)


@pytest.mark.parametrize("klass", [Host, OpsiClient])
def testForceObjectClassFromHash(opsiClient, klass):
	assert isinstance(forceObjectClass(opsiClient.toHash(), klass), klass)


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


@pytest.mark.parametrize("value, expected", [
	('x', 'x'),
	(b'bff69c0d457adb884dafbe8b55a56258', 'bff69c0d457adb884dafbe8b55a56258')
])
def testForceUnicodeResultsInUnicode(value, expected):
	result = forceUnicode(value)
	assert isinstance(result, str)
	assert result == expected


def testForceUnicodeListResultsInListOfUnicode():
	returned = forceUnicodeList([None, 1, 'x', u'y'])
	assert isinstance(returned, list)

	for i in returned:
		assert isinstance(i, str)


def testForceUnicodeLowerListResultsInLowercase():
	assert forceUnicodeLowerList(['X', u'YES']) == ['x', 'yes']


def testForceUnicodeLowerListResultsInUnicode():
	for i in forceUnicodeLowerList([None, 1, 'X', u'y']):
		assert isinstance(i, str)


@pytest.mark.parametrize("value", ("on", "oN", 'YeS', 1, '1', 'x', True, 'true', 'TRUE'))
def testForceBoolWithTrueValues(value):
	assert forceBool(value) is True


@pytest.mark.parametrize("value", ("off", "oFF", 'no', 0, '0', False, 'false', 'FALSE'))
def testForceBoolWithFalsyValues(value):
	assert forceBool(value) is False


def testForceBoolWithPositiveList():
	for i in forceBoolList([1, 'yes', 'on', '1', True]):
		assert i is True


def testForceBoolWithNegativeList():
	for i in forceBoolList([None, 'no', 'false', '0', False]):
		assert i is False


@pytest.mark.parametrize("value, expected", (
	('100', 100),
	('-100', -100),
	(int(1000000000000000), 1000000000000000)
))
def testForceInt(value, expected):
	assert expected == forceInt(value)


@pytest.mark.parametrize("value", ("abc", ))
def testForceIntRaisesValueErrorIfNoConversionPossible(value):
	with pytest.raises(ValueError):
		forceInt(value)


def testForceIntList():
	assert [100, 1, 2] == forceIntList(['100', 1, u'2'])


@pytest.mark.parametrize("value, expected", (
	(0o750, 0o750),
	(0o666, 0o666),
	('666', 0o666),
	('0666', 0o666),
))
def testForceOct(value, expected):
	assert expected == forceOct(value)


@pytest.mark.parametrize("value", ('abc', '8'))
def testForceOctRaisingErrorsOnInvalidValue(value):
	with pytest.raises(ValueError):
		forceOct(value)


@pytest.mark.parametrize("value, expected", (
	('20000202111213', u'2000-02-02 11:12:13'),
	(None, '0000-00-00 00:00:00'),
	(0, u'0000-00-00 00:00:00'),
	('', u'0000-00-00 00:00:00'),
	(datetime.datetime(2013, 9, 11, 10, 54, 23), '2013-09-11 10:54:23'),
	(datetime.datetime(2013, 9, 11, 10, 54, 23, 123123), '2013-09-11 10:54:23'),
))
def testForceOpsiTimestamp(value, expected):
	result = forceOpsiTimestamp(value)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("value", ('abc', '8'))
def testForceOpsiTimestampRaisesErrorsOnWrongInput(value):
	with pytest.raises(ValueError):
		forceOpsiTimestamp(value)


@pytest.mark.parametrize("hostId, expected", (
	(u'client.test.invalid', u'client.test.invalid'),
	(u'CLIENT.test.invalid', u'client.test.invalid')
))
def testForceHostId(hostId, expected):
		assert expected == forceHostId(u'client.test.invalid')


@pytest.mark.parametrize("hostId", ('abc', '8', 'abc.def', '.test.invalid', 'abc.uib.x'))
def testForceHostIdRaisesExceptionIfInvalid(hostId):
	with pytest.raises(ValueError):
		forceHostId(hostId)


@pytest.mark.parametrize("address, expected", (
	('12345678ABCD', u'12:34:56:78:ab:cd'),
	('12:34:56:78:ab:cd', u'12:34:56:78:ab:cd'),
	('12-34-56-78-Ab-cD', u'12:34:56:78:ab:cd'),
	('12-34-56:78AB-CD', u'12:34:56:78:ab:cd'),
	('', ''),
))
def testForcingReturnsAddressSeperatedByColons(address, expected):
	result = forceHardwareAddress(address)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("address", (
	'12345678abc',
	'12345678abcdef',
	'1-2-3-4-5-6-7',
	None,
	True,
))
def testForcingInvalidAddressesRaiseExceptions(address):
	with pytest.raises(ValueError):
		forceHardwareAddress(address)


@pytest.mark.parametrize("input, expected", [
	('1.1.1.1', u'1.1.1.1'),
	('192.168.101.1', u'192.168.101.1'),
	(u'192.168.101.1', u'192.168.101.1'),
])
def testForceIPAddress(input, expected):
	output = forceIPAddress(input)
	assert expected == output
	assert isinstance(output, str)


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


@pytest.mark.parametrize("address, expected", (
	('192.168.0.0/16', u'192.168.0.0/16'),
	('10.10.10.10/32', u'10.10.10.10/32'),
))
def testforceNetworkAddress(address, expected):
	result = forceNetworkAddress(address)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("address", (
	'192.168.101.1',
	'192.1.1.1/40',
	None,
	True,
	'10.10.1/24',
	'a.2.3.4/0',
))
def testForceNetworkAddressWithInvalidAddressesRaisesExceptions(address):
	with pytest.raises(ValueError):
		forceNetworkAddress(address)


@pytest.mark.parametrize("url, expected", (
	('file:///', 'file:///'),
	('file:///path/to/file', 'file:///path/to/file'),
	('smb://server/path', 'smb://server/path'),
	('https://x:y@server.domain.tld:4447/resource', 'https://x:y@server.domain.tld:4447/resource'),
))
def testForceUrl(url, expected):
	result = forceUrl(url)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("url, expected", (
	('https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource', 'https://X:YY12ZZ@SERVER.DOMAIN.TLD:4447/resource'),
	('https://X:Y@server.domain.tld:4447/resource', 'https://X:Y@server.domain.tld:4447/resource'),
))
def testForceUrlDoesNotForceLowercase(url, expected):
	"""
	Complete URLs must not be forced to lowercase because they could \
	include an username / password combination for an proxy.
	"""
	assert expected == forceUrl(url)


@pytest.mark.parametrize("url", (
	'abc',
	'/abc',
	'http//server',
	1,
	True,
	None,
))
def testForceUrlWithInvalidURLsRaisesExceptions(url):
	with pytest.raises(ValueError):
		forceUrl(url)


@pytest.mark.parametrize("hostKey", (
	'abcdef78901234567890123456789012',
))
def testForceOpsiHostKey(hostKey):
	result = forceOpsiHostKey(hostKey)
	assert hostKey.lower() == result
	assert isinstance(result, str)


@pytest.mark.parametrize("hostKey", (
	'abCdeF7890123456789012345678901',  # too short
	'abCdeF78901234567890123456789012b',  # too long
	'GbCdeF78901234567890123456789012',
))
def testForceOpsiHostKeyWithInvalidHostKeysRaisesExceptions(hostKey):
	with pytest.raises(ValueError):
		forceOpsiHostKey(hostKey)


@pytest.mark.parametrize("version, expected", (
	('1.0', '1.0'),
))
def testForceProductVersion(version, expected):
	result = forceProductVersion(version)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("version", ('A1.0', ))
def testProductVersionDoesNotContainUppercase(version):
	with pytest.raises(ValueError):
		forceProductVersion(version)


@pytest.mark.parametrize("version, expected", (
	(1, '1'),
	(8, '8')
))
def testForcePackageVersion(version, expected):
	result = forcePackageVersion(version)
	assert expected == result
	assert isinstance(result, str)


@pytest.mark.parametrize("version", ('A', ))
def testPackageVersionDoesNotAcceptUppercase(version):
	with pytest.raises(ValueError):
		forcePackageVersion(version)


@pytest.mark.parametrize("productId, expectedProductId", (
	('testProduct1', 'testproduct1'),
))
def testForceProductId(productId, expectedProductId):
	result = forceProductId(productId)
	assert expectedProductId == result
	assert isinstance(result, str)


@pytest.mark.parametrize("productId", (u'äöü', 'product test'))
def testForceProductIdWithInvalidProductIdRaisesExceptions(productId):
	with pytest.raises(ValueError):
		forceProductId(productId)


@pytest.mark.parametrize("path, expected", (
	('c:\\tmp\\test.txt', u'c:\\tmp\\test.txt'),
))
def testforceFilename(path, expected):
	result = forceFilename(path)
	assert expected == result
	assert isinstance(expected, str)


@pytest.mark.parametrize("status", ('installed', 'not_installed', 'unknown'))
def testForceInstallationStatus(status):
	result = forceInstallationStatus(status)
	assert result == status
	assert isinstance(result, str)


@pytest.mark.parametrize("status", ('none', 'abc'))
def testforceInstallationStatusWithInvalidStatusRaisesExceptions(status):
	with pytest.raises(ValueError):
		forceInstallationStatus(status)


def testForceUnicodeWithInvalidStatusRaisesExceptions():
	with pytest.raises(ValueError):
		forceActionRequest('installed')


@pytest.mark.parametrize("actionRequest", (
	'setup',
	'uninstall',
	'update',
	'once',
	'always',
	'none',
	None
))
def testForceActionRequest(actionRequest):
	returned = forceActionRequest(actionRequest)
	assert returned == str(actionRequest).lower()
	assert isinstance(returned, str)


def testforceActionRequestReturnsNoneOnUndefined():
	assert forceActionRequest("undefined") is None


def testForceActionProgress():
	returned = forceActionProgress('installing 50%')
	assert returned == u'installing 50%'
	assert isinstance(returned, str)


@pytest.mark.parametrize("code, expected", (
	('xx-xxxx-xx', u'xx-Xxxx-XX'),
	('yy_yy', u'yy-YY'),
	('zz_ZZZZ', u'zz-Zzzz'),
))
def testForceLanguageCodeNormalisesCasing(code, expected):
	assert expected == forceLanguageCode(code)


@pytest.mark.parametrize("code, expected", (
	('dE', u'de'),
	('en-us', u'en-US')
))
def testForceLanguageCode(code, expected):
	assert forceLanguageCode('dE') == u'de'
	assert forceLanguageCode('en-us') == u'en-US'


def testForceLanguageCodeRaisesExceptionOnInvalidCode():
	with pytest.raises(ValueError):
		forceLanguageCode('de-DEU')


@pytest.mark.parametrize("architecture, expected", (
	('X86', u'x86'),
	('X64', u'x64'),
))
def testForcingReturnsLowercase(architecture, expected):
	assert expected == forceArchitecture(architecture)


def testForceTimeFailsIfNoTimeGiven():
	with pytest.raises(ValueError):
		forceTime('Hello World!')


@pytest.mark.parametrize("timeInfo", (
	time.time(),
	time.localtime(),
	datetime.datetime.now(),
))
def testForceTimeReturnsTimeStruct(timeInfo):
	assert isinstance(forceTime(timeInfo), time.struct_time)


@pytest.mark.parametrize("invalidMailAddress", ('infouib.de',))
def testForceEmailAddressRaisesAnExceptionOnInvalidMailAddress(invalidMailAddress):
	with pytest.raises(ValueError):
		forceEmailAddress(invalidMailAddress)


@pytest.mark.parametrize("address, expected", (
	(u'info@uib.de', 'info@uib.de'),
	(u'webmaster@somelongname.passenger-association.aero', 'webmaster@somelongname.passenger-association.aero'),
	(u'bla@name.posts-and-telecommunications.museum', 'bla@name.posts-and-telecommunications.museum'),
	(u'webmaster@bike.equipment', 'webmaster@bike.equipment'),
	(u'some.name@company.travelersinsurance', 'some.name@company.travelersinsurance'),
))
# A large list of TLDs can be found at https://publicsuffix.org/
def testForceEmailAddress(address, expected):
	assert expected == forceEmailAddress(address)


@pytest.mark.parametrize("invalidType", ('TrolololoProduct', None))
def testforceProductTypeRaisesExceptionOnUnknownType(invalidType):
	with pytest.raises(ValueError):
		forceProductType(invalidType)


@pytest.mark.parametrize("inputString", ('LocalBootProduct', 'LOCALBOOT'))
def testforceProductTypeToLocalbootProduct(inputString):
	assert 'LocalbootProduct' == forceProductType(inputString)


@pytest.mark.parametrize("inputString", ('NetbOOtProduct', 'nETbOOT'))
def testforceProductTypeToNetbootProduct(inputString):
	assert 'NetbootProduct' == forceProductType(inputString)


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


@pytest.mark.parametrize("expected, before", (
	([1], [1, 1]),
	([1, 2, 3], (1, 2, 2, 3)),
))
def testAfterForcingItemsInListAreUnique(before, expected):
	assert expected == forceUniqueList(before)


def testForceUniqueListDoesNotChangeOrder():
	assert [2, 1, 3, 5, 4] == forceUniqueList([2, 2, 1, 3, 5, 4, 1])


def testArgsDecoratorArgumentsDefaultToNone():

	@args("somearg", "someOtherArg")
	class SomeClass(object):
		def __init__(self, **kwargs):
			pass

	someObj = SomeClass()

	assert someObj.somearg is None
	assert someObj.someOtherArg is None


def testArgsDecoratorTakesKeywordArguments():

	@args("somearg", someOtherArg=forceInt)
	class SomeOtherClass(object):
		def __init__(self, **kwargs):
			pass

	someOtherObj = SomeOtherClass(someOtherArg="5")

	assert someOtherObj.somearg is None
	assert 5 == someOtherObj.someOtherArg


def testArgsDecoratorCreatesPrivateArgs():

	@args("_somearg", "_someOtherArg")
	class SomeClass(object):
		def __init__(self, **kwargs):
			pass

	someObj = SomeClass(somearg=5)

	assert 5 == someObj._somearg
	assert someObj._someOtherArg is None


def testForceFqdnRemovesTrailingDot():
	assert 'abc.example.local' == forceFqdn('abc.example.local.')


@pytest.mark.parametrize("hostname", [
	'hostname.rootzone.tld',  # complete hostname
	pytest.param('host_name.rootzone.tld', marks=pytest.mark.xfail),  # underscore
	pytest.param('hostname.tld', marks=pytest.mark.xfail),  # only domain
])
def testForceFqdnRequiresHostnameRootZoneAndTopLevelDomain(hostname):
	forceFqdn(hostname)


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
