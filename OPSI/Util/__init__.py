# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2019 uib GmbH <info@uib.de>
# http://www.uib.de/

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
General utility functions.

This module holds various utility functions for the work with opsi.
This includes functions for (de)serialisation, converting classes from
or to JSON, working with librsync and more.

:copyright:	uib GmbH <info@uib.de>
:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import base64
import binascii
import codecs
import ipaddress
import json
import os
import random
import re
import shutil
import socket
import struct
import sys
import time
import types
import secrets
from collections import namedtuple
from hashlib import md5
from itertools import islice
from functools import lru_cache

try:
	# pyright: reportMissingImports=false
	# python3-pycryptodome installs into Cryptodome
	from Cryptodome.Cipher import Blowfish
	from Cryptodome.PublicKey import RSA
	from Cryptodome.Util.number import bytes_to_long
except ImportError:
	# PyCryptodome from pypi installs into Crypto
	from Crypto.Cipher import Blowfish
	from Crypto.PublicKey import RSA
	from Crypto.Util.number import bytes_to_long

from OPSI.Logger import Logger, LOG_DEBUG
from OPSI.Types import (forceBool, forceFilename, forceFqdn, forceUnicode)

OPSIObject = None  # pylint: disable=invalid-name

__all__ = (
	'BLOWFISH_IV', 'PickleString',
	'RANDOM_DEVICE', 'blowfishDecrypt', 'blowfishEncrypt',
	'chunk', 'compareVersions', 'deserialize',
	'findFiles', 'findFilesGenerator', 'formatFileSize', 'fromJson', 'generateOpsiHostKey',
	'getfqdn', 'ipAddressInNetwork', 'isRegularExpressionPattern',
	'md5sum', 'objectToBash', 'objectToBeautifiedText', 'objectToHtml',
	'randomString', 'removeDirectory', 'removeUnit',
	'replaceSpecialHTMLCharacters', 'serialize', 'timestamp', 'toJson'
)

logger = Logger()

BLOWFISH_IV = b"OPSI1234"
RANDOM_DEVICE = "/dev/urandom"
UNIT_REGEX = re.compile(r'^(\d+\.*\d*)\s*([\w]{0,4})$')
UNIT_REGEX = re.compile(r'^(\d+\.*\d*)\s*(\w{0,4})$')
_ACCEPTED_CHARACTERS = (
	"abcdefghijklmnopqrstuvwxyz"
	"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	"0123456789"
)

Version = namedtuple('Version', 'product package')


class CryptoError(ValueError):
	pass


class BlowfishError(CryptoError):
	pass


class PickleString(str):

	def __getstate__(self):
		return base64.standard_b64encode(self)

	def __setstate__(self, state):
		self = base64.standard_b64decode(state)  # pylint: disable=self-cls-assignment


def deserialize(obj, preventObjectCreation=False):
	"""
	Deserialization of `obj`.

	This function will deserialize objects from JSON into opsi \
compatible objects.
	In case `obj` is a list contained elements are deserialized.
	In case `obj` is a dict the values are deserialized.

	In case `obj` is a dict and holds a key *type* and \
`preventObjectCreation` is `True` it will be tried to create an opsi \
object instance from it

	:type obj: object
	:type preventObjectCreation: bool
	"""
	global OPSIObject  # pylint: disable=global-statement,invalid-name
	if OPSIObject is None:
		import OPSI.Object as OPSIObject  # pylint: disable=redefined-outer-name,import-outside-toplevel

	if isinstance(obj, list):
		return [deserialize(element, preventObjectCreation=preventObjectCreation) for element in obj]

	if isinstance(obj, dict):
		if not preventObjectCreation and 'type' in obj:
			try:
				objectClass = getattr(OPSIObject, obj['type'])
				return objectClass.fromHash(obj)
			except Exception as err:  # pylint: disable=broad-except
				logger.debug("Failed to get object from dict %s: %s", obj, err)
				return obj

		return {
			key: deserialize(value, preventObjectCreation=preventObjectCreation)
			for key, value in obj.items()
		}

	return obj


def serialize(obj):
	"""
	Serialize `obj`.

	It will turn an object into a JSON-compatible format - consisting \
of strings, dicts, lists or numbers.

	:return: a JSON-compatible serialisation of the input.
	"""
	if isinstance(obj, str):
		return obj

	try:
		return obj.serialize()
	except AttributeError:
		if isinstance(obj, (list, set, types.GeneratorType)):
			return [serialize(tempObject) for tempObject in obj]
		if isinstance(obj, dict):
			return {key: serialize(value) for key, value in obj.items()}

	return obj


def formatFileSize(sizeInBytes):
	if sizeInBytes < 1024:
		return '%i' % sizeInBytes
	if sizeInBytes < 1048576:  # 1024**2
		return '%iK' % (sizeInBytes / 1024)
	if sizeInBytes < 1073741824:  # 1024**3
		return '%iM' % (sizeInBytes / 1048576)
	if sizeInBytes < 1099511627776:  # 1024**4
		return '%iG' % (sizeInBytes / 1073741824)
	return '%iT' % (sizeInBytes / 1099511627776)


def fromJson(obj, objectType=None, preventObjectCreation=False):
	if isinstance(obj, bytes):
		# Allow decoding errors (workaround for opsi-script bug)
		obj = obj.decode("utf-8", "replace")
	obj = json.loads(obj)
	if isinstance(obj, dict) and objectType:
		obj['type'] = objectType
	return deserialize(obj, preventObjectCreation=preventObjectCreation)


def toJson(obj, ensureAscii=False):
	return json.dumps(serialize(obj), ensure_ascii=ensureAscii)


def md5sum(filename):
	""" Returns the md5sum of the given file. """
	md5object = md5()

	with open(filename, 'rb') as fileToHash:
		for data in iter(lambda: fileToHash.read(524288), b''):
			md5object.update(data)

	return md5object.hexdigest()


def randomString(length, characters=_ACCEPTED_CHARACTERS):
	"""
	Generates a random string for a given length.

	:param characters: The characters to choose from. This defaults to 0-9a-Z.
	"""
	return ''.join(random.choice(characters) for _ in range(length))


def generateOpsiHostKey(forcePython=False):  # pylint: disable=unused-argument
	"""
	Generates an random opsi host key.

	On Python 3.5 or lower this will try to make use of an existing
	random device.
	As a fallback the generation is done in plain Python.

	:param forcePython: Force the usage of Python for host key generation.
	:rtype: str
	"""
	return secrets.token_hex(16)


def timestamp(secs=0, dateOnly=False):
	''' Returns a timestamp of the current system time format: YYYY-mm-dd[ HH:MM:SS] '''
	if not secs:
		secs = time.time()
	if dateOnly:
		return time.strftime("%Y-%m-%d", time.localtime(secs))
	return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(secs))


def objectToBeautifiedText(obj):
	return json.dumps(serialize(obj), indent=4, ensure_ascii=False)


def objectToBash(obj, bashVars=None, level=0):  # pylint: disable=too-many-branches
	"""
	Converts `obj` into bash-compatible format.

	:type bashVars: dict
	:type level: int
	:rtype: dict
	"""
	if bashVars is None:
		bashVars = {}

	if level == 0:
		obj = serialize(obj)
		varName = 'RESULT'
		compress = True
	else:
		varName = 'RESULT%d' % level
		compress = False

	try:
		obj = obj.serialize()
	except AttributeError:
		pass

	try:
		append = bashVars[varName].append
	except KeyError:
		emptyList = []
		bashVars[varName] = emptyList
		append = emptyList.append

	if isinstance(obj, (list, set)):
		append('(\n')
		for element in obj:
			if isinstance(element, (dict, list)):
				level += 1
				objectToBash(element, bashVars, level)
				append('RESULT%d=${RESULT%d[*]}' % (level, level))
			else:
				objectToBash(element, bashVars, level)
			append('\n')
		append(')')
	elif isinstance(obj, dict):
		append('(\n')
		for (key, value) in obj.items():
			append('%s=' % key)
			if isinstance(value, (dict, list)):
				level += 1
				objectToBash(value, bashVars, level)
				append('${RESULT%d[*]}' % level)
			else:
				objectToBash(value, bashVars, level)
			append('\n')
		append(')')
	elif obj is None:
		append('""')
	else:
		append(f'"{obj}"')

	if compress:
		for key, value in bashVars.items():
			bashVars[key] = ''.join(value)

	return bashVars


def objectToHtml(obj, level=0):  # pylint: disable=too-many-branches
	if level == 0:
		obj = serialize(obj)

	html = []
	append = html.append

	if isinstance(obj, (list, set)):
		append('[')
		if len(obj) > 0:
			append('<div style="padding-left: 3em;">')
			for i, currentElement in enumerate(obj):
				append(objectToHtml(currentElement, level + 1))
				if i < len(obj) - 1:
					append(',<br />\n')
			append('</div>')
		append(']')
	elif isinstance(obj, dict):
		append('{')
		if len(obj) > 0:
			append('<div style="padding-left: 3em;">')
			for i, (key, value) in enumerate(obj.items()):
				append('<font class="json_key">')
				append(objectToHtml(key))
				append('</font>: ')
				append(objectToHtml(value, level + 1))
				if i < len(obj) - 1:
					append(',<br />\n')
			append('</div>')
		append('}')
	elif isinstance(obj, bool):
		append(str(obj).lower())
	elif obj is None:
		append('null')
	else:
		if isinstance(obj, str):
			append(replaceSpecialHTMLCharacters(obj).join(('"', '"')))
		else:
			append(replaceSpecialHTMLCharacters(obj))

	return ''.join(html)


def replaceSpecialHTMLCharacters(text):
	return str(text) \
		.replace('\r', '')\
		.replace('\t', '   ')\
		.replace('&', '&amp;')\
		.replace('"', '&quot;')\
		.replace("'", '&apos;')\
		.replace(' ', '&nbsp;')\
		.replace('<', '&lt;')\
		.replace('>', '&gt;')\
		.replace('\n', '<br />\n')


def combineVersions(obj):
	"""
	Returns the combination of product and package version.

	:type obj: Product, ProductOnClient, ProductOnDepot
	:return: The version.
	:rtype: str
	"""
	return '{0.productVersion}-{0.packageVersion}'.format(obj)


def compareVersions(v1, condition, v2):  # pylint: disable=invalid-name,too-many-locals,too-many-branches,too-many-statements
	"""
	Compare the versions `v1` and `v2` with the given `condition`.

	`condition` may be one of `==`, `<`, `<=`, `>`, `>=`.

	Versions will be made the same length by appending '.0' until they
	match.
	If `1.0.0` and `2` are compared the latter will be viewed as `2.0.0`.
	If a version contains a `~` that character and everything following
	it will not be taken into account.

	:raises ValueError: If invalid value for version or condition if given.
	:rtype: bool
	:return: If the comparison matches this will return True.
	"""
	def removePartAfterWave(versionString):
		if "~" in versionString:
			return versionString[:versionString.find("~")]
		return versionString

	def splitProductAndPackageVersion(versionString):
		productVersion = packageVersion = '0'

		match = re.search(r'^\s*([\w.]+)-*([\w.]*)\s*$', versionString)
		if not match:
			raise ValueError("Bad version string '%s'" % versionString)

		productVersion = match.group(1)
		if match.group(2):
			packageVersion = match.group(2)

		return Version(productVersion, packageVersion)

	def makeEqualLength(first, second):
		while len(first) < len(second):
			first.append('0')

		while len(second) < len(first):
			second.append('0')

	def splitValue(value):
		match = re.search(r'^(\d+)(\D*.*)$', value)
		if match:
			return int(match.group(1)), match.group(2)
		match = re.search(r'^(\D+)(\d*.*)$', value)
		if match:
			return match.group(1), match.group(2)

		return '', value

	if not condition:
		condition = '=='
	if condition not in ('==', '=', '<', '<=', '>', '>='):
		raise ValueError("Bad condition '%s'" % condition)
	if condition == '=':
		condition = '=='

	v1 = removePartAfterWave(str(v1))
	v2 = removePartAfterWave(str(v2))

	version = splitProductAndPackageVersion(v1)
	otherVersion = splitProductAndPackageVersion(v2)
	logger.trace("Versions: %s, %s", version, otherVersion)

	comparisons = (
		(version.product, otherVersion.product),
		(version.package, otherVersion.package)
	)

	for first, second in comparisons:
		logger.trace("Comparing %s with %s...", first, second)
		firstParts = first.split('.')
		secondParts = second.split('.')
		makeEqualLength(firstParts, secondParts)

		for value, otherValue in zip(firstParts, secondParts):
			while value or otherValue:
				cv1, value = splitValue(value)
				cv2, otherValue = splitValue(otherValue)

				if cv1 == '':
					cv1 = chr(1)
				if cv2 == '':
					cv2 = chr(1)

				if cv1 == cv2:
					logger.trace("%s == %s => continue", cv1, cv2)
					continue

				if not isinstance(cv1, int):
					cv1 = f"'{cv1}'"
				if not isinstance(cv2, int):
					cv2 = f"'{cv2}'"

				logger.trace("Is %s %s %s?", cv1, condition, cv2)
				conditionFulfilled = eval("%s %s %s" % (cv1, condition, cv2))  # pylint: disable=eval-used
				if not conditionFulfilled:
					logger.debug("Unfulfilled condition: %s %s %s", version, condition, otherVersion)
					return False

				logger.debug("Fulfilled condition: %s %s %s", version, condition, otherVersion)
				return True

	if '=' not in condition:
		logger.debug("Unfulfilled condition: %s %s %s", version, condition, otherVersion)
		return False

	logger.debug("Fulfilled condition: %s %s %s", version, condition, otherVersion)
	return True


def removeUnit(x):  # pylint: disable=invalid-name,too-many-return-statements
	'''
	Take a string representing a byte-based size and return the
	value in bytes.

	:param x: str
	:returns: `x` in bytes.
	:rtype: int or float
	'''
	x = str(x)
	match = UNIT_REGEX.search(x)
	if not match:
		return x

	if '.' in match.group(1):
		value = float(match.group(1))
	else:
		value = int(match.group(1))

	unit = match.group(2)
	mult = 1000

	if unit.lower().endswith('hz'):
		unit = unit[:-2]
	elif unit.lower().endswith('bits'):
		mult = 1024
		unit = unit[:-4]
	elif unit.lower().endswith('b'):
		mult = 1024
		unit = unit[:-1]
	elif unit.lower().endswith(('s', 'v')):
		unit = unit[:-1]

	if unit.endswith('n'):
		return float(value) / (mult * mult)
	if unit.endswith('m'):
		return float(value) / mult
	if unit.lower().endswith('k'):
		return value * mult
	if unit.endswith('M'):
		return value * mult * mult
	if unit.endswith('G'):
		return value * mult * mult * mult

	return value


def blowfishEncrypt(key, cleartext):
	"""
	Takes `cleartext` string, returns hex-encoded,
	blowfish-encrypted string.

	:type key: str
	:type cleartext: str
	:raises BlowfishError: In case things go wrong.
	:rtype: str
	"""
	cleartext = forceUnicode(cleartext)
	key = _prepareBlowfishKey(key)

	while len(cleartext) % 8 != 0:
		# Fill up with \0 until length is a mutiple of 8
		cleartext += chr(0)

	blowfish = Blowfish.new(key, Blowfish.MODE_CBC, BLOWFISH_IV)
	try:
		crypt = blowfish.encrypt(cleartext.encode("utf-8"))
	except Exception as err:
		logger.debug(err, exc_info=True)
		raise BlowfishError("Failed to encrypt") from err

	return crypt.hex()


def blowfishDecrypt(key, crypt):
	"""
	Takes hex-encoded, blowfish-encrypted string,
	returns cleartext string.

	:type key: str
	:param crypt: The encrypted text as hex.
	:type crypt: str
	:raises BlowfishError: In case things go wrong.
	:rtype: str
	"""
	crypt = bytes.fromhex(crypt)
	key = _prepareBlowfishKey(key)

	blowfish = Blowfish.new(key, Blowfish.MODE_CBC, BLOWFISH_IV)
	try:
		cleartext = blowfish.decrypt(crypt)
	except Exception as err:
		logger.debug(err, exc_info=True)
		raise BlowfishError("Failed to decrypt") from err

	# Remove possible \0-chars
	if b'\0' in cleartext:
		cleartext = cleartext[:cleartext.find(b'\0')]

	try:
		return cleartext.decode("utf-8")
	except Exception as err:
		logger.error(err)
		raise BlowfishError("Failed to convert decrypted text to unicode.") from err


def _prepareBlowfishKey(key: str) -> bytes:
	"Transform the key into hex."
	try:
		key = forceUnicode(key).encode()
		return codecs.decode(key, "hex")
	except (binascii.Error, Exception) as err:
		raise BlowfishError(f"Unable to prepare key: {err}") from err


def findFilesGenerator(  # pylint: disable=too-many-branches,too-many-locals,too-many-arguments,too-many-statements
	directory, prefix='',
	excludeDir=None, excludeFile=None, includeDir=None, includeFile=None,
	returnDirs=True, returnLinks=True, followLinks=False,
	repository=None
):
	directory = forceFilename(directory)
	prefix = forceUnicode(prefix)

	if excludeDir:
		if not isRegularExpressionPattern(excludeDir):
			excludeDir = re.compile(forceUnicode(excludeDir))
	else:
		excludeDir = None

	if excludeFile:
		if not isRegularExpressionPattern(excludeFile):
			excludeFile = re.compile(forceUnicode(excludeFile))
	else:
		excludeFile = None

	if includeDir:
		if not isRegularExpressionPattern(includeDir):
			includeDir = re.compile(forceUnicode(includeDir))
	else:
		includeDir = None

	if includeFile:
		if not isRegularExpressionPattern(includeFile):
			includeFile = re.compile(forceUnicode(includeFile))
	else:
		includeFile = None

	returnDirs = forceBool(returnDirs)
	returnLinks = forceBool(returnLinks)
	followLinks = forceBool(followLinks)

	if repository:
		islink = repository.islink
		isdir = repository.isdir
		listdir = repository.listdir
	else:
		islink = os.path.islink
		isdir = os.path.isdir
		listdir = os.listdir

	for entry in listdir(directory):
		pp = os.path.join(prefix, entry)
		dp = os.path.join(directory, entry)
		isLink = False
		if islink(dp):
			isLink = True
			if not returnLinks and not followLinks:
				continue
		if isdir(dp) and (not isLink or followLinks):
			if excludeDir and re.search(excludeDir, entry):
				logger.debug("Excluding dir '%s' and containing files", entry)
				continue
			if includeDir:
				if not re.search(includeDir, entry):
					continue
				logger.debug("Including dir '%s' and containing files", entry)
			if returnDirs:
				yield pp
			yield from findFilesGenerator(
				directory=dp,
				prefix=pp,
				excludeDir=excludeDir,
				excludeFile=excludeFile,
				includeDir=includeDir,
				includeFile=includeFile,
				returnDirs=returnDirs,
				returnLinks=returnLinks,
				followLinks=followLinks,
				repository=repository
			)
			continue

		if excludeFile and re.search(excludeFile, entry):
			if isLink:
				logger.debug("Excluding link '%s'", entry)
			else:
				logger.debug("Excluding file '%s'", entry)
			continue

		if includeFile:
			if not re.search(includeFile, entry):
				continue
			if isLink:
				logger.debug("Including link '%s'", entry)
			else:
				logger.debug("Including file '%s'", entry)
		yield pp

def findFiles(  # pylint: disable=too-many-arguments
	directory, prefix='',
	excludeDir=None, excludeFile=None, includeDir=None, includeFile=None,
	returnDirs=True, returnLinks=True, followLinks=False,
	repository=None
):
	return list(
		findFilesGenerator(
			directory, prefix,
			excludeDir, excludeFile, includeDir, includeFile,
			returnDirs, returnLinks, followLinks,
			repository
		)
	)

if sys.version_info >= (3, 7):
	def isRegularExpressionPattern(object):  # pylint: disable=redefined-builtin
		return isinstance(object, re.Pattern)
else:
	def isRegularExpressionPattern(object):  # pylint: disable=redefined-builtin
		return "SRE_Pattern" in str(type(object))


def ipAddressInNetwork(ipAddress, networkAddress):
	"""
	Checks if the given IP address is in the given network range.
	Returns ``True`` if the given address is part of the network.
	Returns ``False`` if the given address is not part of the network.

	:param ipAddress: The IP which we check.
	:type ipAddress: str
	:param networkAddress: The network address written with slash notation.
	:type networkAddress: str
	"""
	if not isinstance(ipAddress, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
		ipAddress = ipaddress.ip_address(ipAddress)
	if isinstance(ipAddress, ipaddress.IPv6Address) and ipAddress.ipv4_mapped:
		ipAddress = ipAddress.ipv4_mapped

	if not isinstance(networkAddress, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
		networkAddress = ipaddress.ip_network(networkAddress)

	return ipAddress in networkAddress


def getfqdn(name='', conf=None):
	"""
	Get the fqdn.

	If ``name`` is not given it will try various ways to get a valid
	fqdn from the current host.
	If ``conf`` but no name is given it will try to read the FQDN from
	the specified configuration file.
	"""
	if not name:
		try:
			return forceFqdn(os.environ["OPSI_HOSTNAME"])
		except KeyError:
			# not set in environment.
			pass

		# lazy import to avoid circular dependency
		from OPSI.Util.Config import getGlobalConfig  # pylint: disable=import-outside-toplevel

		if conf is not None:
			hostname = getGlobalConfig('hostname', conf)
		else:
			hostname = getGlobalConfig('hostname')

		if hostname:
			return forceFqdn(hostname)

	return forceFqdn(socket.getfqdn(name))


def removeDirectory(directory):
	"""
	Removing an directory.

	If this fails with shutil it will try to use system calls.

	.. versionadded:: 4.0.5.1


	:param directory: Path to the directory
	:tye directory: str
	"""
	logger.debug('Removing directory: %s', directory)
	try:
		shutil.rmtree(directory)
	except UnicodeDecodeError:
		# See http://bugs.python.org/issue3616
		logger.info(
			'Client data directory seems to contain filenames '
			'with unicode characters. Trying fallback.'
		)

		# late import to avoid circular dependency
		import OPSI.System  # pylint: disable=import-outside-toplevel
		OPSI.System.execute('rm -rf {dir}'.format(dir=directory))


def chunk(iterable, size):
	"""
	Returns chunks (parts) of a specified `size` from `iterable`.
	It will not pad (fill) the chunks.

	This works lazy and therefore can be used with any iterable without
	much overhead.

	Original recipe from http://stackoverflow.com/a/22045226
	"""
	it = iter(iterable)
	return iter(lambda: tuple(islice(it, size)), ())


@lru_cache(maxsize=4)
def getPublicKey(data):
	# Key type can be found in 4:11.
	rest = data[11:]
	count = 0
	mp = []
	for _ in range(2):
		length = struct.unpack('>L', rest[count:count + 4])[0]
		mp.append(bytes_to_long(rest[count + 4:count + 4 + length]))
		count += 4 + length

	return RSA.construct((mp[1], mp[0]))
