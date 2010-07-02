#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from OPSI.Logger import *
from OPSI.Object import *

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

error = ValueError(u'Bad value error test')
logger.info(u'   %s' % error)
try:
	raise error
except ValueError, e:
	logger.info(u'      %s' % e)


# ----------------------------------------------------------------------- #
logger.notice(u"Testing type force functions")

client1 = OpsiClient(
	id = 'test1.uib.local',
	description = 'Test client 1',
	notes = 'Notes ...',
	hardwareAddress = '00:01:02:03:04:05',
	ipAddress = '192.168.1.100',
	lastSeen = '2009-01-01 00:00:00',
	opsiHostKey = '45656789789012789012345612340123'
)
j = client1.toJson()
h = client1.toHash()
assert isinstance(forceObjectClass(j, Host), Host)
assert isinstance(forceObjectClass(j, OpsiClient), OpsiClient)
assert isinstance(forceObjectClass(h, Host), Host)
assert isinstance(forceObjectClass(h, OpsiClient), OpsiClient)

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
except ValueError:
	pass

assert forceOct('666') == 0666
assert forceOct('0666') == 0666
assert forceOct(0666) == 0666

assert type(forceOpsiTimestamp('2000-02-02 11:12:13')) is unicode
assert forceOpsiTimestamp('20000202111213') == u'2000-02-02 11:12:13'
try:
	forceOpsiTimestamp('abc')
except ValueError:
	pass
else:
	raise Exception(u"'abc' was accepted as OpsiTimestamp")

assert forceHostId(u'client.uib.local') is u'client.uib.local'
for i in ('abc', 'abc.def', '.uib.local', 'abc.uib.x'):
	try:
		forceHostId(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as hostId" % i)
assert forceHostId(u'client.sub.uib.local') is u'client.sub.uib.local'

for i in  ('12345678ABCD', '12-34-56-78-Ab-cD', '12:34:56:78:ab:cd', '12-34-56:78AB-CD'):
	assert forceHardwareAddress(i) == u'12:34:56:78:ab:cd'
	assert type(forceHardwareAddress(i)) is unicode
for i in ('12345678abc', '12345678abcdef', '1-2-3-4-5-6-7', None, True):
	try:
		forceHardwareAddress(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as hardwareAddress" % i)

assert forceIPAddress('192.168.101.1') == u'192.168.101.1'
assert type(forceIPAddress('1.1.1.1')) is unicode
for i in ('1922.1.1.1', None, True, '1.1.1.1.', '2.2.2.2.2', 'a.2.3.4'):
	try:
		forceIPAddress(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as IPAddress" % i)

assert forceNetworkAddress('192.168.0.0/16') == u'192.168.0.0/16'
assert type(forceNetworkAddress('10.10.10.10/32')) is unicode
for i in ('192.168.101.1', '192.1.1.1/40', None, True, '10.10.1/24', 'a.2.3.4/0'):
	try:
		forceNetworkAddress(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as NetworkAddress" % i)


for i in ('file:///', 'file:///path/to/file', 'smb://server/path', 'https://x:y@server.domain.tld:4447/resource'):
	assert forceUrl(i) == i
	assert type(forceUrl(i)) is unicode
for i in ('abc', '/abc', 'http//server', 1, True, None):
	try:
		forceUrl(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as Url" % i)
	
assert forceOpsiHostKey('abCdeF78901234567890123456789012') == 'abcdef78901234567890123456789012'
assert type(forceOpsiHostKey('12345678901234567890123456789012')) is unicode
for i in ('abCdeF7890123456789012345678901', 'abCdeF78901234567890123456789012b', 'GbCdeF78901234567890123456789012'):
	try:
		forceOpsiHostKey(i)
	except ValueError:
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
	except ValueError:
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
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as installationStatus" % i)

for i in ('setup', 'uninstall', 'update', 'once', 'always', 'none', None):
	assert forceActionRequest(i) == str(i).lower()
	assert type(forceActionRequest(i)) is unicode
for i in ('installed'):
	try:
		forceActionRequest(i)
	except ValueError:
		pass
	else:
		raise Exception(u"'%s' was accepted as actionRequest" % i)


assert forceActionProgress('installing 50%') == u'installing 50%'
assert type(forceActionProgress('installing 50%')) is unicode


assert forceLanguageCode('dE') == u'de'
assert forceLanguageCode('en-us') == u'en-US'
try:
	forceLanguageCode('de-DEU')
except ValueError:
	pass
else:
	raise Exception(u"'de-DEU' was accepted as languageCode")
assert forceLanguageCode('xx-xxxx-xx') == u'xx-Xxxx-XX'
assert forceLanguageCode('yy_yy') == u'yy-YY'
assert forceLanguageCode('zz_ZZZZ') == u'zz-Zzzz'


assert forceArchitecture('X86') == u'x86'
assert forceArchitecture('X64') == u'x64'

forceTime(time.time())
forceTime(time.localtime())

assert forceEmailAddress('info@uib.de') == u'info@uib.de'
try:
	forceEmailAddress('infouib.de')
except ValueError:
	pass
else:
	raise Exception(u"'infouib.de' was accepted as a-mail address")


getPossibleClassAttributes(Host)

obj1 = OpsiConfigserver(
	id                  = 'configserver1.uib.local',
	opsiHostKey         = '71234545689056789012123678901234',
	depotLocalUrl       = 'file:///opt/pcbin/install',
	depotRemoteUrl      = u'smb://configserver1/opt_pcbin/install',
	repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
	repositoryRemoteUrl = u'webdavs://configserver1:4447/repository',
	description         = 'The configserver',
	notes               = 'Config 1',
	hardwareAddress     = None,
	ipAddress           = None,
	inventoryNumber     = '00000000001',
	networkAddress      = '192.168.1.0/24',
	maxBandwidth        = 10000
)

obj2 = OpsiConfigserver(
	id                  = 'configserver1.uib.local',
	opsiHostKey         = '71234545689056789012123678901234',
	depotLocalUrl       = 'file:///opt/pcbin/install',
	depotRemoteUrl      = u'smb://configserver1/opt_pcbin/install',
	repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
	repositoryRemoteUrl = u'webdavs://configserver1:4447/repository',
	description         = 'The configserver',
	notes               = 'Config 1',
	hardwareAddress     = None,
	ipAddress           = None,
	inventoryNumber     = '00000000001',
	networkAddress      = '192.168.1.0/24',
	maxBandwidth        = 10000
)

assert obj1 == obj2
obj2 = obj1
assert obj1 == obj2

obj2 = OpsiDepotserver(
	id                  = 'depotserver1.uib.local',
	opsiHostKey         = '19012334567845645678901232789012',
	depotLocalUrl       = 'file:///opt/pcbin/install',
	depotRemoteUrl      = 'smb://depotserver1.uib.local/opt_pcbin/install',
	repositoryLocalUrl  = 'file:///var/lib/opsi/repository',
	repositoryRemoteUrl = 'webdavs://depotserver1.uib.local:4447/repository',
	description         = 'A depot',
	notes               = 'D€pot 1',
	hardwareAddress     = None,
	ipAddress           = None,
	inventoryNumber     = '00000000002',
	networkAddress      = '192.168.2.0/24',
	maxBandwidth        = 10000
)
assert obj1 != obj2

obj2 = {"test": 123}
assert obj1 != obj2

obj1 = LocalbootProduct(
	id                 = 'product2',
	name               = u'Product 2',
	productVersion     = '2.0',
	packageVersion     = 'test',
	licenseRequired    = False,
	setupScript        = "setup.ins",
	uninstallScript    = u"uninstall.ins",
	updateScript       = "update.ins",
	alwaysScript       = None,
	onceScript         = None,
	priority           = 0,
	description        = None,
	advice             = "",
	productClassIds    = ['localboot-products'],
	windowsSoftwareIds = ['{98723-7898adf2-287aab}', 'xxxxxxxx']
)
obj2 = LocalbootProduct(
	id                 = 'product2',
	name               = u'Product 2',
	productVersion     = '2.0',
	packageVersion     = 'test',
	licenseRequired    = False,
	setupScript        = "setup.ins",
	uninstallScript    = u"uninstall.ins",
	updateScript       = "update.ins",
	alwaysScript       = None,
	onceScript         = None,
	priority           = 0,
	description        = None,
	advice             = "",
	productClassIds    = ['localboot-products'],
	windowsSoftwareIds = ['xxxxxxxx', '{98723-7898adf2-287aab}']
)
assert obj1 == obj2



