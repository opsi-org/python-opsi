#!/usr/bin/python
# -*- coding: utf-8 -*-

from OPSI.Logger import *
from OPSI.Backend.Object import *

logger = Logger()
logger.setConsoleLevel(LOG_DEBUG)
logger.setConsoleColor(True)

someTypes = (
	1,
	None,
	True,
	time.localtime(),
	u'unicode string',
	u'utf-8 string: äöüß€'.encode('utf-8'),
	u'windows-1258 string: äöüß€'.encode('windows-1258'),
	u'utf-16 string: äöüß€'.encode('utf-16'),
	u'latin1 string: äöüß'.encode('latin-1')
)

# ----------------------------------------------------------------------- #
logger.notice(u"Testing Exception classes:")
for message in someTypes:
	error = OpsiError(message)
	logger.info(u'   %s' % error)
	logger.info( '   %s' % error)
	try:
		raise error
	except OpsiError, e:
		logger.info(u'      %s' % e)
		logger.info( '      %s' % e)

error = BackendError()
logger.info(u'   %s' % error)
try:
	raise error
except OpsiError, e:
	logger.info(u'      %s' % e)

error = BackendBadValueError(u'Bad value error test')
logger.info(u'   %s' % error)
try:
	raise error
except OpsiError, e:
	logger.info(u'      %s' % e)


# ----------------------------------------------------------------------- #
logger.notice(u"Testing type force functions")

assert forceList('x') == ['x']

assert type(forceUnicode('x')) is unicode

for i in forceUnicodeList([None, 1, 'x', u'y']):
	assert type(i) is unicode

assert forceBool('YeS') is True
assert forceBool('no') is False
assert forceBool('on') is True
assert forceBool('OFF') is False
assert forceBool(1) is True
assert forceBool('1') is True
assert forceBool(0) is False
assert forceBool('0') is False
assert forceBool(u'x') is True
assert forceBool(True) is True
assert forceBool(False) is False

for i in forceBoolList([None, 'no', 'false', '0', False]):
	assert i is False

assert forceInt('100') == 100
assert forceInt('-100') == -100
assert forceInt(long(1000000000000000)) == 1000000000000000
try:
	forceInt('abc')
except BackendBadValueError:
	pass

assert type(forceOpsiTimestamp('2000-02-02 11:12:13')) is unicode
assert forceOpsiTimestamp('20000202111213') == u'2000-02-02 11:12:13'
try:
	forceOpsiTimestamp('abc')
except BackendBadValueError:
	pass
else:
	raise Exception(u"'abc' was accepted as OpsiTimestamp")

assert forceHostId(u'client.uib.local') is u'client.uib.local'
for i in ('abc', 'abc.def', '.uib.local', 'abc.uib.x'):
	try:
		forceHostId(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as hostId" % i)

for i in  ('12345678ABCD', '12-34-56-78-Ab-cD', '12:34:56:78:ab:cd', '12-34-56:78AB-CD'):
	assert forceHardwareAddress(i) == u'12:34:56:78:ab:cd'
	assert type(forceHardwareAddress(i)) is unicode
for i in ('12345678abc', '12345678abcdef', '1-2-3-4-5-6-7', None, True):
	try:
		forceHardwareAddress(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as hardwareAddress" % i)

assert forceIPAddress('192.168.101.1') == u'192.168.101.1'
assert type(forceIPAddress('1.1.1.1')) is unicode
for i in ('1922.1.1.1', None, True, '1.1.1.1.', '2.2.2.2.2', 'a.2.3.4'):
	try:
		forceIPAddress(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as IPAddress" % i)

assert forceNetworkAddress('192.168.0.0/16') == u'192.168.0.0/16'
assert type(forceNetworkAddress('10.10.10.10/32')) is unicode
for i in ('192.168.101.1', '192.1.1.1/40', None, True, '10.10.1/24', 'a.2.3.4/0'):
	try:
		forceNetworkAddress(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as NetworkAddress" % i)


for i in ('file:///', 'file:///path/to/file', 'smb://server/path', 'https://x:y@server.domain.tld:4447/resource'):
	assert forceUrl(i) == i
	assert type(forceUrl(i)) is unicode
for i in ('abc', '/abc', 'http//server', 1, True, None):
	try:
		forceUrl(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as Url" % i)
	
assert forceOpsiHostKey('abCdeF78901234567890123456789012') == 'abcdef78901234567890123456789012'
assert type(forceOpsiHostKey('12345678901234567890123456789012')) is unicode
for i in ('abCdeF7890123456789012345678901', 'abCdeF78901234567890123456789012b', 'GbCdeF78901234567890123456789012'):
	try:
		forceOpsiHostKey(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as OpsiHostKey" % i)

assert forceProductVersion('1.0') == '1.0'
assert type(forceProductVersion('1.0')) is unicode

assert forcePackageVersion(1) == '1'
assert type(forceProductVersion('8')) is unicode

assert forceProductId('testProduct1') == 'testproduct1'
assert type(forceProductId('test-Product-1')) is unicode
for i in (u'äöü', 'product test'):
	try:
		forceProductId(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as ProductId" % i)

assert forceFilename('c:\\tmp\\test.txt') == u'c:\\tmp\\test.txt'
assert type(forceFilename('/tmp/test.txt')) is unicode


for i in ('installed', 'not_installed'):
	assert forceInstallationStatus(i) == i
	assert type(forceInstallationStatus(i)) is unicode
for i in ('none', 'abc'):
	try:
		forceInstallationStatus(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as installationStatus" % i)

for i in ('setup', 'uninstall', 'update', 'once', 'always', 'none', None):
	assert forceActionRequest(i) == str(i).lower()
	assert type(forceActionRequest(i)) is unicode
for i in ('installed'):
	try:
		forceActionRequest(i)
	except BackendBadValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as actionRequest" % i)


assert forceActionProgress('installing 50%') == u'installing 50%'
assert type(forceActionProgress('installing 50%')) is unicode






















