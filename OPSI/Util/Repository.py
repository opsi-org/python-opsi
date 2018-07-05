# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2018 uib GmbH <info@uib.de>

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
opsi python library - Repository
================================

Functionality to work with opsi repositories.


:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
.. codeauthor:: Jan Schneider <j.schneider@uib.de>
.. codeauthor:: Erol Ueluekmen <e.ueluekmen@uib.de>
.. codeauthor:: Niko Wenselowski <n.wenselowski@uib.de>
"""

import base64
import os
import re
import shutil
import stat
import time
import urllib

from http.client import HTTPConnection, HTTPSConnection, HTTPResponse

from OPSI.web2 import responsecode
from OPSI.web2.dav import davxml

from OPSI import __version__
from OPSI.Exceptions import RepositoryError
from OPSI.Logger import LOG_INFO, Logger
from OPSI.System import mount, umount
from OPSI.Types import forceBool, forceFilename, forceInt, forceUnicode, forceUnicodeList
from OPSI.Util.Message import ProgressSubject
from OPSI.Util import md5sum, randomString
from OPSI.Util.File.Opsi import PackageContentFile
from OPSI.Util.HTTP import getSharedConnectionPool, urlsplit
from OPSI.Util.HTTP import HTTPResponse as OpsiHTTPResponse

if os.name == 'nt':
	from OPSI.System.Windows import getFreeDrive

logger = Logger()


def _(string):
	return string


def getRepository(url, **kwargs):
	if re.search('^file://', url, re.IGNORECASE):
		return FileRepository(url, **kwargs)
	elif re.search('^https?://', url, re.IGNORECASE):
		return HTTPRepository(url, **kwargs)
	elif re.search('^webdavs?://', url, re.IGNORECASE):
		return WebDAVRepository(url, **kwargs)
	elif re.search('^(smb|cifs)://', url, re.IGNORECASE):
		return CIFSRepository(url, **kwargs)

	raise RepositoryError(u"Repository url '%s' not supported" % url)


class RepositoryHook(object):
	def __init__(self):
		pass

	def pre_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject):
		return (source, destination, overallProgressSubject, currentProgressSubject)

	def post_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject):
		return None

	def error_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject, exception):
		pass


class RepositoryObserver(object):
	def dynamicBandwidthLimitChanged(self, repository, bandwidth):
		pass


class Repository:
	def __init__(self, url, **kwargs):
		'''
		maxBandwidth must be in byte/s
		'''
		self._url = forceUnicode(url)
		self._path = u''
		self._maxBandwidth = 0
		self._dynamicBandwidth = False
		self._networkPerformanceCounter = None
		self._lastSpeedCalcTime = None
		self._bufferSize = 16384
		self._bytesTransfered = 0
		self._networkBandwidth = 0.0
		self._currentSpeed = 0.0
		self._averageSpeed = 0.0
		self._dynamicBandwidthLimit = 0.0
		self._dynamicBandwidthThresholdLimit = 0.75
		self._dynamicBandwidthThresholdNoLimit = 0.95
		self._dynamicBandwidthLimitRate = 0.2
		self._bandwidthSleepTime = 0.0
		self._hooks = []
		self._observers = []
		self.setBandwidth(
			kwargs.get('dynamicBandwidth', self._dynamicBandwidth),
			kwargs.get('maxBandwidth', self._maxBandwidth),
		)

	def setBandwidth(self, dynamicBandwidth=False, maxBandwidth=0):
		''' maxBandwidth in byte/s'''
		self._dynamicBandwidth = forceBool(dynamicBandwidth)
		self._maxBandwidth = forceInt(maxBandwidth)
		if self._maxBandwidth < 0:
			self._maxBandwidth = 0

		if self._dynamicBandwidth:
			if not self._networkPerformanceCounter:
				retry = 0
				exception = None
				from OPSI.System import getDefaultNetworkInterfaceName, NetworkPerformanceCounter
				while retry > 5:
					try:
						self._networkPerformanceCounter = NetworkPerformanceCounter(getDefaultNetworkInterfaceName())
						break
					except Exception as counterInitError:
						exception = forceUnicode(counterInitError)
						logger.debug("Setting dynamic bandwidth failed, waiting 5 sec and trying again.")
						retry += 1
						time.sleep(5)

				if exception:
					logger.logException(exception)
					logger.critical(u"Failed to enable dynamic bandwidth: %s" % exception)
					self._dynamicBandwidth = False
		elif self._networkPerformanceCounter:
			try:
				self._networkPerformanceCounter.stop()
			except Exception as counterStopError:
				logger.warning(u"Failed to stop networkPerformanceCounter: %s" % counterStopError)

	def setMaxBandwidth(self, maxBandwidth):
		self.setBandwidth(dynamicBandwidth=self._dynamicBandwidth, maxBandwidth=maxBandwidth)

	def __str__(self):
		return u"<{0}({1!r})>".format(self.__class__.__name__, self._url)

	def __repr__(self):
		return self.__str__()

	def addHook(self, hook):
		if not isinstance(hook, RepositoryHook):
			raise ValueError(u"Not a RepositoryHook: %s" % hook)

		if hook not in self._hooks:
			self._hooks.append(hook)

	def removeHook(self, hook):
		if not isinstance(hook, RepositoryHook):
			raise ValueError(u"Not a RepositoryHook: %s" % hook)

		try:
			self._hooks.remove(hook)
		except ValueError:  # element not in list
			pass

	def attachObserver(self, observer):
		if observer not in self._observers:
			self._observers.append(observer)

	def detachObserver(self, observer):
		if observer in self._observers:
			self._observers.remove(observer)

	def _fireEvent(self, event, *args):
		for obs in self._observers:
			try:
				meth = getattr(obs, event)
				meth(self, *args)
			except Exception as error:
				logger.error(error)

	def _transferDown(self, src, dst, progressSubject=None, bytes=-1):
		return self._transfer('in', src, dst, progressSubject, bytes=bytes)

	def _transferUp(self, src, dst, progressSubject=None):
		return self._transfer('out', src, dst, progressSubject)

	def _getNetworkUsage(self):
		networkUsage = 0.0
		if self._networkPerformanceCounter:
			if self._transferDirection == 'out':
				networkUsage = self._networkPerformanceCounter.getBytesOutPerSecond()
			else:
				networkUsage = self._networkPerformanceCounter.getBytesInPerSecond()
		return networkUsage

	def _calcSpeed(self, read):
		now = time.time()

		try:
			self._lastSpeedCalcBytes += read
		except AttributeError:
			self._lastSpeedCalcBytes = read

		try:
			self._lastAverageSpeedCalcBytes += read
		except AttributeError:
			self._lastAverageSpeedCalcBytes = read

		if self._lastSpeedCalcTime is not None:
			delta = now - self._lastSpeedCalcTime
			if delta > 0:
				self._currentSpeed = float(self._lastSpeedCalcBytes) / float(delta)
				self._lastSpeedCalcBytes = 0

		try:
			delta = now - self._lastAverageSpeedCalcTime
			if delta > 1:
				self._averageSpeed = float(self._lastAverageSpeedCalcBytes) / float(delta)
				self._lastAverageSpeedCalcBytes = 0
				self._lastAverageSpeedCalcTime = now
		except AttributeError:
			self._lastAverageSpeedCalcTime = now
			self._averageSpeed = self._currentSpeed

		self._lastSpeedCalcTime = now

	def _bandwidthLimit(self):
		if not (self._dynamicBandwidth and self._networkPerformanceCounter) and not self._maxBandwidth:
			return

		now = time.time()
		bwlimit = 0.0
		if self._dynamicBandwidth and self._networkPerformanceCounter:
			bwlimit = self._dynamicBandwidthLimit
			totalNetworkUsage = self._getNetworkUsage()
			if totalNetworkUsage > 0:
				if not self._dynamicBandwidthLimit:
					self._networkBandwidth = totalNetworkUsage

				usage = (float(self._averageSpeed) / float(totalNetworkUsage)) * 1.03
				if usage > 1:
					usage = 1.0

				try:
					self._networkUsageData.append([now, usage])
				except AttributeError:
					self._networkUsageData = [[now, usage]]

				if self._networkUsageData and (now - self._networkUsageData[0][0]) >= 5:
					usage = 0.0
					count = 0.0
					index = -1

					for i, element in enumerate(self._networkUsageData):
						if now - element[0] <= 5:
							if index == -1:
								index = i

						if now - element[0] <= 2.0:
							usage += element[1]
							count += 1.0

					if count > 0:
						usage = float(usage) / float(count)
						logger.debug(u"Current network usage %0.2f kByte/s, last measured network bandwidth %0.2f kByte/s, usage: %0.5f, dynamic limit: %0.2f kByte/s"
								% ((float(totalNetworkUsage) / 1024), (float(self._networkBandwidth) / 1024), usage, float(bwlimit) / 1024))

						if index > 1:
							self._networkUsageData = self._networkUsageData[index-1:]

						if self._dynamicBandwidthLimit:
							if usage >= self._dynamicBandwidthThresholdNoLimit:
								logger.info(u"No other traffic detected, resetting dynamically limited bandwidth, using 100%")
								bwlimit = self._dynamicBandwidthLimit = 0.0
								self._networkUsageData = []
								self._fireEvent('dynamicBandwidthLimitChanged', self._dynamicBandwidthLimit)
						else:
							if usage <= self._dynamicBandwidthThresholdLimit:
								if self._averageSpeed < 20000:
									self._dynamicBandwidthLimit = bwlimit = 0.0
									logger.debug(u"Other traffic detected, not limiting traffic because average speed is only %0.2f kByte/s" % (float(self._averageSpeed) / 1024))
								else:
									self._dynamicBandwidthLimit = bwlimit = self._averageSpeed * self._dynamicBandwidthLimitRate
									if self._dynamicBandwidthLimit < 10000:
										self._dynamicBandwidthLimit = bwlimit = 10000
										logger.info(u"Other traffic detected, dynamically limiting bandwidth to minimum of %0.2f kByte/s" % (float(bwlimit) / 1024))
									else:
										logger.info(u"Other traffic detected, dynamically limiting bandwidth to %0.1f%% of last average to %0.2f kByte/s" \
											% (float(self._dynamicBandwidthLimitRate) * 100, float(bwlimit) / 1024))
									self._fireEvent('dynamicBandwidthLimitChanged', self._dynamicBandwidthLimit)
								self._networkUsageData = []

		if self._maxBandwidth and (bwlimit == 0 or bwlimit > self._maxBandwidth):
			bwlimit = float(self._maxBandwidth)

		speed = float(self._currentSpeed)
		if bwlimit > 0 and speed > 0:
			factor = 1.0
			if speed > bwlimit:
				# Too fast
				factor = float(speed) / float(bwlimit)
				logger.debug(u"Transfer speed %0.2f kByte/s is to fast, limit: %0.2f kByte/s, factor: %0.5f" \
					% ((speed / 1024), (bwlimit / 1024), factor))

				if factor < 1.001:
					bandwidthSleepTime = self._bandwidthSleepTime + (0.00007 * factor)
				elif factor < 1.01:
					bandwidthSleepTime = self._bandwidthSleepTime + (0.0007 * factor)
				else:
					bandwidthSleepTime = self._bandwidthSleepTime + (0.007 * factor)
				self._bandwidthSleepTime = (bandwidthSleepTime + self._bandwidthSleepTime) / 2
			else:
				# Too slow
				factor = float(bwlimit) / float(speed)
				logger.debug(u"Transfer speed %0.2f kByte/s is to slow, limit: %0.2f kByte/s, factor: %0.5f" \
					% ((speed / 1024), (bwlimit / 1024), factor))

				if factor < 1.001:
					bandwidthSleepTime = self._bandwidthSleepTime - (0.00006 * factor)
				elif factor < 1.01:
					bandwidthSleepTime = self._bandwidthSleepTime - (0.0006 * factor)
				else:
					bandwidthSleepTime = self._bandwidthSleepTime - (0.006 * factor)
				self._bandwidthSleepTime = (bandwidthSleepTime + self._bandwidthSleepTime) / 2

			if factor > 2:
				self._networkUsageData = []

			if self._bandwidthSleepTime <= 0.0:
				self._bandwidthSleepTime = 0.000001

			if self._bandwidthSleepTime <= 0.2:
				self._bufferSize = int(float(self._bufferSize) * 1.03)
				self._networkUsageData = []
			elif self._bandwidthSleepTime > 0.3:
				self._bufferSize = int(float(self._bufferSize) / 1.1)
				self._bandwidthSleepTime = 0.3
				self._networkUsageData = []

			if self._bufferSize > 262144:
				self._bufferSize = 262144
			elif self._bufferSize < 1:
				self._bufferSize = 1

			logger.debug(u"Transfer speed %0.2f kByte/s, limit: %0.2f kByte/s, sleep time: %0.6f, buffer size: %s" \
				% (speed / 1024, bwlimit / 1024, self._bandwidthSleepTime, self._bufferSize))
		else:
			self._bandwidthSleepTime = 0.000001
			self._bufferSize = 16384

		time.sleep(self._bandwidthSleepTime)

	def _transfer(self, transferDirection, src, dst, progressSubject=None, bytes=-1):
		logger.debug(u"Transfer %s from %s to %s, dynamic bandwidth %s, max bandwidth %s" % (transferDirection, src, dst, self._dynamicBandwidth, self._maxBandwidth))
		try:
			self._transferDirection = transferDirection
			self._bytesTransfered = 0
			transferStartTime = time.time()
			buf = True

			if isinstance(src, HTTPResponse) or hasattr(src, 'length'):
				fileSize = src.length
			else:
				fileSize = os.path.getsize(src.name)
			logger.debug('Filesize is: {0}'.format(fileSize))

			while buf and (bytes < 0 or self._bytesTransfered < bytes):
				logger.debug2("self._bufferSize: '%d" % self._bufferSize)
				logger.debug2("self._bytesTransfered: '%d'" % self._bytesTransfered)
				logger.debug2("bytes: '%d'" % bytes)

				remaining_bytes = fileSize - self._bytesTransfered
				logger.debug2("self._remainingBytes: '%d'" % remaining_bytes)
				if remaining_bytes > 0 and remaining_bytes < self._bufferSize:
					buf = src.read(remaining_bytes)
				elif remaining_bytes > 0:
					buf = src.read(self._bufferSize)
				else:
					break

				read = len(buf)

				if read > 0:
					if bytes >= 0 and (self._bytesTransfered + read) > bytes:
						buf = buf[:bytes-self._bytesTransfered]
						read = len(buf)
					self._bytesTransfered += read
					if isinstance(dst, (HTTPConnection, HTTPSConnection)):
						dst.send(buf)
					else:
						dst.write(buf)

					if progressSubject:
						progressSubject.addToState(read)

					self._calcSpeed(read)
					if self._dynamicBandwidth or self._maxBandwidth:
						self._bandwidthLimit()
					elif self._currentSpeed > 1000000:
						self._bufferSize = 262144

			transferTime = time.time() - transferStartTime
			if transferTime == 0:
				transferTime = 0.0000001
			logger.info(u"Transfered %0.2f kByte in %0.2f minutes, average speed was %0.2f kByte/s" % \
				((float(self._bytesTransfered) / 1024), (float(transferTime) / 60), (float(self._bytesTransfered)/transferTime) / 1024))
			return self._bytesTransfered
		except Exception as error:
			logger.logException(error, LOG_INFO)
			raise

	def _preProcessPath(self, path):
		return path

	def content(self, source='', recursive=False):
		"""
		List the content of the repository.

		The returned entries are a dict with the following keys:
		`name`, `size`, `path` and `type`.
		`name` is the name of file or folder.
		`path` is the relative path.
		`type` is either 'file' or 'dir'.

		:param recursive: Recursive listing?
		:type recursive: bool
		:returns: Content of the repository.
		:rtype: [dict, ]
		"""
		raise RepositoryError(u"Not implemented")

	def listdir(self, source=''):
		return [c['name'] for c in self.content(source, recursive=False)]

	def getCountAndSize(self, source=''):
		source = forceUnicode(source)
		count = 0
		size = 0
		for entry in self.content(source, recursive=True):
			if entry.get('type', '') == 'file':
				count += 1
				size += entry.get('size', 0)

		return (count, size)

	def fileInfo(self, source):
		source = forceUnicode(source)
		info = {}
		try:
			parts = source.split('/')
			dirname = u'/'.join(parts[:-1])
			filename = parts[-1]
			if not filename:
				return {
					'name': dirname.split('/')[:-1],
					'path': dirname.split('/')[:-1],
					'type': 'dir',
					'size': 0
				}

			for c in self.content(dirname):
				if c['name'] == filename:
					info = c
					return info
			raise IOError(u'File not found')
		except Exception as error:
			raise RepositoryError(u"Failed to get file info for '%s': %s" % (source, error))

	def exists(self, source):
		try:
			self.fileInfo(source)
		except Exception:
			return False

		return True

	def islink(self, source):
		return False

	def isfile(self, source):
		try:
			info = self.fileInfo(source)
			return info.get('type', '') == 'file'
		except Exception:
			return False

	def isdir(self, source):
		try:
			info = self.fileInfo(source)
			return info.get('type', '') == 'dir'
		except Exception:
			return False

	def copy(self, source, destination, overallProgressSubject=None, currentProgressSubject=None):
		'''
		source = file,  destination = file              => overwrite destination
		source = file,  destination = dir               => copy into destination
		source = file,  destination = not existent      => create destination directories, copy source to destination
		source = dir,   destination = file              => error
		source = dir,   destination = dir               => copy source dir into destination
		source = dir,   destination = not existent      => create destination, copy content of source into destination
		source = dir/*, destination = dir/not existent  => create destination if not exists, copy content of source into destination
		'''
		for hook in self._hooks:
			(source, destination, overallProgressSubject, currentProgressSubject) = hook.pre_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject)

		try:
			source = forceFilename(source)
			destination = forceFilename(destination)

			copySrcContent = False

			if source.endswith(('/*.*', '\\*.*')):
				source = source[:-4]
				copySrcContent = True

			elif source.endswith(('/*', '\\*')):
				source = source[:-2]
				copySrcContent = True

			if copySrcContent and not self.isdir(source):
				raise IOError(u"Source directory '%s' not found" % source)

			logger.info(u"Copying from '%s' to '%s'" % (source, destination))

			totalFiles = 0
			size = 0
			info = self.fileInfo(source)

			if overallProgressSubject:
				overallProgressSubject.reset()
				if info.get('type') == 'file':
					(totalFiles, size) = (1, info['size'])
				else:
					(totalFiles, size) = self.getCountAndSize(source)
				overallProgressSubject.setEnd(size)

			if info.get('type') == 'file':
				destinationFile = destination
				if not os.path.exists(destination):
					parent = os.path.dirname(destination)
					if not os.path.exists(parent):
						os.makedirs(parent)
				elif os.path.isdir(destination):
					destinationFile = os.path.join(destination, info['name'])

				if overallProgressSubject:
					sizeString = "%d Byte" % info['size']
					if info['size'] > 1024 * 1024:
						sizeString = "%0.2f MByte" % (float(info['size']) / (1024 * 1024))
					elif info['size'] > 1024:
						sizeString = "%0.2f kByte" % (float(info['size']) / 1024)
					overallProgressSubject.setMessage(u"[1/1] %s (%s)" % (info['name'], sizeString))

				try:
					self.download(source, destinationFile, currentProgressSubject)
				except OSError as error:
					if error.errno != 1:
						raise
					# Operation not permitted
					logger.debug(error)

				if overallProgressSubject:
					overallProgressSubject.addToState(info['size'])

			elif info.get('type') == 'dir':
				if not os.path.exists(destination):
					os.makedirs(destination)
				elif os.path.isfile(destination):
					raise IOError(u"Cannot copy directory '%s' into file '%s'" % (source, destination))
				elif os.path.isdir(destination):
					if not copySrcContent:
						destination = os.path.join(destination, info['name'])
				content = self.content(source, recursive=True)
				fileCount = 0
				for c in content:
					if c.get('type') == 'dir':
						path = [destination]
						path.extend(c['path'].split('/'))
						targetDir = os.path.join(*path)
						if not targetDir:
							raise RuntimeError(u"Bad target directory '%s'" % targetDir)
						if not os.path.isdir(targetDir):
							os.makedirs(targetDir)
					elif c.get('type') == 'file':
						fileCount += 1
						if overallProgressSubject:
							countLen = len(str(totalFiles))
							countLenFormat = '%' + str(countLen) + 's'
							sizeString = "%d Byte" % c['size']
							if c['size'] > 1024 * 1024:
								sizeString = "%0.2f MByte" % (float(c['size']) / (1024 * 1024))
							elif c['size'] > 1024:
								sizeString = "%0.2f kByte" % (float(c['size']) / 1024)
							overallProgressSubject.setMessage(u"[%s/%s] %s (%s)" \
									% (countLenFormat % fileCount, totalFiles, c['name'], sizeString))
						path = [destination]
						path.extend(c['path'].split('/')[:-1])
						targetDir = os.path.join(*path)
						if not targetDir:
							raise RuntimeError(u"Bad target directory '%s'" % targetDir)
						if targetDir and not os.path.isdir(targetDir):
							os.makedirs(targetDir)
						self.download(u'/'.join((source, c['path'])), os.path.join(targetDir, c['name']), currentProgressSubject)

						if overallProgressSubject:
							overallProgressSubject.addToState(c['size'])
			else:
				raise RuntimeError(u"Failed to copy: unknown source type '%s'" % source)
			logger.info(u'Copy done')
			if overallProgressSubject:
				overallProgressSubject.setState(size)
		except Exception as error:
			for hook in self._hooks:
				hook.error_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject, error)
			raise error

		for hook in self._hooks:
			hook.post_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject)

	def upload(self, source, destination):
		raise RepositoryError(u"Not implemented")

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):
		raise RepositoryError(u"Not implemented")

	def delete(self, destination):
		raise RepositoryError(u"Not implemented")

	def makeDirectory(self, destination):
		raise RepositoryError(u"Not implemented")

	def disconnect(self):
		if self._networkPerformanceCounter:
			try:
				self._networkPerformanceCounter.stop()
			except Exception:
				pass

	def __del__(self):
		try:
			self.disconnect()
		except Exception:
			pass


class FileRepository(Repository):

	def __init__(self, url, **kwargs):
		Repository.__init__(self, url, **kwargs)

		match = re.search('^file://(/[^/]+.*)$', self._url, re.IGNORECASE)
		if not match:
			raise RepositoryError(u"Bad file url: '%s'" % self._url)
		self._path = match.group(1)

	def _preProcessPath(self, path):
		path = forceUnicode(path)
		if path.startswith('/'):
			path = path[1:]
		if path.endswith('/'):
			path = path[:-1]
		path = self._path + u'/' + path
		if os.name == 'nt':
			path = path.replace('/', '\\')

		return path

	def fileInfo(self, source):
		source = self._preProcessPath(source)
		try:
			info = {
				'name': os.path.basename(source),
				'path': source[len(self._path)+1:],
				'type': 'file',
				'size': 0
			}
			if not os.path.exists(source):
				raise IOError(u'File not found')
			if os.path.isdir(source):
				info['type'] = 'dir'
			if os.path.isfile(source):
				info['size'] = os.path.getsize(source)
			return info
		except Exception as error:
			raise RepositoryError(u"Failed to get file info for '%s': %s" % (source, error))

	def exists(self, source):
		return os.path.exists(self._preProcessPath(source))

	def islink(self, source):
		return os.path.islink(self._preProcessPath(source))

	def isfile(self, source):
		return os.path.isfile(self._preProcessPath(source))

	def isdir(self, source):
		return os.path.isdir(self._preProcessPath(source))

	def content(self, source='', recursive=False):
		source = self._preProcessPath(source)
		srcLen = len(source)
		content = []

		def _recurse(path, content):
			path = os.path.abspath(forceFilename(path))
			for entry in os.listdir(path):
				try:
					info = {
						'name': entry,
						'size': 0,
						'type': 'file'
					}

					entry = os.path.join(path, entry)
					info['path'] = entry[srcLen:]
					if os.path.islink(entry) and not os.path.isdir(entry):
						pass
					elif os.path.isfile(entry):
						info['size'] = os.path.getsize(entry)
						content.append(info)
					elif os.path.isdir(entry):
						info['type'] = 'dir'
						content.append(info)
						if recursive:
							_recurse(path=entry, content=content)
				except Exception as error:
					logger.error(error)

			return content

		return _recurse(path=source, content=content)

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):
		'''
		startByteNumber: position of first byte to be read
		endByteNumber:   position of last byte to be read
		'''
		size = self.fileInfo(source)['size']
		source = self._preProcessPath(source)
		destination = forceUnicode(destination)
		startByteNumber = forceInt(startByteNumber)
		endByteNumber = forceInt(endByteNumber)

		if endByteNumber > -1:
			size -= endByteNumber
		if startByteNumber > -1:
			size -= startByteNumber

		logger.debug(u"Length of binary data to download: %d bytes" % size)

		if progressSubject:
			progressSubject.setEnd(size)

		try:
			with open(source, 'rb') as src:
				if startByteNumber > -1:
					src.seek(startByteNumber)
				bytes = -1
				if endByteNumber > -1:
					bytes = endByteNumber + 1
					if startByteNumber > -1:
						bytes -= startByteNumber

				if startByteNumber > 0 and os.path.exists(destination):
					dstWriteMode = 'ab'
				else:
					dstWriteMode = 'wb'

				with open(destination, dstWriteMode) as dst:
					self._transferDown(src, dst, progressSubject, bytes=bytes)
		except Exception as error:
			raise RepositoryError(u"Failed to download '%s' to '%s': %s" \
						% (source, destination, forceUnicode(error)))

	def upload(self, source, destination, progressSubject=None):
		source = forceUnicode(source)
		destination = self._preProcessPath(destination)

		fs = os.stat(source)
		size = fs[stat.ST_SIZE]
		logger.debug(u"Length of binary data to upload: %d" % size)

		if progressSubject:
			progressSubject.setEnd(size)

		try:
			with open(source, 'rb') as src:
				with open(destination, 'wb') as dst:
					self._transferUp(src, dst, progressSubject)
		except Exception as error:
			raise RepositoryError(u"Failed to upload '%s' to '%s': %s" \
						% (source, destination, error))

	def delete(self, destination):
		destination = self._preProcessPath(destination)
		os.unlink(destination)

	def makeDirectory(self, destination):
		destination = self._preProcessPath(destination)
		if not os.path.isdir(destination):
			os.mkdir(destination)


class HTTPRepository(Repository):

	def __init__(self, url, **kwargs):
		Repository.__init__(self, url, **kwargs)

		self._application = 'opsi repository module version %s' % __version__
		self._username = u''
		self._password = u''
		self._port = 80
		self._path = u'/'
		self._socketTimeout = None
		self._connectTimeout = 30
		self._retryTime = 5
		self._connectionPoolSize = 1
		self._cookie = ''
		self._proxy = None
		serverCertFile = None
		verifyServerCert = False
		caCertFile = None
		verifyServerCertByCa = False

		for key, value in kwargs.items():
			key = key.lower()
			if key == 'application':
				self._application = str(value)
			elif key == 'username':
				self._username = forceUnicode(value)
			elif key == 'password':
				self._password = forceUnicode(value)
			elif key == 'proxyurl':
				self._proxy = forceUnicode(value)
			elif key == 'servercertfile':
				serverCertFile = forceFilename(value)
			elif key == 'verifyservercert':
				verifyServerCert = forceBool(value)
			elif key == 'cacertfile':
				caCertFile = forceFilename(value)
			elif key == 'verifyservercertbyca':
				verifyServerCertByCa = forceBool(value)

		(scheme, host, port, baseurl, username, password) = urlsplit(self._url)

		if scheme not in ('http', 'https', 'webdav', 'webdavs'):
			raise RepositoryError(u"Bad http url: '%s'" % self._url)
		self._protocol = scheme
		if port:
			self._port = port
		elif self._protocol.endswith('s'):
			self._port = 443

		self._host = host
		self._path = baseurl
		if not self._username and username:
			self._username = username
		if not self._password and password:
			self._password = password
		self._username = forceUnicode(self._username)
		self._password = forceUnicode(self._password)
		if self._password:
			logger.addConfidentialString(self._password)

		auth = u'%s:%s' % (self._username, self._password)
		self._auth = 'Basic ' + base64.b64encode(auth.encode('latin-1'))

		self._connectionPool = getSharedConnectionPool(
			scheme=self._protocol,
			host=self._host,
			port=self._port,
			socketTimeout=self._socketTimeout,
			connectTimeout=self._connectTimeout,
			retryTime=self._retryTime,
			maxsize=self._connectionPoolSize,
			block=True,
			serverCertFile=serverCertFile,
			verifyServerCert=verifyServerCert,
			caCertFile=caCertFile,
			verifyServerCertByCa=verifyServerCertByCa,
			proxyURL=self._proxy
		)

	def _preProcessPath(self, path):
		path = forceUnicode(path).lstrip("/")
		path = (u"/".join([self._path, path])).lstrip("/")
		if not self._url.endswith("/"):
			path = u"/" + path

		path = path.rstrip("/")
		return urllib.quote(path.encode('utf-8'))

	def _headers(self):
		headers = {'user-agent': self._application}
		if self._cookie:
			headers['cookie'] = self._cookie
		if self._auth:
			headers['authorization'] = self._auth
		return headers

	def _processResponseHeaders(self, response):
		# Get cookie from header
		cookie = response.getheader('set-cookie', None)
		if cookie:
			# Store cookie
			self._cookie = cookie.split(';')[0].strip()

	def getPeerCertificate(self, asPem=False):
		return self._connectionPool.getPeerCertificate(asPem)

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):
		'''
		startByteNumber: position of first byte to be read
		endByteNumber:   position of last byte to be read
		'''
		destination = forceUnicode(destination)
		startByteNumber = forceInt(startByteNumber)
		endByteNumber = forceInt(endByteNumber)
		source = self._preProcessPath(source)

		try:
			trynum = 0
			bytesTransfered = 0
			while True:
				trynum += 1
				conn = self._connectionPool.getConnection()

				headers = self._headers()
				startByteNumber += bytesTransfered
				if startByteNumber > -1 or endByteNumber > -1:
					sbn = startByteNumber
					ebn = endByteNumber
					if sbn <= -1:
						sbn = 0
					if ebn <= -1:
						ebn = ''
					headers['range'] = 'bytes=%s-%s' % (sbn, ebn)
				if self._proxy:
					conn.putrequest('GET', source, skip_host=True)
					conn.putheader('Host', "%s:%s" % (self._host, self._port))
				else:
					conn.putrequest('GET', source)
				for key, value in headers.items():
					conn.putheader(key, value)
				conn.endheaders()
				conn.sock.settimeout(self._socketTimeout)

				httplib_response = None
				try:
					httplib_response = conn.getresponse()
					self._processResponseHeaders(httplib_response)
					if httplib_response.status not in (responsecode.OK, responsecode.PARTIAL_CONTENT):
						raise RuntimeError(httplib_response.status)
					size = forceInt(httplib_response.getheader('content-length', 0))
					logger.debug(u"Length of binary data to download: %d bytes" % size)

					if progressSubject:
						progressSubject.setEnd(size)

					if startByteNumber > 0 and os.path.exists(destination):
						mode = 'ab'
					else:
						mode = 'wb'

					with open(destination, mode) as dst:
						bytesTransfered = self._transferDown(httplib_response, dst, progressSubject)
				except Exception as error:
					conn = None
					self._connectionPool.endConnection(conn)
					if trynum > 2:
						raise
					logger.info(u"Error '%s' occurred while downloading, retrying" % error)
					continue
				response = OpsiHTTPResponse.from_httplib(httplib_response)
				conn = None
				self._connectionPool.endConnection(conn)
				break

		except Exception as error:
			logger.logException(error)
			raise RepositoryError(u"Failed to download '%s' to '%s': %s" % (source, destination, error))
		logger.debug2(u"HTTP download done")

	def disconnect(self):
		Repository.disconnect(self)
		if self._connectionPool:
			self._connectionPool.free()


class WebDAVRepository(HTTPRepository):

	def __init__(self, url, **kwargs):
		HTTPRepository.__init__(self, url, **kwargs)
		parts = self._url.split('/')
		if len(parts) < 3 or parts[0].lower() not in ('webdav:', 'webdavs:'):
			raise RepositoryError(u"Bad http url: '%s'" % self._url)
		self._contentCache = {}

	def content(self, source='', recursive=False):
		source = forceUnicode(source)

		source = self._preProcessPath(source)
		if not source.endswith('/'):
			source += '/'

		if recursive and source in self._contentCache:
			if time.time() - self._contentCache[source]['time'] > 60:
				del self._contentCache[source]
			else:
				return self._contentCache[source]['content']

		headers = self._headers()
		depth = '1'
		if recursive:
			depth = 'infinity'
		headers['depth'] = depth

		response = self._connectionPool.urlopen(method='PROPFIND', url=source, body=None, headers=headers, retry=True, redirect=True)
		self._processResponseHeaders(response)
		if response.status != responsecode.MULTI_STATUS:
			raise RepositoryError(u"Failed to list dir '%s': %s" % (source, response.status))

		encoding = 'utf-8'
		contentType = response.getheader('content-type', '').lower()
		for part in contentType.split(';'):
			if 'charset=' in part:
				encoding = part.split('=')[1].replace('"', '').strip()

		msr = davxml.WebDAVDocument.fromString(response.data)
		if not msr.root_element.children[0].childOfType(davxml.PropertyStatus).childOfType(davxml.PropertyContainer).childOfType(davxml.ResourceType).children:
			raise RepositoryError(u"Not a directory: '%s'" % source)

		content = []
		srcLen = len(source)
		for child in msr.root_element.children[1:]:
			pContainer = child.childOfType(davxml.PropertyStatus).childOfType(davxml.PropertyContainer)
			info = {
				'size': 0,
				'type': 'file',
				'path': unicode(urllib.unquote(child.childOfType(davxml.HRef).children[0].data[srcLen:]), encoding),
				'name': unicode(pContainer.childOfType(davxml.DisplayName).children[0].data, encoding),
			}

			if str(pContainer.childOfType(davxml.GETContentLength)) != 'None':
				info['size'] = int(str(pContainer.childOfType(davxml.GETContentLength)))

			if pContainer.childOfType(davxml.ResourceType).children:
				info['type'] = 'dir'
				if info['path'].endswith('/'):
					info['path'] = info['path'][:-1]

			content.append(info)

		if recursive:
			self._contentCache[source] = {
				'time': time.time(),
				'content': content
			}

		return content

	def upload(self, source, destination, progressSubject=None):
		source = forceUnicode(source)
		destination = self._preProcessPath(destination)
		self._contentCache = {}

		fs = os.stat(source)
		size = fs[stat.ST_SIZE]
		logger.debug(u"Length of binary data to upload: %d" % size)

		if progressSubject:
			progressSubject.setEnd(size)

		conn = None
		response = None
		try:
			headers = self._headers()
			headers['content-length'] = size

			trynum = 0
			while True:
				trynum += 1
				conn = self._connectionPool.getConnection()
				conn.putrequest('PUT', destination)
				for (k, v) in headers.items():
					conn.putheader(k, v)
				conn.endheaders()
				conn.sock.settimeout(self._socketTimeout)

				httplib_response = None
				try:
					with open(source, 'rb') as src:
						self._transferUp(src, conn, progressSubject)
					httplib_response = conn.getresponse()
				except Exception as error:
					conn = None
					self._connectionPool.endConnection(conn)
					if trynum > 2:
						raise
					logger.info(u"Error '%s' occurred while uploading, retrying" % error)
					continue
				response = OpsiHTTPResponse.from_httplib(httplib_response)
				conn = None
				self._connectionPool.endConnection(conn)
				break

			self._processResponseHeaders(response)
			if response.status not in (responsecode.CREATED, responsecode.NO_CONTENT):
				raise RuntimeError(response.status)
		except Exception as error:
			logger.logException(error)
			if conn:
				self._connectionPool.endConnection(None)
			raise RepositoryError(u"Failed to upload '%s' to '%s': %s" % (source, destination, forceUnicode(error)))
		logger.debug2(u"WebDAV upload done")

	def delete(self, destination):
		destination = self._preProcessPath(destination)

		headers = self._headers()
		response = self._connectionPool.urlopen(method='DELETE', url=destination, body=None, headers=headers, retry=True, redirect=True)
		self._processResponseHeaders(response)
		if response.status != responsecode.NO_CONTENT:
			raise RepositoryError(u"Failed to delete '%s': %s" % (destination, response.status))


class CIFSRepository(FileRepository):
	def __init__(self, url, **kwargs):
		Repository.__init__(self, url, **kwargs)

		match = re.search('^(smb|cifs)://([^/]+/.+)$', self._url, re.IGNORECASE)
		if not match:
			raise RepositoryError(u"Bad smb/cifs url: '%s'" % self._url)

		if os.name not in ('posix', 'nt'):
			raise NotImplementedError(u"CIFSRepository not yet avaliable on os '%s'" % os.name)

		self._mountShare = forceBool(kwargs.get('mount', True))
		self._mounted = False
		self._mountPointCreated = False

		self._mountPoint = kwargs.get('mountPoint')
		if not self._mountPoint:
			if os.name == 'posix':
				self._mountPoint = u'/tmp/.cifs-mount.%s' % randomString(5)
			elif os.name == 'nt':
				self._mountPoint = getFreeDrive(startLetter='g')

		self._username = forceUnicode(kwargs.get('username', 'guest'))
		self._password = forceUnicode(kwargs.get('password', ''))
		if self._password:
			logger.addConfidentialString(self._password)

		self._mountOptions = kwargs.get('mountOptions', {})

		if self._mountShare:
			self._path = self._mountPoint
		parts = match.group(2).split('/')
		if len(parts) > 2:
			self._path += u'/' + u'/'.join(parts[2:])
		if self._path.endswith('/'):
			self._path = self._path[:-1]
		if self._mountShare:
			self._mount()
		else:
			parts = self._url.split('/')
			self._path = u'\\\\%s\\%s%s' % (parts[2], parts[3], self._path.replace('/', '\\'))

	def getMountPoint(self):
		return self._mountPoint

	def _mount(self):
		if self._mounted:
			self._umount()
		if not self._mountPoint:
			raise ValueError(u"Mount point not defined")
		logger.info(u"Mountpoint: %s " % self._mountPoint)
		logger.info(u"Mounting '%s' to '%s'" % (self._url, self._mountPoint))
		if os.name == 'posix' and not os.path.isdir(self._mountPoint):
			os.makedirs(self._mountPoint)
			self._mountPointCreated = True

		try:
			mountOptions = self._mountOptions
			mountOptions['username'] = self._username
			mountOptions['password'] = self._password
			mount(self._url, self._mountPoint, **mountOptions)
			self._mounted = True
		except Exception as mountError:
			if self._mountPointCreated:
				try:
					os.rmdir(self._mountPoint)
				except Exception as removalError:
					logger.error(removalError)
			raise mountError

	def _umount(self):
		if not self._mounted or not self._mountPoint:
			return

		logger.info(u"Umounting '%s' from '%s'" % (self._url, self._mountPoint))

		umount(self._mountPoint)

		self._mounted = False
		if self._mountPointCreated:
			os.rmdir(self._mountPoint)

	def disconnect(self):
		FileRepository.disconnect(self)
		self._umount()


class DepotToLocalDirectorySychronizer(object):
	def __init__(self, sourceDepot, destinationDirectory, productIds=[], maxBandwidth=0, dynamicBandwidth=False):
		self._sourceDepot = sourceDepot
		self._destinationDirectory = forceUnicode(destinationDirectory)
		self._productIds = forceUnicodeList(productIds)
		if not os.path.isdir(self._destinationDirectory):
			os.mkdir(self._destinationDirectory)
		self._sourceDepot.setBandwidth(dynamicBandwidth=dynamicBandwidth, maxBandwidth=maxBandwidth)

	def _synchronizeDirectories(self, source, destination, progressSubject=None):
		source = forceUnicode(source)
		destination = forceUnicode(destination)
		logger.debug(u"Syncing directory %s to %s" % (source, destination))
		if not os.path.isdir(destination):
			os.mkdir(destination)

		for f in os.listdir(destination):
			relSource = (source + u'/' + f).split(u'/', 1)[1]
			if relSource == self._productId + u'.files':
				continue
			if relSource in self._fileInfo:
				continue

			path = os.path.join(destination, f)
			if os.path.isdir(path) and not os.path.islink(path):
				logger.info(u"Deleting '%s'" % relSource)
				shutil.rmtree(path)
			else:
				if path.endswith(u'.opsi_sync_endpart'):
					oPath = path[:-1 * len(".opsi_sync_endpart")]
					if os.path.isfile(oPath):
						logger.info(u"Appending '%s' to '%s'" % (path, oPath))
						with open(oPath, 'ab') as f1:
							with open(path, 'rb') as f2:
								f1.write(f2.read())
				logger.info(u"Deleting '%s'" % relSource)
				os.remove(path)

		for f in self._sourceDepot.content(source):
			source = forceUnicode(source)
			s = source + u'/' + f['name']
			d = os.path.join(destination, f['name'])
			relSource = s.split(u'/', 1)[1]
			if relSource == self._productId + u'.files':
				continue
			if relSource not in self._fileInfo:
				continue
			if f['type'] == 'dir':
				self._synchronizeDirectories(s, d, progressSubject)
			else:
				logger.debug(u"Syncing %s with %s %s" % (relSource, d, self._fileInfo[relSource]))
				if self._fileInfo[relSource]['type'] == 'l':
					self._linkFiles[relSource] = self._fileInfo[relSource]['target']
					continue
				size = 0
				localSize = 0
				exists = False
				if self._fileInfo[relSource]['type'] == 'f':
					size = int(self._fileInfo[relSource]['size'])
					exists = os.path.exists(d)
					if exists:
						md5s = md5sum(d)
						logger.debug(u"Destination file '%s' already exists (size: %s, md5sum: %s)" % (d, size, md5s))
						localSize = os.path.getsize(d)
						if (localSize == size) and (md5s == self._fileInfo[relSource]['md5sum']):
							continue

				if progressSubject:
					progressSubject.setMessage(_(u"Downloading file '%s'") % f['name'])

				if exists and (localSize < size):
					partialEndFile = d + u'.opsi_sync_endpart'
					# First byte needed is byte number <localSize>
					logger.info(u"Downloading file '%s' starting at byte number %d" % (f['name'], localSize))
					if os.path.exists(partialEndFile):
						os.remove(partialEndFile)
					self._sourceDepot.download(s, partialEndFile, startByteNumber=localSize)

					with open(d, 'ab') as f1:
						with open(partialEndFile, 'rb') as f2:
							f1.write(f2.read())

					md5s = md5sum(d)
					if md5s != self._fileInfo[relSource]['md5sum']:
						logger.warning(u"MD5sum of composed file differs")
						partialStartFile = d + u'.opsi_sync_startpart'
						if os.path.exists(partialStartFile):
							os.remove(partialStartFile)
						# Last byte needed is byte number <localSize> - 1
						logger.info(u"Downloading file '%s' ending at byte number %d" % (f['name'], localSize-1))
						self._sourceDepot.download(s, partialStartFile, endByteNumber=localSize - 1)

						with open(partialStartFile, 'ab') as f1:
							with open(partialEndFile, 'rb') as f2:
								f1.write(f2.read())

						if os.path.exists(d):
							os.remove(d)
						os.rename(partialStartFile, d)
					os.remove(partialEndFile)
				else:
					if exists:
						os.remove(d)
					logger.info(u"Downloading file '%s'" % f['name'])
					self._sourceDepot.download(s, d, progressSubject=progressSubject)
				md5s = md5sum(d)
				if md5s != self._fileInfo[relSource]['md5sum']:
					error = u"Failed to download '%s': MD5sum mismatch (local:%s != remote:%s)" % (f['name'], md5s, self._fileInfo[relSource]['md5sum'])
					logger.error(error)
					raise RuntimeError(error)

	def synchronize(self, productProgressObserver=None, overallProgressObserver=None):
		if not self._productIds:
			logger.info(u"Getting product dirs of depot '%s'" % self._sourceDepot)
			for c in self._sourceDepot.content():
				self._productIds.append(c['name'])

		overallProgressSubject = ProgressSubject(id='sync_products_overall', type='product_sync', end=len(self._productIds), fireAlways=True)
		overallProgressSubject.setMessage(_(u'Synchronizing products'))
		if overallProgressObserver:
			overallProgressSubject.attachObserver(overallProgressObserver)

		for self._productId in self._productIds:
			productProgressSubject = ProgressSubject(id='sync_product_' + self._productId, type='product_sync', fireAlways=True)
			productProgressSubject.setMessage(_(u"Synchronizing product %s") % self._productId)
			if productProgressObserver:
				productProgressSubject.attachObserver(productProgressObserver)
			packageContentFile = None

			try:
				self._linkFiles = {}
				logger.notice(u"Syncing product %s of depot %s with local directory %s" \
						% (self._productId, self._sourceDepot, self._destinationDirectory))

				productDestinationDirectory = os.path.join(self._destinationDirectory, self._productId)
				if not os.path.isdir(productDestinationDirectory):
					os.mkdir(productDestinationDirectory)

				logger.info(u"Downloading package content file")
				packageContentFile = os.path.join(productDestinationDirectory, u'%s.files' % self._productId)
				self._sourceDepot.download(u'%s/%s.files' % (self._productId, self._productId), packageContentFile)
				self._fileInfo = PackageContentFile(packageContentFile).parse()

				size = 0
				for value in self._fileInfo.values():
					try:
						size += int(value['size'])
					except KeyError:
						pass

				productProgressSubject.setMessage(_(u"Synchronizing product %s (%.2f kByte)") % (self._productId, (size / 1024)))
				productProgressSubject.setEnd(size)
				productProgressSubject.setEndChangable(False)

				self._synchronizeDirectories(self._productId, productDestinationDirectory, productProgressSubject)

				fs = self._linkFiles.keys()
				fs.sort()
				for f in fs:
					t = self._linkFiles[f]
					cwd = os.getcwd()
					os.chdir(productDestinationDirectory)
					try:
						if os.name == 'nt':
							if t.startswith('/'):
								t = t[1:]
							if f.startswith('/'):
								f = f[1:]
							t = os.path.join(productDestinationDirectory, t.replace('/', '\\'))
							f = os.path.join(productDestinationDirectory, f.replace('/', '\\'))
							if os.path.exists(f):
								if os.path.isdir(f):
									shutil.rmtree(f)
								else:
									os.remove(f)
							logger.info(u"Symlink => copying '%s' to '%s'" % (t, f))
							if os.path.isdir(t):
								shutil.copytree(t, f)
							else:
								shutil.copyfile(t, f)
						else:
							if os.path.exists(f):
								if os.path.isdir(f) and not os.path.islink(f):
									shutil.rmtree(f)
								else:
									os.remove(f)
							parts = len(f.split('/'))
							parts -= len(t.split('/'))
							for i in range(parts):
								t = os.path.join('..', t)
							logger.info(u"Symlink '%s' to '%s'" % (f, t))
							os.symlink(t, f)
					finally:
						os.chdir(cwd)
			except Exception as error:
				productProgressSubject.setMessage(_(u"Failed to sync product %s: %s") % (self._productId, error))
				if packageContentFile and os.path.exists(packageContentFile):
					os.unlink(packageContentFile)
				raise

			overallProgressSubject.addToState(1)

			if productProgressObserver:
				productProgressSubject.detachObserver(productProgressObserver)

		if overallProgressObserver:
			overallProgressSubject.detachObserver(overallProgressObserver)
