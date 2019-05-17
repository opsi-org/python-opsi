# -*- coding: utf-8 -*-

# This module is part of the desktop management solution opsi
# (open pc server integration) http://www.opsi.org

# Copyright (C) 2006-2019 uib GmbH - http://www.uib.de/

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
Working with files.

This includes classes not only useful for reading and writing but
parsing files for information.

:author: Jan Schneider <j.schneider@uib.de>
:author: Niko Wenselowski <n.wenselowski@uib.de>
:license: GNU Affero General Public License version 3
"""

import builtins
import codecs
import functools
import locale
import os
import re
import threading
import time
from configparser import RawConfigParser, SafeConfigParser
from io import StringIO
from itertools import islice

from OPSI.Exceptions import BackendBadValueError, BackendMissingDataError
from OPSI.Logger import Logger
from OPSI.Types import (forceArchitecture, forceBool, forceDict,
	forceEmailAddress, forceFilename, forceHardwareAddress,
	forceHardwareDeviceId, forceHardwareVendorId, forceHostname, forceInt,
	forceIPAddress, forceList, forceOct, forceProductId, forceTime,
	forceUnicode, forceUnicodeList, forceUnicodeLower, forceUnicodeLowerList)
from OPSI.System import which, execute
from OPSI.Util import ipAddressInNetwork

if os.name == 'posix':
	import fcntl
	import grp
	import pwd
elif os.name == 'nt':
	import win32con
	import win32file
	import pywintypes

logger = Logger()


def requiresParsing(function):
	"""
	Decorator that calls parse() on unparsed configs.
	"""
	@functools.wraps(function)
	def parsedFile(self, *args, **kwargs):
		if not self._parsed:
			self.parse()

		return function(self, *args, **kwargs)

	return parsedFile


class File(object):
	def __init__(self, filename):
		self._filename = forceFilename(filename)
		self._fileHandle = None

	def getFilename(self):
		return self._filename

	def setFilename(self, filename):
		self._filename = forceFilename(filename)

	def exists(self):
		return os.path.exists(self._filename)

	def delete(self):
		if os.path.exists(self._filename):
			os.unlink(self._filename)

	def chown(self, user, group):
		if os.name == 'nt':
			logger.warning(u"Not implemented on windows")
			return
		uid = -1
		if isinstance(user, int):
			if user > -1:
				uid = user
		elif user is not None:
			try:
				uid = pwd.getpwnam(user)[2]
			except KeyError:
				raise ValueError(u"Unknown user '%s'" % user)

		gid = -1
		if isinstance(group, int):
			if group > -1:
				gid = group
		elif group is not None:
			try:
				gid = grp.getgrnam(group)[2]
			except KeyError:
				raise ValueError(u"Unknown group '%s'" % group)

		os.chown(self._filename, uid, gid)

	def chmod(self, mode):
		mode = forceOct(mode)
		os.chmod(self._filename, mode)

	def create(self, user=None, group=None, mode=None):
		if not os.path.exists(self._filename):
			self.open('w')
			self.close()

		if user is not None or group is not None:
			self.chown(user, group)
		if mode is not None:
			self.chmod(mode)

	def open(self, mode='r'):
		self._fileHandle = builtins.open(self._filename, mode)
		return self._fileHandle

	def close(self):
		if not self._fileHandle:
			return
		self._fileHandle.close()
		self._fileHandle = None

	def __getattr__(self, attr):
		if attr in self.__dict__:
			return self.__dict__[attr]
		elif self.__dict__['_fileHandle']:
			return getattr(self.__dict__['_fileHandle'], attr)

	def __getstate__(self):
		state = self.__dict__.copy()
		file = self._fileHandle
		state['_fileHandle'] = None
		state['fileState'] = {}
		state['fileState']['closed'] = file.closed
		state['fileState']['encoding'] = file.encoding
		state['fileState']['mode'] = file.mode
		state['fileState']['name'] = file.name
		state['fileState']['newlines'] = file.newlines
		state['fileState']['softspace'] = file.softspace
		state['fileState']['position'] = file.tell()
		return state

	def __setstate__(self, state):
		self.__dict__, self.fileState = state.copy(), None
		self.setFilename(state['fileState']['name'])
		if not state['fileState']['closed']:
			self.open(state['fileState']['mode'])
			self._fileHandle.encoding = state['fileState']['encoding']
			self._fileHandle.newlines = state['fileState']['newlines']
			self._fileHandle.softspace = state['fileState']['softspace']
			self.seek(state['fileState']['position'])


class LockableFile(File):
	_fileLockLock = threading.Lock()

	def __init__(self, filename, lockFailTimeout=2000):
		File.__init__(self, filename)
		self._lockFailTimeout = forceInt(lockFailTimeout)

	def open(self, mode='r', encoding=None, errors='replace'):
		truncate = False
		if mode in ('w', 'wb') and os.path.exists(self._filename):
			if mode == 'w':
				mode = 'r+'
				truncate = True
			elif mode == 'wb':
				mode = 'rb+'
				truncate = True
		if encoding:
			self._fileHandle = codecs.open(self._filename, mode, encoding, errors)
		else:
			self._fileHandle = builtins.open(self._filename, mode)
		self._lockFile(mode)
		if truncate:
			self._fileHandle.seek(0)
			self._fileHandle.truncate()
		return self._fileHandle

	def close(self):
		if not self._fileHandle:
			return
		self._fileHandle.flush()
		File.close(self)

	def _lockFile(self, mode='r'):
		timeout = 0
		while timeout < self._lockFailTimeout:
			# While not timed out and not locked
			logger.debug("Trying to lock file '%s' (%s/%s)" % (self._filename, timeout, self._lockFailTimeout))
			try:
				if os.name == 'posix':
					# Flags for exclusive, non-blocking lock
					flags = fcntl.LOCK_EX | fcntl.LOCK_NB
					if mode in ('r', 'rb'):
						# Flags for shared, non-blocking lock
						flags = fcntl.LOCK_SH | fcntl.LOCK_NB
					fcntl.flock(self._fileHandle.fileno(), flags)
				elif os.name == 'nt':
					flags = win32con.LOCKFILE_EXCLUSIVE_LOCK | win32con.LOCKFILE_FAIL_IMMEDIATELY
					if mode in ('r', 'rb'):
						flags = win32con.LOCKFILE_FAIL_IMMEDIATELY
					hfile = win32file._get_osfhandle(self._fileHandle.fileno())
					win32file.LockFileEx(hfile, flags, 0, 0x7fff0000, pywintypes.OVERLAPPED())
			except IOError:
				# increase timeout counter, sleep 100 millis
				timeout += 100
				time.sleep(0.1)
				continue
			# File successfully locked
			logger.debug("File '%s' locked after %d millis" % (self._filename, timeout))
			return self._fileHandle

		File.close(self)
		# File lock failed => raise IOError
		raise IOError("Failed to lock file '%s' after %d millis" % (self._filename, self._lockFailTimeout))

	def _unlockFile(self):
		if not self._fileHandle:
			return
		if os.name == 'posix':
			fcntl.flock(self._fileHandle.fileno(), fcntl.LOCK_UN)
		elif os.name == 'nt':
			hfile = win32file._get_osfhandle(self._fileHandle.fileno())
			win32file.UnlockFileEx(hfile, 0, 0x7fff0000, pywintypes.OVERLAPPED())


class TextFile(LockableFile):
	def __init__(self, filename, lockFailTimeout=2000):
		LockableFile.__init__(self, filename, lockFailTimeout)
		self._lines = []
		self._lineSeperator = u'\n'

	def open(self, mode='r', encoding='utf-8', errors='replace'):
		return LockableFile.open(self, mode, encoding, errors)

	def write(self, str):
		if not self._fileHandle:
			raise IOError("File not opened")
		str = forceUnicode(str)
		self._fileHandle.write(str)

	def readlines(self):
		self._lines = []
		if not self._fileHandle:
			for encoding in ('utf-8', 'utf-16', 'latin_1', 'cp1252', 'replace'):
				errors = 'strict'
				if encoding == 'replace':
					errors = 'replace'
					encoding = 'utf-8'

				self.open(encoding=encoding, errors=errors)
				try:
					self._lines = self._fileHandle.readlines()
					self.close()
					break
				except ValueError:
					self.close()
					continue
		return self._lines

	def getLines(self):
		return self._lines

	def writelines(self, sequence=[]):
		if not self._fileHandle:
			raise IOError("File not opened")
		if sequence:
			self._lines = forceUnicodeList(sequence)
		for index, current in enumerate(self._lines):
			self._lines[index] = current + self._lineSeperator
		self._fileHandle.writelines(self._lines)


class ChangelogFile(TextFile):
	'''
	Files containing changelogs.

	These follow the Debian style changelogs:

	package (version) distribution(s); urgency=urgency
		[optional blank line(s), stripped]
	  * change details
		 more change details
		  [blank line(s), included]
	  * even more change details
		  [optional blank line(s), stripped]
	[one space]-- maintainer name <email address>[two spaces]date
	'''

	releaseLineRegex = re.compile(r'^\s*(\S+)\s+\(([^\)]+)\)\s+([^;]+);\s+urgency=(\S+)\s*$')

	def __init__(self, filename, lockFailTimeout=2000):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._parsed = False
		self._entries = []

	def parse(self, lines=None):
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._parsed = False
		self._entries = []
		currentEntry = {}
		for lineNum, line in enumerate(self._lines):
			try:
				match = self.releaseLineRegex.search(line)
				if match:
					if currentEntry:
						self.addEntry(currentEntry)

					currentEntry = {
						'package': match.group(1),
						'version': match.group(2),
						'release': match.group(3),
						'urgency': match.group(4),
						'changelog': [],
						'maintainerName': u'',
						'maintainerEmail': u'',
						'date': None
					}
					continue

				if line.startswith(' --'):
					if '  ' not in line:
						raise ValueError(u"maintainer must be separated from date using two spaces")
					if not currentEntry or currentEntry['date']:
						raise ValueError(u"found trailer out of release")

					(maintainer, date) = line[3:].strip().split(u'  ', 1)
					email = u''
					try:
						(maintainer, email) = maintainer.split(u'<', 1)
						maintainer = maintainer.strip()
						email = email.strip().replace(u'<', u'').replace(u'>', u'')
					except ValueError:
						pass

					currentEntry['maintainerName'] = maintainer
					currentEntry['maintainerEmail'] = email
					if u'+' in date:
						date = date.split(u'+')[0]
					currentEntry['date'] = time.strptime(date.strip(), "%a, %d %b %Y %H:%M:%S")
					changelog = []
					buf = []
					for l in currentEntry['changelog']:
						if not changelog and not l.strip():
							continue
						if not l.strip():
							buf.append(forceUnicode(l))
						else:
							changelog.extend(buf)
							buf = []
							changelog.append(forceUnicode(l))
					currentEntry['changelog'] = forceUnicodeList(changelog)

				else:
					if not currentEntry and line.strip():
						raise ValueError(u"text not in release")
					if currentEntry:
						currentEntry['changelog'].append(line.rstrip())
			except Exception as error:
				raise ValueError(u"Parse error in line %d: %s" % (lineNum, error))
		if currentEntry:
			self.addEntry(currentEntry)
		self._parsed = True
		return self._entries

	def generate(self):
		# get current locale
		loc = locale.getlocale()
		locale.setlocale(locale.LC_ALL, 'C')
		try:
			if not self._entries:
				raise ValueError(u"No entries to write")
			self._lines = []
			for entry in self._entries:
				self._lines.append(u'%s (%s) %s; urgency=%s' % (entry['package'], entry['version'], entry['release'], entry['urgency']))
				self._lines.append(u'')
				for line in entry['changelog']:
					self._lines.append(line)
				if self._lines[-1].strip():
					self._lines.append(u'')
				self._lines.append(u' -- %s <%s>  %s' % (entry['maintainerName'], entry['maintainerEmail'], time.strftime('%a, %d %b %Y %H:%M:%S +0000', entry['date'])))
				self._lines.append(u'')

			self.open('w')
			self.writelines()
			self.close()
		finally:
			if loc:
				try:
					locale.setlocale(locale.LC_ALL, loc)
				except Exception:
					pass

	@requiresParsing
	def getEntries(self):
		return self._entries

	def setEntries(self, entries):
		entries = forceList(entries)
		self._entries = []
		for entry in entries:
			self.addEntry(entry)

	def addEntry(self, entry):
		entry = forceDict(entry)
		for key in ('package', 'version', 'release', 'urgency', 'changelog', 'maintainerName', 'maintainerEmail', 'date'):
			try:
				entry[key]
			except KeyError:
				raise KeyError(u"Missing key '%s' in entry %s" % (key, entry))

		entry['package'] = forceProductId(entry['package'])
		entry['version'] = forceUnicode(entry['version'])
		entry['release'] = forceUnicode(entry['release'])
		entry['urgency'] = forceUnicode(entry['urgency'])
		entry['changelog'] = forceUnicodeList(entry['changelog'])
		entry['maintainerName'] = forceUnicode(entry['maintainerName'])
		entry['maintainerEmail'] = forceEmailAddress(entry['maintainerEmail'])
		entry['date'] = forceTime(entry['date'])
		self._entries.append(entry)


class ConfigFile(TextFile):
	def __init__(self, filename, lockFailTimeout=2000, commentChars=[';', '#'], lstrip=True):
		TextFile.__init__(self, filename, lockFailTimeout)
		self._commentChars = forceList(commentChars)
		self._lstrip = forceBool(lstrip)
		self._parsed = False

	def parse(self, lines=None):
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._parsed = False
		lines = []
		for line in self._lines:
			l = line.strip()
			if not l or l[0] in self._commentChars:
				continue

			if self._lstrip:
				line = line.strip()
			else:
				line = line.rstrip()

			for cc in self._commentChars:
				if cc not in line:
					continue

				parts = line.split(cc)
				quote = 0
				doublequote = 0
				cut = -1
				for i, part in enumerate(islice(parts, len(parts) - 1)):
					quote += part.count("'")
					doublequote += part.count('"')
					if len(part) > 0 and part[-1] == '\\':
						# escaped comment
						continue

					if not quote % 2 and not doublequote % 2:
						cut = i
						break

				if cut > -1:
					line = cc.join(parts[:cut + 1])

			if not line:
				continue

			lines.append(line)
		self._parsed = True
		return lines


class IniFile(ConfigFile):

	optionMatch = re.compile(r'^([^:=]+)\s*([:=].*)$')

	def __init__(self, filename, lockFailTimeout=2000, ignoreCase=True, raw=True):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars=[';', '#'])
		self._ignoreCase = forceBool(ignoreCase)
		self._raw = forceBool(raw)
		self._configParser = None
		self._parsed = False
		self._sectionSequence = []
		self._keepOrdering = False

	def setSectionSequence(self, sectionSequence):
		self._sectionSequence = forceUnicodeList(sectionSequence)

	def setKeepOrdering(self, keepOrdering):
		self._keepOrdering = forceBool(keepOrdering)

	def parse(self, lines=None, returnComments=False):
		logger.debug(u"Parsing ini file '%s'" % self._filename)
		start = time.time()
		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._parsed = False

		lines = []
		currentSection = None
		comments = {}
		currentComments = []
		for line in self._lines:
			line = line.strip()
			if not line:
				if returnComments:
					currentComments.append(u'')
				continue
			if line.startswith('['):
				currentSection = line.split('[', 1)[1].split(']', 1)[0].strip()
				if returnComments:
					comments[currentSection] = {'[]': currentComments}
					currentComments = []
				if self._ignoreCase:
					line = line.lower()
			if line[0] in self._commentChars and not returnComments:
				continue
			comment = None
			for cc in self._commentChars:
				if cc not in line:
					continue

				parts = line.split(cc)
				quote = 0
				doublequote = 0
				cut = -1
				for i, part in enumerate(islice(parts, len(parts) - 1)):
					quote += part.count("'")
					doublequote += part.count('"')
					if len(part) > 0 and part[-1] == '\\':
						# escaped comment
						continue
					if not quote % 2 and not doublequote % 2:
						cut = i
						break

				if cut > -1:
					line = cc.join(parts[:cut + 1])
					if returnComments:
						comment = cc + cc.join(parts[cut + 1:])

			if self._ignoreCase or comment:
				match = self.optionMatch.search(line)
				if match:
					option = match.group(1)
					if self._ignoreCase:
						option = option.lower()
						line = option + match.group(2)
					if currentComments and currentSection:
						comments[currentSection][option.strip()] = currentComments
						currentComments = []
			if comment:
				currentComments.append(comment)
			if not line:
				continue
			lines.append(line)
		self._configParser = None
		if self._raw:
			self._configParser = RawConfigParser()
		else:
			self._configParser = SafeConfigParser()

		try:
			self._configParser.read_file(StringIO(u'\r\n'.join(lines)))
		except Exception as e:
			raise RuntimeError(u"Failed to parse ini file '%s': %s" % (self._filename, e))

		logger.debug(u"Finished reading file after %0.3f seconds" % (time.time() - start))

		self._parsed = True
		if returnComments:
			return (self._configParser, comments)
		return self._configParser

	def generate(self, configParser, comments={}):
		self._configParser = configParser

		if not self._configParser:
			raise ValueError(u"Got no data to write")

		sectionSequence = []
		optionSequence = {}
		if self._keepOrdering and os.path.exists(self._filename):
			for line in self.readlines():
				line = line.strip()
				if not line or line[0] in self._commentChars:
					continue
				if line.startswith('['):
					section = line.split('[', 1)[1].split(']', 1)[0].strip()
					sectionSequence.append(section)
				elif '=' in line:
					option = line.split('=')[0].strip()
					if sectionSequence[-1] not in optionSequence:
						optionSequence[sectionSequence[-1]] = []
					optionSequence[sectionSequence[-1]].append(option)
		else:
			sectionSequence = list(self._sectionSequence)

		sectionSequence.reverse()
		sections = self._configParser.sections()
		sections.sort()
		for section in sectionSequence:
			if section in sections:
				logger.debug2(u"Moving section %s to top" % section)
				sections.remove(section)
				sections.insert(0, section)
			logger.debug2(u"Section sequence: %s" % sections)

		self._lines = []
		for section in sections:
			section = forceUnicode(section)
			if comments:
				for l in comments.get(section, {}).get('[]', []):
					self._lines.append(forceUnicode(l))
			self._lines.append(u'[%s]' % section)
			options = self._configParser.options(section)
			options.sort()
			for i, option in enumerate(options):
				options[i] = forceUnicode(option)
			optseq = optionSequence.get(section, [])
			if optseq:
				optseq.reverse()
				for option in optseq:
					if option in options:
						options.remove(option)
						options.insert(0, option)
			for option in options:
				if comments:
					for l in comments.get(section, {}).get(option, []):
						self._lines.append(forceUnicode(l))
				self._lines.append(u'%s = %s' % (option, forceUnicode(self._configParser.get(section, option))))
			if not comments:
				self._lines.append(u'')
		self.open('w')
		self.writelines()
		self.close()


class InfFile(ConfigFile):

	sectionRegex = re.compile(r'\[\s*([^\]]+)\s*\]')
	pciDeviceRegex = re.compile(r'VEN_([\da-fA-F]+)&DEV_([\da-fA-F]+)', re.IGNORECASE)
	hdaudioDeviceRegex = re.compile(r'HDAUDIO\\\.*VEN_([\da-fA-F]+)&DEV_([\da-fA-F]+)', re.IGNORECASE)
	usbDeviceRegex = re.compile(r'USB.*VID_([\da-fA-F]+)&PID_([\da-fA-F]+)', re.IGNORECASE)
	acpiDeviceRegex = re.compile(r'ACPI\\(\S+)_-_(\S+)', re.IGNORECASE)
	varRegex = re.compile(r'%([^%]+)%')
	classRegex = re.compile(r'class\s*=')

	def __init__(self, filename, lockFailTimeout=2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars=[';', '#'])
		self._sourceDisksNames = []
		self._devices = []

	@requiresParsing
	def getDevices(self):
		return self._devices

	@requiresParsing
	def getSourceDisksNames(self):
		return self._sourceDisksNames

	def isDeviceKnown(self, vendorId, deviceId, deviceType=None):
		try:
			vendorId = forceHardwareVendorId(vendorId)
			deviceId = forceHardwareDeviceId(deviceId)
		except Exception as e:
			logger.error(e)
			return False
		if not self._parsed:
			self.parse()
		for d in self._devices:
			if (not deviceType or (d.get('type') == deviceType)) and (d.get('vendor') == vendorId) and (not d.get('device') or (d['device'] == deviceId)):
				return True
		return False

	def parse(self, lines=None):
		logger.debug(u"Parsing inf file %s" % self._filename)
		lines = ConfigFile.parse(self, lines)
		self._parsed = False
		self._devices = []

		path = os.path.dirname(self._filename)

		deviceClass = u'???'
		deviceSections = []
		appendNext = False
		newLines = []
		for line in lines:
			if appendNext:
				newLines[-1] = lines[-1][:-1] + line
			else:
				newLines.append(line)

			appendNext = line.endswith(u'\\')
		lines = newLines

		# Get strings
		logger.debug2(u"   - Getting strings")
		strings = {}
		section = u''
		for line in lines:
			match = re.search(self.sectionRegex, line)
			if match:
				if section.lower() == u'strings':
					break
				section = match.group(1)
			else:
				if section.lower() == u'strings':
					try:
						(var, string) = line.split(u'=', 1)
						string = string.strip()
						if string.startswith(u'"') and string.endswith(u'"'):
							string = string[1:-1]
						strings[var.strip().lower()] = string
					except Exception:
						pass
		logger.debug2(u"        got strings: %s" % strings)

		# Get source disks names
		self._sourceDisksNames = []
		sectionFound = False
		for line in lines:
			match = re.search(self.sectionRegex, line)
			if match:
				section = match.group(1)
				sectionFound = section.lower().startswith(u'sourcedisksnames')
				continue

			if sectionFound:
				if '=' not in line:
					continue
				name = line.split(u'=')[1].split(u',')[0].strip()
				name = strings.get(name.replace('%', '').lower(), name)
				if name not in self._sourceDisksNames:
					self._sourceDisksNames.append(name)

		# Get devices
		logger.debug2(u"   - Getting devices")
		section = u''
		for line in lines:
			match = re.search(self.sectionRegex, line)
			if match:
				if section.lower() == u'manufacturer':
					break
				section = match.group(1)
			else:
				if section.lower() == u'version':
					if line.lower().startswith(u'class'):
						if re.search(self.classRegex, line.lower()):
							deviceClass = line.split('=')[1].strip().lower()
							match = re.search(self.varRegex, deviceClass)
							if match:
								var = match.group(1).lower()
								if var in strings:
									deviceClass = deviceClass.replace(u'%{0}%'.format(var), strings[var])

				elif section.lower() == u'manufacturer':
					if line and u'=' in line:
						for d in line.split(u'=')[1].split(u','):
							deviceSections.append(d.strip())

		devSections = set()
		for deviceSection in deviceSections:
			for i in deviceSection.split('.'):
				devSections.add(i)
		deviceSections = devSections
		logger.debug2(u"      - Device sections: %s" % ', '.join(deviceSections))

		def isDeviceSection(section):
			if section in deviceSections:
				return True
			for s in section.split(u'.'):
				if s not in deviceSections:
					return False
			return True

		found = set()
		section = ''
		sectionsParsed = []
		for line in lines:
			try:
				match = re.search(self.sectionRegex, line)
				if match:
					if section and isDeviceSection(section):
						sectionsParsed.append(section)
					section = match.group(1)
					if isDeviceSection(section):
						logger.debug2(u"   - Parsing device section: %s" % section)
				else:
					if isDeviceSection(section) and section not in sectionsParsed:
						try:
							if '=' not in line or ',' not in line:
								continue
							devString = line.split(u'=')[1].split(u',')[1].strip()
							logger.debug2(u"      - Processing device string: %s" % devString)
							type = ''
							match = re.search(self.hdaudioDeviceRegex, devString)
							if match:
								type = u'HDAUDIO'
							else:
								match = re.search(self.pciDeviceRegex, devString)
								if match:
									type = u'PCI'
								else:
									match = re.search(self.usbDeviceRegex, devString)
									if match:
										type = u'USB'
									else:
										match = re.search(self.acpiDeviceRegex, devString)
										if match:
											type = u'ACPI'
							if match:
								logger.debug2(u"         - Device type is %s" % type)
								if type == u'ACPI':
									vendor = match.group(1)
									device = match.group(2)
								else:
									vendor = forceHardwareVendorId(match.group(1))
									device = forceHardwareDeviceId(match.group(2))
								if u"%s:%s" % (vendor, device) not in found:
									logger.debug2(u"         - Found %s device: %s:%s" % (type, vendor, device))
									found.add(u"%s:%s:%s" % (type, vendor, device))
									self._devices.append(
										{
											'path': path,
											'class': deviceClass,
											'vendor': vendor,
											'device': device,
											'type': type
										}
									)
						except IndexError:
							logger.warning(u"Skipping bad line '%s' in file %s" % (line, self._filename))
			except Exception as e:
				logger.error(u"Parse error in inf file '%s' line '%s': %s" % (self._filename, line, e))
		self._parsed = True


class PciidsFile(ConfigFile):

	def __init__(self, filename, lockFailTimeout=2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars=[';', '#'], lstrip=False)
		self._devices = {}
		self._vendors = {}
		self._subDevices = {}

	@requiresParsing
	def getVendor(self, vendorId):
		vendorId = forceHardwareVendorId(vendorId)
		return self._vendors.get(vendorId, None)

	@requiresParsing
	def getDevice(self, vendorId, deviceId):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		return self._devices.get(vendorId, {}).get(deviceId, None)

	@requiresParsing
	def getSubDevice(self, vendorId, deviceId, subVendorId, subDeviceId):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		subVendorId = forceHardwareVendorId(subVendorId)
		subDeviceId = forceHardwareDeviceId(subDeviceId)
		return self._subDevices.get(vendorId, {}).get(deviceId, {}).get(subVendorId + ':' + subDeviceId, None)

	def parse(self, lines=None):
		logger.debug(u"Parsing ids file %s" % self._filename)

		lines = ConfigFile.parse(self, lines)
		self._parsed = False

		self._devices = {}
		self._vendors = {}
		self._subDevices = {}

		currentVendorId = None
		currentDeviceId = None
		for line in lines:
			try:
				if line.startswith(u'C '):
					# Start of list of known device classes, subclasses and programming interfaces
					break

				if line.startswith(u'\t'):
					if not currentVendorId or currentVendorId not in self._devices:
						raise ValueError(u"Parse error in file '%s': %s" % (self._filename, line))

					if line.startswith(u'\t\t'):
						if not currentDeviceId or currentVendorId not in self._subDevices or currentDeviceId not in self._subDevices[currentVendorId]:
							raise ValueError(u"Parse error in file '%s': %s" % (self._filename, line))
						(subVendorId, subDeviceId, subName) = line.lstrip().split(None, 2)
						subVendorId = forceHardwareVendorId(subVendorId)
						subDeviceId = forceHardwareDeviceId(subDeviceId)
						self._subDevices[currentVendorId][currentDeviceId][subVendorId + ':' + subDeviceId] = subName.strip()
					else:
						(deviceId, deviceName) = line.lstrip().split(None, 1)
						currentDeviceId = deviceId = forceHardwareDeviceId(deviceId)
						if deviceId not in self._subDevices[currentVendorId]:
							self._subDevices[currentVendorId][deviceId] = {}
						self._devices[currentVendorId][deviceId] = deviceName.strip()
				else:
					(vendorId, vendorName) = line.split(None, 1)
					currentVendorId = vendorId = forceHardwareVendorId(vendorId)
					try:
						self._devices[vendorId]
					except KeyError:
						self._devices[vendorId] = {}

					try:
						self._subDevices[vendorId]
					except KeyError:
						self._subDevices[vendorId] = {}

					self._vendors[vendorId] = vendorName.strip()
			except Exception as e:
				logger.error(e)
		self._parsed = True


UsbidsFile = PciidsFile


class TxtSetupOemFile(ConfigFile):

	sectionRegex = re.compile(r'\[\s*([^\]]+)\s*\]')
	pciDeviceRegex = re.compile(r'VEN_([\da-fA-F]+)(&DEV_([\da-fA-F]+))?(\S*)\s*$')
	usbDeviceRegex = re.compile(r'USB.*VID_([\da-fA-F]+)(&PID_([\da-fA-F]+))?(\S*)\s*$', re.IGNORECASE)
	filesRegex = re.compile(r'^files\.(computer|display|keyboard|mouse|scsi)\.(.+)$', re.IGNORECASE)
	configsRegex = re.compile(r'^config\.(.+)$', re.IGNORECASE)
	hardwareIdsRegex = re.compile(r'^hardwareids\.(computer|display|keyboard|mouse|scsi)\.(.+)$', re.IGNORECASE)
	dllEntryRegex = re.compile(r'^(dll\s*\=\s*)(\S+.*)$', re.IGNORECASE)

	def __init__(self, filename, lockFailTimeout=2000):
		ConfigFile.__init__(self, filename, lockFailTimeout, commentChars=[';', '#'])
		self._devices = []
		self._files = []
		self._componentNames = []
		self._componentOptions = []
		self._defaultComponentIds = []
		self._serviceNames = []
		self._driverDisks = []
		self._configs = []

	@requiresParsing
	def getDevices(self):
		return self._devices

	@requiresParsing
	def isDeviceKnown(self, vendorId, deviceId, deviceType=None):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		for d in self._devices:
			if (not deviceType or (d.get('type') == deviceType)) and (d.get('vendor') == vendorId) and (not d.get('device') or (d['device'] == deviceId)):
				return True
		return False

	@requiresParsing
	def getDevice(self, vendorId, deviceId, deviceType=None, architecture='x86'):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		architecture = forceArchitecture(architecture)

		device = None
		for d in self._devices:
			if (not deviceType or (d.get('type') == deviceType)) and (d.get('vendor') == vendorId) and (not d.get('device') or d['device'] == deviceId):
				if architecture == 'x86':
					if 'amd64' in d['componentId'].lower() or 'x64' in d['componentId'].lower():
						logger.debug(u"Skipping device with component id '%s' which does not seem to match architecture '%s'" % (d['componentId'], architecture))
						continue
				elif architecture == 'x64':
					if 'i386' in d['componentId'].lower() or 'x86' in d['componentId'].lower():
						logger.debug(u"Skipping device with component id '%s' which does not seem to match architecture '%s'" % (d['componentId'], architecture))
						continue
				device = d
				break
		if not device:
			raise ValueError(u"Device '%s:%s' not found in txtsetup.oem file '%s'" % (vendorId, deviceId, self._filename))
		return device

	def getFilesForDevice(self, vendorId, deviceId, deviceType=None, fileTypes=[], architecture='x86'):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)
		fileTypes = forceUnicodeLowerList(fileTypes)
		architecture = forceArchitecture(architecture)

		device = self.getDevice(vendorId=vendorId, deviceId=deviceId, deviceType=deviceType, architecture=architecture)

		files = []
		diskDriverDirs = {}
		for d in self._driverDisks:
			diskDriverDirs[d["diskName"]] = d["driverDir"]

		for f in self._files:
			if f['componentName'] != device['componentName'] or f['componentId'] != device['componentId']:
				continue
			if fileTypes and f['fileType'] not in fileTypes:
				continue
			if f['diskName'] not in diskDriverDirs:
				raise ValueError(u"Driver disk for file %s not found in txtsetup.oem file '%s'" % (f, self._filename))
			files.append(os.path.join(diskDriverDirs[f['diskName']], f['filename']))
		return files

	def getComponentOptionsForDevice(self, vendorId, deviceId, deviceType=None, architecture='x86'):
		vendorId = forceHardwareVendorId(vendorId)
		deviceId = forceHardwareDeviceId(deviceId)

		device = self.getDevice(vendorId=vendorId, deviceId=deviceId, deviceType=deviceType, architecture=architecture)

		for componentOptions in self._componentOptions:
			if componentOptions['componentName'] == device['componentName'] and componentOptions["componentId"] == device['componentId']:
				return componentOptions
		for componentOptions in self._componentOptions:
			if componentOptions['componentName'].lower() == device['componentName'].lower() and componentOptions["componentId"].lower() == device['componentId'].lower():
				return componentOptions
		raise ValueError(u"Component options for device %s not found in txtsetup.oem file '%s'" % (device, self._filename))

	@requiresParsing
	def applyWorkarounds(self):
		if not self._defaultComponentIds:
			# Missing default component will cause problems in windows textmode setup
			logger.info(u"No default component ids found, using '%s' as default component id" % self._componentOptions[0]['componentId'])
			self._defaultComponentIds.append(
				{
					'componentName': self._componentOptions[0]['componentName'],
					'componentId': self._componentOptions[0]['componentId']
				}
			)
		files = []
		for f in self._files:
			if f['fileType'] == 'dll':
				# dll entries will cause problems in windows textmode setup
				continue
			files.append(f)
		self._files = files

	def parse(self, lines=None):
		logger.debug(u"Parsing txtsetup.oem file %s" % self._filename)

		lines = ConfigFile.parse(self, lines)
		self._parsed = False

		self._devices = []
		self._files = []
		self._componentNames = []
		self._componentOptions = []
		self._defaultComponentIds = []
		self._serviceNames = []
		self._driverDisks = []
		self._configs = []

		sections = {}
		section = None
		for line in lines:
			logger.debug2(u"txtsetup.oem: %s" % line)
			match = re.search(self.sectionRegex, line)
			if match:
				section = match.group(1)
				sections[section] = []
			elif section:
				sections[section].append(line)

		# Search for component options
		logger.info(u"Searching for component names and options")
		for (section, lines) in sections.items():
			if section.lower() not in ('computer', 'display', 'keyboard', 'mouse', 'scsi'):
				continue
			componentName = section
			for line in lines:
				if u'=' not in line:
					continue
				optionName = None
				(componentId, value) = line.split('=', 1)
				componentId = componentId.strip()
				try:
					(description, optionName) = value.split(',', 1)
					optionName = optionName.strip()
				except ValueError:
					description = value
				description = description.strip()
				if description.startswith(u'"') and description.endswith(u'"'):
					description = description[1:-1]
				if not componentName in self._componentNames:
					self._componentNames.append(componentName)
				self._componentOptions.append(
					{
						"componentName": componentName,
						"description": description,
						"componentId": componentId,
						"optionName": optionName
					}
				)

		logger.info(u"Component names found: %s" % self._componentNames)
		logger.info(u"Component options found: %s" % self._componentOptions)

		# Search for default component ids
		logger.info(u"Searching for default component ids")
		for (section, lines) in sections.items():
			if section.lower() != 'defaults':
				continue

			for line in lines:
				(componentName, componentId) = line.split('=', 1)
				self._defaultComponentIds.append(
					{
						'componentName': componentName.strip(),
						'componentId': componentId.strip()
					}
				)

		if self._defaultComponentIds:
			logger.info(u"Found default component ids: %s" % self._defaultComponentIds)

		# Search for hardware ids
		logger.info(u"Searching for devices")
		for (section, lines) in sections.items():
			match = re.search(self.hardwareIdsRegex, section)
			if not match:
				continue
			componentName = match.group(1)
			componentId = match.group(2)
			logger.info(u"Found hardwareIds section '%s', component name '%s', component id '%s'" % (section, componentName, componentId))
			for line in lines:
				if not re.search(r'[iI][dD]\s*=', line):
					continue
				(device, serviceName) = line.split(u'=', 1)[1].strip().split(u',', 1)
				device = device.strip()
				if device.startswith(u'"') and device.endswith(u'"'):
					device = device[1:-1]
				serviceName = serviceName.strip()
				if serviceName.startswith(u'"') and serviceName.endswith(u'"'):
					serviceName = serviceName[1:-1]
				match = re.search(self.pciDeviceRegex, device)
				if not match:
					continue
				vendor = forceHardwareVendorId(match.group(1))
				device = None
				if match.group(3):
					device = forceHardwareDeviceId(match.group(3))
				extra = None
				if match.group(4):
					extra = forceUnicode(match.group(4))
				logger.debug(u"   Found %s device: %s:%s, service name: %s" % (u'PCI', vendor, device, serviceName))
				self._devices.append(
					{
						'vendor': vendor,
						'device': device,
						'extra': extra,
						'type': u'PCI',
						'serviceName': serviceName,
						'componentName': componentName,
						'componentId': componentId
					}
				)
				if serviceName not in self._serviceNames:
					self._serviceNames.append(serviceName)

		if not self._devices:
			raise ValueError(u"No devices found in txtsetup file '%s'" % self._filename)

		logger.info(u"Found services: %s" % self._serviceNames)
		logger.debug(u"Found devices: %s" % self._devices)

		# Search for disks
		logger.info(u"Searching for disks")
		for (section, lines) in sections.items():
			if section.lower() != 'disks':
				continue

			for line in lines:
				if u'=' not in line:
					continue

				(diskName, value) = line.split('=', 1)
				diskName = diskName.strip()
				(desc, tf, dd) = value.split(',', 2)
				desc = desc.strip()
				if desc.startswith(u'"') and desc.endswith(u'"'):
					desc = desc[1:-1]
				tf = tf.strip()
				if tf.startswith(u'\\'):
					tf = tf[1:]
				dd = dd.strip()
				if dd.startswith(u'\\'):
					dd = dd[1:]

				self._driverDisks.append(
					{
						"diskName": diskName,
						"description": desc,
						"tagfile": tf,
						"driverDir": dd
					}
				)
		if not self._driverDisks:
			raise ValueError(u"No driver disks found in txtsetup file '%s'" % self._filename)
		logger.info(u"Found driver disks: %s" % self._driverDisks)

		# Search for files
		logger.info(u"Searching for files")
		for (section, lines) in sections.items():
			match = re.search(self.filesRegex, section)
			if not match:
				continue
			componentName = match.group(1)
			componentId = match.group(2)
			logger.info(u"Found files section '%s', component name '%s', component id '%s'" % (section, componentName, componentId))
			for line in lines:
				(fileType, value) = line.split(u'=', 1)
				fileType = fileType.strip()
				parts = value.split(u',')
				diskName = parts[0].strip()
				filename = parts[1].strip()
				optionName = None
				if len(parts) > 2:
					optionName = parts[2].strip()

				self._files.append(
					{
						'fileType': fileType,
						'diskName': diskName,
						'filename': filename,
						'componentName': componentName,
						'componentId': componentId,
						'optionName': optionName
					}
				)
		logger.debug(u"Found files: %s" % self._files)

		# Search for configs
		logger.info(u"Searching for configs")
		for (section, lines) in sections.items():
			match = re.search(self.configsRegex, section)
			if not match:
				continue
			componentId = match.group(1)
			logger.info(u"Found configs section '%s', component id '%s'" % (section, componentId))
			for line in lines:
				value = line.split(u'=', 1)[1]
				(keyName, valueName, valueType, value) = value.split(u',', 3)
				keyName = keyName.strip()
				valueName = valueName.strip()
				valueType = valueType.strip()
				value = value.strip()
				self._configs.append(
					{
						'keyName': keyName.strip(),
						'valueName': valueName.strip(),
						'valueType': valueType.strip(),
						'value': value.strip(),
						'componentId': componentId
					}
				)
		logger.debug(u"Found configs: %s" % self._configs)
		self._parsed = True

	def generate(self):
		lines = []
		lines.append(u'[Disks]\r\n')
		for disk in self._driverDisks:
			lines.append(u'%s = "%s", \\%s, \\%s\r\n' % (disk["diskName"], disk["description"], disk["tagfile"], disk["driverDir"]))
		lines.append(u'\r\n')
		lines.append(u'[Defaults]\r\n')
		for default in self._defaultComponentIds:
			lines.append(u'%s = %s\r\n' % (default["componentName"], default["componentId"]))

		for name in self._componentNames:
			lines.append(u'\r\n')
			lines.append(u'[%s]\r\n' % name)
			for options in self._componentOptions:
				if options["componentName"] != name:
					continue
				line = u'%s = "%s"' % (options["componentId"], options["description"])
				if options["optionName"]:
					line += u', %s' % options["optionName"]
				lines.append(line + u'\r\n')

		for name in self._componentNames:
			for options in self._componentOptions:
				if options["componentName"] != name:
					continue
				lines.append(u'\r\n')
				lines.append(u'[Files.%s.%s]\r\n' % (name, options["componentId"]))
				for f in self._files:
					if f['componentName'] != name or f['componentId'] != options["componentId"]:
						continue
					line = u'%s = %s, %s' % (f['fileType'], f['diskName'], f['filename'])
					if f["optionName"]:
						line += u', %s' % f["optionName"]
					lines.append(line + u'\r\n')

		for name in self._componentNames:
			for options in self._componentOptions:
				if options["componentName"] != name:
					continue
				lines.append(u'\r\n')
				lines.append(u'[HardwareIds.%s.%s]\r\n' % (name, options["componentId"]))
				for dev in self._devices:
					if dev['componentName'] != name or dev['componentId'] != options["componentId"]:
						continue

					line = u'id = "%s\\VEN_%s' % (dev['type'], dev['vendor'])
					if dev['device']:
						line += u'&DEV_%s' % dev['device']
					if dev['extra']:
						line += dev['extra']
					if dev['type'] == 'USB':
						line = line.replace(u'VEN_', u'VID_').replace(u'DEV_', u'PID_')
					line += '", "%s"' % dev['serviceName']
					lines.append(line + u'\r\n')

		configComponents = {}
		for config in self._configs:
			if config['componentId'] not in configComponents:
				configComponents[config['componentId']] = []
			configComponents[config['componentId']].append(config)

		for (componentId, configs) in configComponents.items():
			lines.append(u'\r\n')
			lines.append(u'[Config.%s]\r\n' % componentId)
			for conf in configs:
				lines.append(u'value = %s, %s, %s, %s\r\n' % (conf['keyName'], conf['valueName'], conf['valueType'], conf['value']))

		self._lines = lines
		self._fileHandle = codecs.open(self._filename, 'w', 'cp1250')
		self.writelines()
		self.close()


class ZsyncFile(LockableFile):
	def __init__(self, filename, lockFailTimeout=2000):
		LockableFile.__init__(self, filename, lockFailTimeout)
		self._header = {}
		self._data = ''
		self._parsed = False

	def parse(self, lines=None):
		logger.debug(u"Parsing zsync file %s" % self._filename)

		self._parsed = False

		with open(self._filename, 'rb') as f:
			for line in iter(lambda: f.readline().strip(), b''):
				strLine = line.decode()
				key, value = strLine.split(':', 1)
				self._header[key.strip()] = value.strip()

			# Header and data are divided by an empty line
			self._data = f.read()

		self._parsed = True

	def generate(self, dataFile=None):
		if dataFile:
			execute(u"%s -u '%s' -o '%s' '%s'" % (which('zsyncmake'), os.path.basename(dataFile), self._filename, dataFile))
			self.parse()

		with open(self._filename, 'wb') as f:
			for key, value in self._header.items():
				if key.lower() == 'mtime':
					continue
				headerData = '%s: %s\n' % (key, value)
				f.write(headerData.encode())
			f.write('\n'.encode())
			f.write(self._data)


class DHCPDConf_Component(object):
	def __init__(self, startLine, parentBlock):
		self.startLine = startLine
		self.endLine = startLine
		self.parentBlock = parentBlock

	def getShifting(self):
		shifting = u''
		if not self.parentBlock:
			return shifting
		parentBlock = self.parentBlock.parentBlock
		while parentBlock:
			shifting += u'\t'
			parentBlock = parentBlock.parentBlock
		return shifting

	def asText(self):
		return self.getShifting()

	def __str__(self):
		return u'<{0}({1:d}, {2})>'.format(
			self.__class__.__name__, self.startLine, self.endLine)

	def __repr__(self):
		return self.__str__()


class DHCPDConf_Parameter(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, key, value):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.key = key
		self.value = value
		if isinstance(self.value, str):
			if self.value.lower() in (u'yes', u'true', u'on'):
				self.value = True
			elif self.value.lower() in (u'no', u'false', u'off'):
				self.value = False

	def asText(self):
		value = self.value
		if isinstance(value, bool):
			if value:
				value = u'on'
			else:
				value = u'off'
		elif (self.key in (u'filename', u'ddns-domainname') or
				re.match(r".*['/\\].*", value) or
				re.match(r'^\w+\.\w+$', value) or
				self.key.endswith(u'-name')):

			value = u'"%s"' % value
		return u"%s%s %s;" % (self.getShifting(), self.key, value)

	def asHash(self):
		return {self.key: self.value}


class DHCPDConf_Option(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, key, value):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.key = key
		self.value = value
		if not isinstance(self.value, list):
			self.value = [self.value]

	def asText(self):
		quotedOptions = (
			u'-name', u'-domain', u'-identifier', u'-search',
			u'merit-dump', u'nds-context', u'netbios-scope', u'nwip-domain',
			u'nwip-suboptions', u'nis-domain', u'nisplus-domain', u'root-path',
			u'uap-servers', u'user-class', u'vendor-encapsulated-options',
			u'circuit-id', u'remote-id', u'fqdn.fqdn', u'ddns-rev-domainname'
		)

		text = []
		for value in self.value:
			if (re.match(r".*['/\\].*", value) or
				re.match(r"^\w+\.\w+$", value) or
				self.key.endswith(quotedOptions)):

				text.append(u'"%s"' % value)
			else:
				text.append(value)

		return "{0}option {key} {values};".format(self.getShifting(), key=self.key, values=u', '.join(text))

	def asHash(self):
		return {self.key: self.value}


class DHCPDConf_Comment(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, data):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self._data = data

	def asText(self):
		return u'{0}#{1}'.format(self.getShifting(), self._data)


class DHCPDConf_EmptyLine(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)


class DHCPDConf_Block(DHCPDConf_Component):
	def __init__(self, startLine, parentBlock, type, settings=[]):
		DHCPDConf_Component.__init__(self, startLine, parentBlock)
		self.type = type
		self.settings = settings
		self.lineRefs = {}
		self.components = []

	def getComponents(self):
		return self.components

	def removeComponents(self):
		logger.debug(u"Removing components: %s" % self.components)
		for c in forceList(self.components):
			self.removeComponent(c)

	def addComponent(self, component):
		self.components.append(component)
		if component.startLine not in self.lineRefs:
			self.lineRefs[component.startLine] = []
		self.lineRefs[component.startLine].append(component)

	def removeComponent(self, component):
		index = -1
		for i, currentComponent in enumerate(self.components):
			if currentComponent == component:
				index = i
				break

		if index < 0:
			raise BackendMissingDataError(u"Component '{0}' not found".format(component))

		del self.components[index]

		index = -1
		if component.startLine in self.lineRefs:
			for i, currentComponent in enumerate(self.lineRefs[component.startLine]):
				if currentComponent == component:
					index = i
					break
		if index >= 0:
			del self.lineRefs[component.startLine][index]

	def getOptions_hash(self, inherit=None):
		options = {}
		for component in self.components:
			if not isinstance(component, DHCPDConf_Option):
				continue
			options[component.key] = component.value

		if inherit and (self.type != inherit) and self.parentBlock:
			for (key, value) in self.parentBlock.getOptions_hash(inherit).items():
				if key not in options:
					options[key] = value

		return options

	def getOptions(self, inherit=None):
		options = []
		for component in self.components:
			if not isinstance(component, DHCPDConf_Option):
				continue
			options.append(component)

		if inherit and self.type != inherit and self.parentBlock:
			options.extend(self.parentBlock.getOptions(inherit))

		return options

	def getParameters_hash(self, inherit=None):
		parameters = {}
		for component in self.components:
			if not isinstance(component, DHCPDConf_Parameter):
				continue
			parameters[component.key] = component.value

		if inherit and self.type != inherit and self.parentBlock:
			for (key, value) in self.parentBlock.getParameters_hash(inherit).items():
				if key not in parameters:
					parameters[key] = value
		return parameters

	def getParameters(self, inherit=None):
		parameters = []

		if inherit and self.type != inherit and self.parentBlock:
			parameters.extend(self.parentBlock.getParameters(inherit))

		return parameters

	def getBlocks(self, type, recursive=False):
		blocks = []
		for component in self.components:
			if not isinstance(component, DHCPDConf_Block):
				continue
			if component.type == type:
				blocks.append(component)
			if recursive:
				blocks.extend(component.getBlocks(type, recursive))
		return blocks

	def asText(self):
		text = u''
		shifting = self.getShifting()
		if not isinstance(self, DHCPDConf_GlobalBlock):
			text += shifting + u' '.join(self.settings) + u' {\n'

		notWritten = self.components
		lineNumber = self.startLine
		if lineNumber < 1:
			lineNumber = 1

		while lineNumber <= self.endLine:
			if lineNumber not in self.lineRefs or not self.lineRefs[lineNumber]:
				lineNumber += 1
				continue

			for i, lineRef in enumerate(self.lineRefs[lineNumber]):
				compText = lineRef.asText()
				if i > 0 and isinstance(lineRef, DHCPDConf_Comment):
					compText = u' ' + compText.lstrip()
				text += compText
				# Mark component as written
				if lineRef in notWritten:
					notWritten.remove(lineRef)
			text += u'\n'
			lineNumber += 1

		for component in notWritten:
			text += component.asText() + u'\n'

		if not isinstance(self, DHCPDConf_GlobalBlock):
			# Write '}' to close block
			text += shifting + u'}'

		return text


class DHCPDConf_GlobalBlock(DHCPDConf_Block):
	def __init__(self):
		DHCPDConf_Block.__init__(self, 1, None, u'global')


class DHCPDConfFile(TextFile):

	def __init__(self, filename, lockFailTimeout=2000):
		TextFile.__init__(self, filename, lockFailTimeout)

		self._currentLine = 0
		self._currentToken = None
		self._currentIndex = -1
		self._data = u''
		self._currentBlock = None
		self._globalBlock = None
		self._parsed = False

		logger.debug(u"Parsing dhcpd conf file '%s'" % self._filename)

	def getGlobalBlock(self):
		return self._globalBlock

	def parse(self, lines=None):
		self._currentLine = 0
		self._currentToken = None
		self._currentIndex = -1
		self._data = u''
		self._currentBlock = self._globalBlock = DHCPDConf_GlobalBlock()
		self._parsed = False

		if lines:
			self._lines = forceUnicodeList(lines)
		else:
			self.readlines()
		self._globalBlock.endLine = len(self._lines)

		minIndex = 0
		while True:
			self._currentToken = None
			self._currentIndex = -1
			if not self._data.strip():
				if not self._getNewData():
					break
				if not self._data.strip():
					self._parse_emptyline()
				continue
			for token in ('#', ';', '{', '}'):
				index = self._data.find(token)
				if (index != -1) and (index >= minIndex) and ((self._currentIndex == -1) or (index < self._currentIndex)):
					if (self._data[:index].count('"') % 2 == 1) or (self._data[:index].count("'") % 2 == 1):
						continue
					self._currentToken = token
					self._currentIndex = index
			if not self._currentToken:
				minIndex = len(self._data)
				if not self._getNewData():
					break
				continue
			minIndex = 0
			if self._currentToken == '#':
				self._parse_comment()
			elif self._currentToken == ';':
				self._parse_semicolon()
			elif self._currentToken == '{':
				self._parse_lbracket()
			elif self._currentToken == '}':
				self._parse_rbracket()
		self._parsed = True

	def generate(self):
		if not self._globalBlock:
			raise ValueError(u"Got no data to write")

		self.open('w')
		self.write(self._globalBlock.asText())
		self.close()

	@requiresParsing
	def addHost(self, hostname, hardwareAddress, ipAddress, fixedAddress, parameters=None):
		if not parameters:
			parameters = {}

		hostname = forceHostname(hostname)
		hardwareAddress = forceHardwareAddress(hardwareAddress)
		ipAddress = forceIPAddress(ipAddress)
		fixedAddress = forceUnicodeLower(fixedAddress)
		parameters = forceDict(parameters)

		existingHost = None
		for block in self._globalBlock.getBlocks('host', recursive=True):
			if block.settings[1].lower() == hostname:
				existingHost = block
			else:
				for (key, value) in block.getParameters_hash().items():
					if key == 'fixed-address' and value.lower() == fixedAddress:
						raise BackendBadValueError(u"Host '%s' uses the same fixed address" % block.settings[1])
					elif key == 'hardware' and value.lower() == 'ethernet %s' % hardwareAddress:
						raise BackendBadValueError(u"Host '%s' uses the same hardware ethernet address" % block.settings[1])

		if existingHost:
			logger.info(u"Host '%s' already exists in config file '%s', deleting first" % (hostname, self._filename))
			self.deleteHost(hostname)

		logger.notice(u"Creating host '%s', hardwareAddress '%s', ipAddress '%s', fixedAddress '%s', parameters '%s' in dhcpd config file '%s'" %
					(hostname, hardwareAddress, ipAddress, fixedAddress, parameters, self._filename))

		for (key, value) in parameters.items():
			parameters[key] = DHCPDConf_Parameter(-1, None, key, value).asHash()[key]

		# Default parent block is global
		parentBlock = self._globalBlock

		# Search the right subnet block
		for block in self._globalBlock.getBlocks('subnet', recursive=True):
			if ipAddressInNetwork(ipAddress, u'%s/%s' % (block.settings[1], block.settings[3])):
				logger.debug(u"Choosing subnet %s/%s for host %s" % (block.settings[1], block.settings[3], hostname))
				parentBlock = block

		# Search the right group for the host
		bestGroup = None
		bestMatchCount = 0
		for block in parentBlock.getBlocks('group'):
			matchCount = 0
			blockParameters = block.getParameters_hash(inherit='global')
			if blockParameters:
				# Block has parameters set, check if they match the hosts parameters
				for (key, value) in blockParameters.items():
					if key not in parameters:
						continue

					if parameters[key] == value:
						matchCount += 1
					else:
						matchCount -= 1

			if matchCount > bestMatchCount or matchCount >= 0 and not bestGroup:
				matchCount = bestMatchCount
				bestGroup = block

		if bestGroup:
			parentBlock = bestGroup

		# Remove parameters which are already defined in parents
		blockParameters = parentBlock.getParameters_hash(inherit='global')
		if blockParameters:
			for (key, value) in blockParameters.items():
				if key in parameters and parameters[key] == value:
					del parameters[key]

		hostBlock = DHCPDConf_Block(
			startLine=-1,
			parentBlock=parentBlock,
			type='host',
			settings=['host', hostname]
		)
		hostBlock.addComponent(DHCPDConf_Parameter(startLine=-1, parentBlock=hostBlock, key='fixed-address', value=fixedAddress))
		hostBlock.addComponent(DHCPDConf_Parameter(startLine=-1, parentBlock=hostBlock, key='hardware', value="ethernet %s" % hardwareAddress))
		for (key, value) in parameters.items():
			hostBlock.addComponent(
				DHCPDConf_Parameter(startLine=-1, parentBlock=hostBlock, key=key, value=value))

		parentBlock.addComponent(hostBlock)

	@requiresParsing
	def getHost(self, hostname):
		hostname = forceHostname(hostname)

		for block in self._globalBlock.getBlocks('host', recursive=True):
			if block.settings[1] == hostname:
				return block.getParameters_hash()
		return None

	@requiresParsing
	def deleteHost(self, hostname):
		hostname = forceHostname(hostname)

		logger.notice(u"Deleting host '%s' from dhcpd config file '%s'" % (hostname, self._filename))
		hostBlocks = []
		for block in self._globalBlock.getBlocks('host', recursive=True):
			if block.settings[1] == hostname:
				hostBlocks.append(block)
			else:
				for (key, value) in block.getParameters_hash().items():
					if key == 'fixed-address' and value == hostname:
						hostBlocks.append(block)

		if not hostBlocks:
			logger.warning(u"Failed to remove host '%s': not found" % hostname)
			return

		for block in hostBlocks:
			block.parentBlock.removeComponent(block)

	@requiresParsing
	def modifyHost(self, hostname, parameters):
		hostname = forceHostname(hostname)
		parameters = forceDict(parameters)

		logger.notice(u"Modifying host '%s' in dhcpd config file '%s'" % (hostname, self.filename))

		hostBlocks = []
		for block in self._globalBlock.getBlocks('host', recursive=True):
			if block.settings[1] == hostname:
				hostBlocks.append(block)
			else:
				for (key, value) in block.getParameters_hash().items():
					if key == 'fixed-address' and value == hostname:
						hostBlocks.append(block)
					elif key == 'hardware' and value.lower() == parameters.get('hardware'):
						raise BackendBadValueError(u"Host '%s' uses the same hardware ethernet address" % block.settings[1])

		if len(hostBlocks) != 1:
			raise BackendBadValueError(u"Host '%s' found %d times" % (hostname, len(hostBlocks)))

		hostBlock = hostBlocks[0]
		hostBlock.removeComponents()

		for (key, value) in parameters.items():
			parameters[key] = DHCPDConf_Parameter(-1, None, key, value).asHash()[key]

		for (key, value) in hostBlock.parentBlock.getParameters_hash(inherit='global').items():
			if key not in parameters:
				continue

			if parameters[key] == value:
				del parameters[key]

		for (key, value) in parameters.items():
			hostBlock.addComponent(
				DHCPDConf_Parameter(startLine=-1, parentBlock=hostBlock, key=key, value=value)
			)

	def _getNewData(self):
		if self._currentLine >= len(self._lines):
			return False
		self._data += self._lines[self._currentLine]
		self._currentLine += 1
		return True

	def _parse_emptyline(self):
		logger.debug2(u"_parse_emptyline")
		self._currentBlock.addComponent(
			DHCPDConf_EmptyLine(
				startLine=self._currentLine,
				parentBlock=self._currentBlock
			)
		)
		self._data = self._data[:self._currentIndex]

	def _parse_comment(self):
		logger.debug2(u"_parse_comment")
		self._currentBlock.addComponent(
			DHCPDConf_Comment(
				startLine=self._currentLine,
				parentBlock=self._currentBlock,
				data=self._data.strip()[1:]
			)
		)
		self._data = self._data[:self._currentIndex]

	def _parse_semicolon(self):
		logger.debug2(u"_parse_semicolon")
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex + 1:]

		key = data.split()[0]
		if key != 'option':
			# Parameter
			value = u' '.join(data.split()[1:]).strip()
			if len(value) > 1 and value.startswith('"') and value.endswith('"'):
				value = value[1:-1]

			self._currentBlock.addComponent(
				DHCPDConf_Parameter(
					startLine=self._currentLine,
					parentBlock=self._currentBlock,
					key=key,
					value=value
				)
			)
			return

		# Option
		key = data.split()[1]
		value = u' '.join(data.split()[2:]).strip()
		if len(value) > 1 and value.startswith('"') and value.endswith('"'):
			value = value[1:-1]
		values = []
		quote = u''
		current = []
		for l in value:
			if l == u'"':
				if quote == u'"':
					quote = u''
				elif quote == u"'":
					current.append(l)
				else:
					quote = u'"'
			elif l == u"'":
				if quote == u"'":
					quote = u''
				elif quote == u'"':
					current.append(l)
				else:
					quote = u"'"
			elif re.search(r'\s', l):
				current.append(l)
			elif l == u',':
				if quote:
					current.append(l)
				else:
					values.append(u''.join(current).strip())
					current = []
			else:
				current.append(l)

		if current:
			values.append(u''.join(current).strip())

		self._currentBlock.addComponent(
			DHCPDConf_Option(
				startLine=self._currentLine,
				parentBlock=self._currentBlock,
				key=key,
				value=values
			)
		)

	def _parse_lbracket(self):
		logger.debug2(u"_parse_lbracket")
		# Start of a block
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex+1:]
		# Split the block definition at whitespace
		# The first value is the block type
		# Example: subnet 194.31.185.0 netmask 255.255.255.0 => type is subnet
		block = DHCPDConf_Block(
			startLine=self._currentLine,
			parentBlock=self._currentBlock,
			type=data.split()[0].strip(),
			settings=data.split()
		)
		self._currentBlock.addComponent(block)
		self._currentBlock = block

	def _parse_rbracket(self):
		logger.debug2(u"_parse_rbracket")
		# End of a block
		data = self._data[:self._currentIndex]
		self._data = self._data[self._currentIndex+1:]

		self._currentBlock.endLine = self._currentLine
		self._currentBlock = self._currentBlock.parentBlock
