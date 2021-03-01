# -*- coding: utf-8 -*-

# This file is part of python-opsi.
# Copyright (C) 2006-2019 uib GmbH <info@uib.de>

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
:copyright: uib GmbH <info@uib.de>
:license: GNU Affero General Public License version 3
"""
# pylint: disable=too-many-lines

import os
import re
import shutil
import stat
import time
import urllib
import xml.etree.ElementTree as ET
from enum import IntEnum
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from urllib.parse import quote

from OPSI import __version__
from OPSI.Exceptions import RepositoryError
from OPSI.Logger import LOG_INFO, Logger
from OPSI.System import mount, umount
from OPSI.Types import (
	forceBool, forceFilename, forceInt, forceUnicode, forceUnicodeList)
from OPSI.Util.Message import ProgressSubject
from OPSI.Util import md5sum, randomString
from OPSI.Util.File.Opsi import PackageContentFile
from OPSI.Util.HTTP import (
	createBasicAuthHeader, getSharedConnectionPool, urlsplit)
from OPSI.Util.HTTP import HTTPResponse as OpsiHTTPResponse
from OPSI.Util.Path import cd

if os.name == 'nt':
	from OPSI.System.Windows import getFreeDrive

logger = Logger()


class ResponseCode(IntEnum):
	OK = 200
	CREATED = 201
	NO_CONTENT = 204
	PARTIAL_CONTENT = 206
	MULTI_STATUS = 207


def _(string):
	return string


def getRepository(url, **kwargs):
	if re.search(r'^file://', url, re.IGNORECASE):
		return FileRepository(url, **kwargs)
	if re.search(r'^https?://', url, re.IGNORECASE):
		return HTTPRepository(url, **kwargs)
	if re.search(r'^webdavs?://', url, re.IGNORECASE):
		return WebDAVRepository(url, **kwargs)
	if re.search(r'^(smb|cifs)://', url, re.IGNORECASE):
		return CIFSRepository(url, **kwargs)

	raise RepositoryError(f"Repository url '{url}' not supported")


def getFileInfosFromDavXML(davxmldata, encoding='utf-8'):  # pylint: disable=unused-argument,too-many-branches
	content = []
	root = ET.fromstring(davxmldata)
	for child in root:  # pylint: disable=too-many-nested-blocks
		info = {'size': 0, 'type': 'file', 'path': '', 'name': ''}
		if child.tag != "{DAV:}response":
			raise RepositoryError("No valid davxml given")

		if child[0].tag == "{DAV:}href":
			info['path'] = urllib.parse.unquote(child[0].text)
			info['name'] = info['path'].rstrip('/').split('/')[-1]

		if child[1].tag == "{DAV:}propstat":
			for node in child[1]:
				if node.tag != "{DAV:}prop":
					continue

				for childnode in node:
					tag = childnode.tag
					text = childnode.text
					if tag == "{DAV:}getcontenttype":
						if "directory" in text:
							info['type'] = 'dir'
					elif tag == "{DAV:}resourcetype":
						for resChild in childnode:
							if resChild.tag == "{DAV:}collection":
								info['type'] = 'dir'
					elif tag == "{DAV:}getcontentlength":
						if text != "None":
							info['size'] = int(text)
					#elif tag == "{DAV:}displayname":
					#	info['name'] = text

				# IIS Fix: Remove trailing backslash on file-paths
				if info['type'] == 'file' and info['path'].endswith("/"):
					info['path'] = info['path'][:-1]

			content.append(info)

	return content


class RepositoryHook:
	def __init__(self):
		pass

	def pre_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject):  # pylint: disable=no-self-use
		return (source, destination, overallProgressSubject, currentProgressSubject)

	def post_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject):  # pylint: disable=unused-argument,no-self-use
		return None

	def error_Repository_copy(self, source, destination, overallProgressSubject, currentProgressSubject, exception):  # pylint: disable=unused-argument,too-many-arguments
		pass


class RepositoryObserver:  # pylint: disable=too-few-public-methods
	def dynamicBandwidthLimitChanged(self, repository, bandwidth):  # pylint: disable=unused-argument
		pass


class Repository:  # pylint: disable=too-many-instance-attributes
	DEFAULT_BUFFER_SIZE = 32 * 1024

	def __init__(self, url, **kwargs):
		'''
		maxBandwidth must be in byte/s
		'''
		self._url = forceUnicode(url)
		self._path = ''
		self._maxBandwidth = 0
		self._dynamicBandwidth = False
		self._networkPerformanceCounter = None
		self._lastSpeedCalcTime = None
		self._lastAverageSpeedCalcTime = None
		self._bufferSize = self.DEFAULT_BUFFER_SIZE
		self._lastSpeedCalcBytes = 0
		self._lastAverageSpeedCalcBytes = 0
		self._bytesTransfered = 0
		self._networkBandwidth = 0.0
		self._currentSpeed = 0.0
		self._averageSpeed = 0.0
		self._dynamicBandwidthLimit = 0.0
		self._dynamicBandwidthThresholdLimit = 0.75
		self._dynamicBandwidthThresholdNoLimit = 0.95  # pylint: disable=invalid-name
		self._dynamicBandwidthLimitRate = 0.2
		self._bandwidthSleepTime = 0.0
		self._hooks = []
		self._observers = []
		self._networkUsageData = []
		self._transferDirection = None
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
				from OPSI.System import getDefaultNetworkInterfaceName, NetworkPerformanceCounter  # pylint: disable=import-outside-toplevel
				while retry > 5:
					try:
						self._networkPerformanceCounter = NetworkPerformanceCounter(getDefaultNetworkInterfaceName())
						break
					except Exception as err:  # pylint: disable=broad-except
						exception = str(err)
						logger.debug("Setting dynamic bandwidth failed, waiting 5 sec and trying again.")
						retry += 1
						time.sleep(5)

				if exception:
					logger.error(exception)
					logger.critical("Failed to enable dynamic bandwidth: %s", exception)
					self._dynamicBandwidth = False
		elif self._networkPerformanceCounter:
			try:
				self._networkPerformanceCounter.stop()
			except Exception as err:  # pylint: disable=broad-except
				logger.warning("Failed to stop networkPerformanceCounter: %s", err)

	def setMaxBandwidth(self, maxBandwidth):
		self.setBandwidth(dynamicBandwidth=self._dynamicBandwidth, maxBandwidth=maxBandwidth)

	def __str__(self):
		return f"<{self.__class__.__name__}({self._url})>"

	def __repr__(self):
		return self.__str__()

	def addHook(self, hook):
		if not isinstance(hook, RepositoryHook):
			raise ValueError(f"Not a RepositoryHook: {hook}")

		if hook not in self._hooks:
			self._hooks.append(hook)

	def removeHook(self, hook):
		if not isinstance(hook, RepositoryHook):
			raise ValueError(f"Not a RepositoryHook: {hook}")

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
			except Exception as err:  # pylint: disable=broad-except
				logger.error(err)

	def _transferDown(self, src, dst, progressSubject=None, bytes=-1):  # pylint: disable=redefined-builtin
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

		if not self._lastAverageSpeedCalcTime:
			self._lastAverageSpeedCalcTime = now
			self._averageSpeed = self._currentSpeed
		else:
			delta = now - self._lastAverageSpeedCalcTime
			if delta > 1:
				self._averageSpeed = float(self._lastAverageSpeedCalcBytes) / float(delta)
				self._lastAverageSpeedCalcBytes = 0
				self._lastAverageSpeedCalcTime = now

		self._lastSpeedCalcTime = now

	def _bandwidthLimit(self):  # pylint: disable=too-many-branches,too-many-statements
		if not (self._dynamicBandwidth and self._networkPerformanceCounter) and not self._maxBandwidth:
			return

		now = time.time()
		bwlimit = 0.0
		if self._dynamicBandwidth and self._networkPerformanceCounter:  # pylint: disable=too-many-nested-blocks
			bwlimit = self._dynamicBandwidthLimit
			totalNetworkUsage = self._getNetworkUsage()
			if totalNetworkUsage > 0:
				if not self._dynamicBandwidthLimit:
					self._networkBandwidth = totalNetworkUsage

				usage = (float(self._averageSpeed) / float(totalNetworkUsage)) * 1.03
				if usage > 1:
					usage = 1.0

				self._networkUsageData.append([now, usage])

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
						logger.debug(
							"Current network usage %0.2f kByte/s, last measured network bandwidth %0.2f kByte/s, "
							"usage: %0.5f, dynamic limit: %0.2f kByte/s",
							float(totalNetworkUsage) / 1024, float(self._networkBandwidth) / 1024,
							usage, float(bwlimit) / 1024
						)

						if index > 1:
							self._networkUsageData = self._networkUsageData[index - 1:]

						if self._dynamicBandwidthLimit:
							if usage >= self._dynamicBandwidthThresholdNoLimit:
								logger.info("No other traffic detected, resetting dynamically limited bandwidth, using 100%")
								bwlimit = self._dynamicBandwidthLimit = 0.0
								self._networkUsageData = []
								self._fireEvent('dynamicBandwidthLimitChanged', self._dynamicBandwidthLimit)
						else:
							if usage <= self._dynamicBandwidthThresholdLimit:
								if self._averageSpeed < 20000:
									self._dynamicBandwidthLimit = bwlimit = 0.0
									logger.debug(
										"Other traffic detected, not limiting traffic because average speed is only %0.2f kByte/s",
										float(self._averageSpeed) / 1024
									)
								else:
									self._dynamicBandwidthLimit = bwlimit = self._averageSpeed * self._dynamicBandwidthLimitRate
									if self._dynamicBandwidthLimit < 10000:
										self._dynamicBandwidthLimit = bwlimit = 10000
										logger.info(
											"Other traffic detected, dynamically limiting bandwidth to minimum of %0.2f kByte/s",
											float(bwlimit) / 1024
										)
									else:
										logger.info(
											"Other traffic detected, dynamically limiting bandwidth to %0.1f%% of last average to %0.2f kByte/s",
											float(self._dynamicBandwidthLimitRate) * 100,
											float(bwlimit) / 1024
										)
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
				logger.debug(
					"Transfer speed %0.2f kByte/s is to fast, limit: %0.2f kByte/s, factor: %0.5f",
					speed / 1024, bwlimit / 1024, factor
				)

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
				logger.debug(
					"Transfer speed %0.2f kByte/s is to slow, limit: %0.2f kByte/s, factor: %0.5f",
					speed / 1024, bwlimit / 1024, factor
				)

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

			logger.debug(
				"Transfer speed %0.2f kByte/s, limit: %0.2f kByte/s, sleep time: %0.6f, buffer size: %d",
				speed / 1024, bwlimit / 1024, self._bandwidthSleepTime, self._bufferSize
			)
		else:
			self._bandwidthSleepTime = 0.000001
			self._bufferSize = self.DEFAULT_BUFFER_SIZE

		time.sleep(self._bandwidthSleepTime)

	def _transfer(self, transferDirection, src, dst, progressSubject=None, bytes=-1):  # pylint: disable=redefined-builtin,too-many-arguments,too-many-branches
		logger.debug("Transfer %s from %s to %s, dynamic bandwidth %s, max bandwidth %s",
			transferDirection, src, dst, self._dynamicBandwidth, self._maxBandwidth
		)
		try:
			self._transferDirection = transferDirection
			self._bytesTransfered = 0
			transferStartTime = time.time()
			buf = True

			if isinstance(src, HTTPResponse) or hasattr(src, 'length'):
				fileSize = src.length
			else:
				fileSize = os.path.getsize(src.name)
			logger.debug('Filesize is: %s', fileSize)

			while buf and (bytes < 0 or self._bytesTransfered < bytes):
				logger.trace("self._bufferSize: %d", self._bufferSize)
				logger.trace("self._bytesTransfered: %d", self._bytesTransfered)
				logger.trace("bytes: %d", bytes)

				remainingBytes = fileSize - self._bytesTransfered
				logger.trace("remainingBytes: %d", remainingBytes)
				if 0 < remainingBytes < self._bufferSize:
					buf = src.read(remainingBytes)
				elif remainingBytes > 0:
					buf = src.read(self._bufferSize)
				else:
					break

				read = len(buf)

				if read > 0:
					if (self._bytesTransfered + read) > bytes >= 0:
						buf = buf[:bytes - self._bytesTransfered]
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
					#elif self._currentSpeed > 1000000:
					#	self._bufferSize = self.DEFAULT_BUFFER_SIZE

			transferTime = time.time() - transferStartTime
			if transferTime == 0:
				transferTime = 0.0000001
			logger.info(
				"Transfered %0.2f kByte in %0.2f minutes, average speed was %0.2f kByte/s",
				float(self._bytesTransfered) / 1024,
				float(transferTime) / 60,
				(float(self._bytesTransfered) / transferTime) / 1024
			)
			return self._bytesTransfered
		except Exception as error:
			logger.info(error, exc_info=True)
			raise

	def _preProcessPath(self, path):  # pylint: disable=no-self-use
		return path

	def content(self, source='', recursive=False):  # pylint: disable=no-self-use
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
		raise RepositoryError("Not implemented")

	def listdir(self, source=''):
		return [item['name'] for item in self.content(source, recursive=False)]

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
			dirname = '/'.join(parts[:-1])
			filename = parts[-1]
			if not filename:
				return {
					'name': dirname.split('/')[:-1],
					'path': dirname.split('/')[:-1],
					'type': 'dir',
					'size': 0
				}

			for item in self.content(dirname):
				if item['name'] == filename:
					info = item
					return info
			raise IOError('File not found')
		except Exception as err:  # pylint: disable=broad-except
			raise RepositoryError(f"Failed to get file info for '{source}': {err}") from err

	def exists(self, source):
		try:
			self.fileInfo(source)
		except Exception:  # pylint: disable=broad-except
			return False

		return True

	def islink(self, source):  # pylint: disable=unused-argument,no-self-use
		return False

	def isfile(self, source):
		try:
			info = self.fileInfo(source)
			return info.get('type', '') == 'file'
		except Exception:  # pylint: disable=broad-except
			return False

	def isdir(self, source):
		try:
			info = self.fileInfo(source)
			return info.get('type', '') == 'dir'
		except Exception:  # pylint: disable=broad-except
			return False

	def copy(self, source, destination, overallProgressSubject=None, currentProgressSubject=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
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
			(source, destination, overallProgressSubject, currentProgressSubject) = \
				hook.pre_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject)

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
				raise IOError(f"Source directory '{source}' not found")

			logger.info("Copying from '%s' to '%s'", source, destination)

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
					sizeString = f"{info['size']} Byte"
					if info['size'] > 1024 * 1024:
						sizeString = "%0.2f MByte" % (float(info['size']) / (1024 * 1024))
					elif info['size'] > 1024:
						sizeString = "%0.2f kByte" % (float(info['size']) / 1024)
					overallProgressSubject.setMessage(f"[1/1] {info['name']} ({sizeString})")

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
					raise IOError(f"Cannot copy directory '{source}' into file '{destination}'")
				elif os.path.isdir(destination):
					if not copySrcContent:
						destination = os.path.join(destination, info['name'])
				content = self.content(source, recursive=True)
				fileCount = 0
				for item in content:
					if item.get('type') == 'dir':
						path = [destination]
						path.extend(item['path'].split('/'))
						targetDir = os.path.join(*path)
						if not targetDir:
							raise RuntimeError(f"Bad target directory '{targetDir}'")
						if not os.path.isdir(targetDir):
							os.makedirs(targetDir)
					elif item.get('type') == 'file':
						fileCount += 1
						if overallProgressSubject:
							countLen = len(str(totalFiles))
							countLenFormat = '%' + str(countLen) + 's'
							sizeString = "%d Byte" % item['size']
							if item['size'] > 1024 * 1024:
								sizeString = "%0.2f MByte" % (float(item['size']) / (1024 * 1024))
							elif item['size'] > 1024:
								sizeString = "%0.2f kByte" % (float(item['size']) / 1024)

							overallProgressSubject.setMessage(
								"[%s/%s] %s (%s)" % (
									countLenFormat % fileCount,
									totalFiles,
									item['name'],
									sizeString
								)
							)
						path = [destination]
						path.extend(item['path'].split('/')[:-1])
						targetDir = os.path.join(*path)
						if not targetDir:
							raise RuntimeError(f"Bad target directory '{targetDir}'")
						if targetDir and not os.path.isdir(targetDir):
							os.makedirs(targetDir)
						self.download('/'.join((source, item['path'])), os.path.join(targetDir, item['name']), currentProgressSubject)

						if overallProgressSubject:
							overallProgressSubject.addToState(item['size'])
			else:
				raise RuntimeError(f"Failed to copy: unknown source type '{source}'")
			logger.info('Copy done')
			if overallProgressSubject:
				overallProgressSubject.setState(size)
		except Exception as error:
			for hook in self._hooks:
				hook.error_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject, error)
			raise error

		for hook in self._hooks:
			hook.post_Repository_copy(source, destination, overallProgressSubject, currentProgressSubject)

	def upload(self, source, destination, progressSubject=None):  # pylint: disable=no-self-use
		raise RepositoryError("Not implemented")

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):  # pylint: disable=no-self-use,too-many-arguments
		raise RepositoryError("Not implemented")

	def delete(self, destination):  # pylint: disable=no-self-use
		raise RepositoryError("Not implemented")

	def makeDirectory(self, destination):  # pylint: disable=no-self-use
		raise RepositoryError("Not implemented")

	def disconnect(self):
		if self._networkPerformanceCounter:
			try:
				self._networkPerformanceCounter.stop()
			except Exception:  # pylint: disable=broad-except
				pass

	def __del__(self):
		try:
			self.disconnect()
		except Exception:  # pylint: disable=broad-except
			pass


class FileRepository(Repository):

	def __init__(self, url, **kwargs):
		Repository.__init__(self, url, **kwargs)

		match = re.search(r'^file://(/[^/]+.*)$', self._url, re.IGNORECASE)
		if not match:
			raise RepositoryError(f"Bad file url: '{self._url}'")
		self._path = match.group(1)

	def _preProcessPath(self, path):
		path = forceUnicode(path)
		if path.startswith('/'):
			path = path[1:]
		if path.endswith('/'):
			path = path[:-1]
		path = self._path + '/' + path
		if os.name == 'nt':
			path = path.replace('/', '\\')

		return path

	def fileInfo(self, source):
		source = self._preProcessPath(source)
		try:
			if not os.path.exists(source):
				raise IOError('File not found')

			info = {
				'name': os.path.basename(source),
				'path': source[len(self._path) + 1:],
				'type': 'file',
				'size': 0
			}
			if os.path.isdir(source):
				info['type'] = 'dir'
			if os.path.isfile(source):
				info['size'] = os.path.getsize(source)
			return info
		except Exception as err:  # pylint: disable=broad-except
			raise RepositoryError(f"Failed to get file info for '{source}': {err}") from err

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
				except Exception as err:  # pylint: disable=broad-except
					logger.error(err)

			return content

		return _recurse(path=source, content=content)

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):  # pylint: disable=too-many-arguments
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

		logger.debug("Length of binary data to download: %d bytes", size)

		if progressSubject:
			progressSubject.setEnd(size)

		try:
			with open(source, 'rb') as src:
				if startByteNumber > -1:
					src.seek(startByteNumber)
				_bytes = -1
				if endByteNumber > -1:
					_bytes = endByteNumber + 1
					if startByteNumber > -1:
						_bytes -= startByteNumber

				if startByteNumber > 0 and os.path.exists(destination):
					dstWriteMode = 'ab'
				else:
					dstWriteMode = 'wb'

				with open(destination, dstWriteMode) as dst:
					self._transferDown(src, dst, progressSubject, bytes=_bytes)
		except Exception as err:  # pylint: disable=broad-except
			raise RepositoryError(f"Failed to download '{source}' to '{destination}': {err}") from err

	def upload(self, source, destination, progressSubject=None):
		source = forceUnicode(source)
		destination = self._preProcessPath(destination)

		fs = os.stat(source)
		size = fs[stat.ST_SIZE]
		logger.debug("Length of binary data to upload: %d", size)

		if progressSubject:
			progressSubject.setEnd(size)

		try:
			with open(source, 'rb') as src:
				with open(destination, 'wb') as dst:
					self._transferUp(src, dst, progressSubject)
		except Exception as err:
			raise RepositoryError(f"Failed to upload '{source}' to '{destination}': {err}") from err

	def delete(self, destination):
		destination = self._preProcessPath(destination)
		os.unlink(destination)

	def makeDirectory(self, destination):
		destination = self._preProcessPath(destination)
		if not os.path.isdir(destination):
			os.mkdir(destination)


class HTTPRepository(Repository):  # pylint: disable=too-many-instance-attributes

	_USER_AGENT = f"opsi-HTTPRepository/{__version__}"

	def __init__(self, url, **kwargs):  # pylint: disable=too-many-branches,too-many-statements
		Repository.__init__(self, url, **kwargs)

		self._application = self._USER_AGENT
		self._username = ''
		self._password = ''
		self._port = 80
		self._path = '/'
		self._socketTimeout = None
		self._connectTimeout = 30
		self._retryTime = 5
		self._connectionPoolSize = 1
		self._cookie = ''
		self._proxy = None
		verifyServerCert = False
		caCertFile = None

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
			elif key in ('verifyservercert', 'verifyservercertbyca'):
				verifyServerCert = forceBool(value)
			elif key == 'cacertfile':
				caCertFile = forceFilename(value)

		(scheme, host, port, baseurl, username, password) = urlsplit(self._url)

		if scheme not in ('http', 'https', 'webdav', 'webdavs'):
			raise RepositoryError(f"Bad http url: '{self._url}'")
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

		self._auth = createBasicAuthHeader(self._username, self._password)

		self._connectionPool = getSharedConnectionPool(
			scheme=self._protocol,
			host=self._host,
			port=self._port,
			socketTimeout=self._socketTimeout,
			connectTimeout=self._connectTimeout,
			retryTime=self._retryTime,
			maxsize=self._connectionPoolSize,
			block=True,
			verifyServerCert=verifyServerCert,
			caCertFile=caCertFile,
			proxyURL=self._proxy
		)

	def _preProcessPath(self, path):
		path = forceUnicode(path).lstrip("/")
		path = ("/".join([self._path, path])).lstrip("/")
		if not self._url.endswith("/"):
			path = "/" + path

		path = path.rstrip("/")
		return quote(path.encode('utf-8'))

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

	def download(self, source, destination, progressSubject=None, startByteNumber=-1, endByteNumber=-1):  # pylint: disable=too-many-arguments,too-many-locals,too-many-statements,too-many-branches
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
						ebn = ""
					headers["range"] = f"bytes={sbn}-{ebn}"
				if self._proxy:
					conn.putrequest("GET", source, skip_host=True)
					conn.putheader("Host", f"{self._host}:{self._port}")
				else:
					conn.putrequest("GET", source)
				for key, value in headers.items():
					conn.putheader(key, value)
				conn.endheaders()
				conn.sock.settimeout(self._socketTimeout)

				httplibResponse = None
				try:
					httplibResponse = conn.getresponse()
					self._processResponseHeaders(httplibResponse)
					if httplibResponse.status not in (ResponseCode.OK, ResponseCode.PARTIAL_CONTENT):
						raise RuntimeError(httplibResponse.status)
					size = forceInt(httplibResponse.getheader('content-length', 0))
					logger.debug("Length of binary data to download: %d bytes", size)

					if progressSubject:
						progressSubject.setEnd(size)

					if startByteNumber > 0 and os.path.exists(destination):
						mode = 'ab'
					else:
						mode = 'wb'

					with open(destination, mode) as dst:
						bytesTransfered = self._transferDown(httplibResponse, dst, progressSubject)
				except Exception as err:  # pylint: disable=broad-except
					conn = None
					self._connectionPool.endConnection(conn)
					if trynum > 2:
						raise
					logger.info("Error '%s' occurred while downloading, retrying", err)
					continue
				OpsiHTTPResponse.from_httplib(httplibResponse)

				conn = None
				self._connectionPool.endConnection(conn)
				break

		except Exception as err:
			logger.error(err, exc_info=True)
			raise RepositoryError(f"Failed to download '{source}' to '{destination}': {err}") from err
		logger.trace("HTTP download done")

	def disconnect(self):
		Repository.disconnect(self)
		if self._connectionPool:
			self._connectionPool.free()


class WebDAVRepository(HTTPRepository):

	_USER_AGENT = f"opsi-WebDAVRepository/{__version__}"

	def __init__(self, url, **kwargs):
		HTTPRepository.__init__(self, url, **kwargs)
		parts = self._url.split('/')
		if len(parts) < 3 or parts[0].lower() not in ('webdav:', 'webdavs:'):
			raise RepositoryError(f"Bad http url: '{self._url}'")
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
		if response.status != ResponseCode.MULTI_STATUS:
			raise RepositoryError(f"Failed to list dir '{source}': {response.status}")

		encoding = 'utf-8'
		contentType = response.getheader('content-type', '').lower()
		for part in contentType.split(';'):
			if 'charset=' in part:
				encoding = part.split('=')[1].replace('"', '').strip()

		davxmldata = response.data
		logger.trace("davxmldata: %s", davxmldata)
		content = []
		for entry in getFileInfosFromDavXML(davxmldata=davxmldata, encoding=encoding):
			if entry["path"].startswith("/"):
				# Absolut path to realtive path
				entry["path"] = os.path.relpath(entry["path"], start=source)
			content.append(entry)
		logger.debug("fileinfo: %s", content)

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
		logger.debug("Length of binary data to upload: %d", size)

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
				for (key, value) in headers.items():
					conn.putheader(key, value)
				conn.endheaders()
				conn.sock.settimeout(self._socketTimeout)

				httplibResponse = None
				try:
					with open(source, 'rb') as src:
						self._transferUp(src, conn, progressSubject)
					httplibResponse = conn.getresponse()
				except Exception as err:  # pylint: disable=broad-except
					conn = None
					self._connectionPool.endConnection(conn)
					if trynum > 2:
						raise
					logger.info("Error '%s' occurred while uploading, retrying", err)
					continue
				response = OpsiHTTPResponse.from_httplib(httplibResponse)
				conn = None
				self._connectionPool.endConnection(conn)
				break

			self._processResponseHeaders(response)
			if response.status not in (ResponseCode.CREATED, ResponseCode.NO_CONTENT):
				raise RuntimeError(response.status)
		except Exception as err:
			logger.error(err, exc_info=True)
			if conn:
				self._connectionPool.endConnection(None)
			raise RepositoryError(f"Failed to upload '{source}' to '{destination}': {err}") from err
		logger.trace("WebDAV upload done")

	def delete(self, destination):
		destination = self._preProcessPath(destination)

		headers = self._headers()
		response = self._connectionPool.urlopen(method='DELETE', url=destination, body=None, headers=headers, retry=True, redirect=True)
		self._processResponseHeaders(response)
		if response.status != ResponseCode.NO_CONTENT:
			raise RepositoryError(f"Failed to delete '{destination}': {response.status}")


class CIFSRepository(FileRepository):  # pylint: disable=too-many-instance-attributes
	def __init__(self, url, **kwargs):  # pylint: disable=super-init-not-called
		Repository.__init__(self, url, **kwargs)  # pylint: disable=non-parent-init-called

		match = re.search(r'^(smb|cifs)://([^/]+/.+)$', self._url, re.IGNORECASE)
		if not match:
			raise RepositoryError(f"Bad smb/cifs url: '{self._url}'")

		if os.name not in ('posix', 'nt'):
			raise NotImplementedError(f"CIFSRepository not yet avaliable on os '{os.name}'")

		self._mountShare = forceBool(kwargs.get('mount', True))
		self._mounted = False
		self._mountPointCreated = False

		self._mountPoint = kwargs.get('mountPoint')
		if not self._mountPoint:
			if os.name == 'posix':
				self._mountPoint = f'/tmp/.cifs-mount.{randomString(5)}'
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
			self._path += '/' + '/'.join(parts[2:])
		if self._path.endswith('/'):
			self._path = self._path[:-1]
		if self._mountShare:
			self._mount()
		else:
			parts = self._url.split('/')
			self._path = "\\\\" + parts[2] + "\\" + parts[3] + self._path.replace('/', '\\')

	def getMountPoint(self):
		return self._mountPoint

	def _mount(self):
		if self._mounted:
			self._umount()
		if not self._mountPoint:
			raise ValueError("Mount point not defined")
		logger.info("Mountpoint: %s ", self._mountPoint)
		logger.info("Mounting '%s' to '%s'", self._url, self._mountPoint)
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
				except Exception as err:  # pylint: disable=broad-except
					logger.error(err)
			raise mountError

	def _umount(self):
		if not self._mounted or not self._mountPoint:
			return

		logger.info("Umounting '%s' from '%s'", self._url, self._mountPoint)

		umount(self._mountPoint)

		self._mounted = False
		if self._mountPointCreated:
			os.rmdir(self._mountPoint)

	def disconnect(self):
		FileRepository.disconnect(self)
		self._umount()


class DepotToLocalDirectorySychronizer:  # pylint: disable=too-few-public-methods
	def __init__(self, sourceDepot, destinationDirectory, productIds=None, maxBandwidth=0, dynamicBandwidth=False):  # pylint: disable=too-many-arguments
		productIds = productIds or []
		self._sourceDepot = sourceDepot
		self._destinationDirectory = forceUnicode(destinationDirectory)
		self._productIds = forceUnicodeList(productIds)
		self._productId = None
		self._linkFiles = {}
		self._fileInfo = None
		if not os.path.isdir(self._destinationDirectory):
			os.mkdir(self._destinationDirectory)
		self._sourceDepot.setBandwidth(dynamicBandwidth=dynamicBandwidth, maxBandwidth=maxBandwidth)

	def _synchronizeDirectories(self, source, destination, progressSubject=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		source = forceUnicode(source)
		destination = forceUnicode(destination)
		logger.debug("Syncing directory %s to %s", source, destination)
		if not os.path.isdir(destination):
			if os.path.exists(destination):
				os.remove(destination)
			os.mkdir(destination)

		# Local directory cleanup
		for item in os.listdir(destination):
			relSource = (source + '/' + item).split('/', 1)[1]
			if relSource == self._productId + '.files':
				continue
			if relSource in self._fileInfo:
				continue

			path = os.path.join(destination, item)
			logger.info("Deleting '%s'", relSource)
			if os.path.isdir(path) and not os.path.islink(path):
				shutil.rmtree(path)
			else:
				os.remove(path)

		# Start sync
		for item in self._sourceDepot.content(source):  # pylint: disable=too-many-nested-blocks
			source = forceUnicode(source)
			sourcePath = source + '/' + item['name']
			destinationPath = os.path.join(destination, item['name'])
			relSource = sourcePath.split('/', 1)[1]
			if relSource == self._productId + '.files':
				continue
			if relSource not in self._fileInfo:
				continue
			if self._fileInfo[relSource]['type'] == 'd':
				self._synchronizeDirectories(sourcePath, destinationPath, progressSubject)
			else:
				logger.debug("Syncing %s with %s %s", relSource, destinationPath, self._fileInfo[relSource])
				if self._fileInfo[relSource]['type'] == 'l':
					self._linkFiles[relSource] = self._fileInfo[relSource]['target']
					continue
				size = 0
				localSize = 0
				exists = False
				if self._fileInfo[relSource]['type'] == 'f':
					size = int(self._fileInfo[relSource]['size'])
					exists = os.path.exists(destinationPath)
					if exists:
						md5s = md5sum(destinationPath)
						logger.debug("Destination file '%s' already exists (size: %s, md5sum: %s)", destinationPath, size, md5s)
						localSize = os.path.getsize(destinationPath)
						if (localSize == size) and (md5s == self._fileInfo[relSource]['md5sum']):
							continue

				if progressSubject:
					progressSubject.setMessage(_("Downloading file '%s'") % item['name'])

				partialEndFile = f"{destinationPath}.opsi_sync_endpart"
				partialStartFile = f"{destinationPath}.opsi_sync_startpart"

				composed = False
				if exists and (localSize < size):
					try:
						# First byte needed is byte number <localSize>
						logger.info("Downloading file '%s' starting at byte number %d", item['name'], localSize)
						if os.path.exists(partialEndFile):
							os.remove(partialEndFile)
						self._sourceDepot.download(sourcePath, partialEndFile, startByteNumber=localSize)

						with open(destinationPath, 'ab') as f1:
							with open(partialEndFile, 'rb') as f2:
								shutil.copyfileobj(f2, f1)

						md5s = md5sum(destinationPath)
						if md5s != self._fileInfo[relSource]['md5sum']:
							logger.info("MD5sum of composed file differs after downloading end part")
							if os.path.exists(partialStartFile):
								os.remove(partialStartFile)
							# Last byte needed is byte number <localSize> - 1
							logger.info("Downloading file '%s' ending at byte number %d", item['name'], localSize - 1)
							self._sourceDepot.download(sourcePath, partialStartFile, endByteNumber=localSize - 1)

							with open(partialStartFile, 'ab') as f1:
								with open(partialEndFile, 'rb') as f2:
									shutil.copyfileobj(f2, f1)

							if os.path.exists(destinationPath):
								os.remove(destinationPath)
							os.rename(partialStartFile, destinationPath)
							md5s = md5sum(destinationPath)
							if md5s != self._fileInfo[relSource]['md5sum']:
								logger.info("MD5sum of composed file differs after downloading start part")
								raise RuntimeError("MD5sum differs")
						composed = True
					except Exception as err:  # pylint: disable=broad-except
						logger.warning("Error completing a partially downloaded file '%s': %s", item['name'], err, exc_info=True)

				for fn in (partialEndFile, partialStartFile):
					if os.path.exists(fn):
						os.remove(fn)

				if not composed:
					if os.path.exists(destinationPath):
						os.remove(destinationPath)
					logger.info("Downloading file '%s'", item['name'])
					self._sourceDepot.download(sourcePath, destinationPath, progressSubject=progressSubject)

				md5s = md5sum(destinationPath)
				if md5s != self._fileInfo[relSource]['md5sum']:
					error = (
						f"Failed to download '{item['name']}': "
						f"MD5sum mismatch (local:{md5s} != remote:{self._fileInfo[relSource]['md5sum']})"
					)
					logger.error(error)
					raise RuntimeError(error)

	def synchronize(self, productProgressObserver=None, overallProgressObserver=None):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
		if not self._productIds:
			logger.info("Getting product dirs of depot '%s'", self._sourceDepot)
			for item in self._sourceDepot.content():
				self._productIds.append(item['name'])

		overallProgressSubject = ProgressSubject(id='sync_products_overall', type='product_sync', end=len(self._productIds), fireAlways=True)
		overallProgressSubject.setMessage(_('Synchronizing products'))
		if overallProgressObserver:
			overallProgressSubject.attachObserver(overallProgressObserver)

		for self._productId in self._productIds:
			productProgressSubject = ProgressSubject(id='sync_product_' + self._productId, type='product_sync', fireAlways=True)
			productProgressSubject.setMessage(_("Synchronizing product %s") % self._productId)
			if productProgressObserver:
				productProgressSubject.attachObserver(productProgressObserver)
			packageContentFile = None

			try:
				self._linkFiles = {}
				logger.notice(
					"Syncing product %s of depot %s with local directory %s",
					self._productId, self._sourceDepot, self._destinationDirectory
				)

				productDestinationDirectory = os.path.join(self._destinationDirectory, self._productId)
				if not os.path.isdir(productDestinationDirectory):
					os.mkdir(productDestinationDirectory)

				logger.info("Downloading package content file")
				packageContentFile = os.path.join(productDestinationDirectory, f"{self._productId}.files")
				self._sourceDepot.download(f"{self._productId}/{self._productId}.files", packageContentFile)
				self._fileInfo = PackageContentFile(packageContentFile).parse()

				size = 0
				for value in self._fileInfo.values():
					try:
						size += int(value['size'])
					except KeyError:
						pass

				productProgressSubject.setMessage(_("Synchronizing product %s (%.2f kByte)") % (self._productId, (size / 1024)))
				productProgressSubject.setEnd(size)
				productProgressSubject.setEndChangable(False)

				self._synchronizeDirectories(self._productId, productDestinationDirectory, productProgressSubject)

				links = list(self._linkFiles.keys())
				links.sort()
				for linkDestination in links:
					linkSource = self._linkFiles[linkDestination]

					with cd(productDestinationDirectory):
						if os.name == 'nt':
							if linkSource.startswith('/'):
								linkSource = linkSource[1:]
							if linkDestination.startswith('/'):
								linkDestination = linkDestination[1:]
							linkSource = os.path.join(productDestinationDirectory, linkSource.replace('/', '\\'))
							linkDestination = os.path.join(productDestinationDirectory, linkDestination.replace('/', '\\'))
							if os.path.exists(linkDestination):
								if os.path.isdir(linkDestination):
									shutil.rmtree(linkDestination)
								else:
									os.remove(linkDestination)
							logger.info("Symlink => copying '%s' to '%s'", linkSource, linkDestination)
							if os.path.isdir(linkSource):
								shutil.copytree(linkSource, linkDestination)
							else:
								shutil.copyfile(linkSource, linkDestination)
						else:
							if os.path.exists(linkDestination):
								if os.path.isdir(linkDestination) and not os.path.islink(linkDestination):
									shutil.rmtree(linkDestination)
								else:
									os.remove(linkDestination)
							parts = len(linkDestination.split('/'))
							parts -= len(linkSource.split('/'))
							for _counter in range(parts):
								linkSource = os.path.join('..', linkSource)
							logger.info("Symlink '%s' to '%s'", linkDestination, linkSource)
							os.symlink(linkSource, linkDestination)
			except Exception as error:
				productProgressSubject.setMessage(_("Failed to sync product %s: %s") % (self._productId, error))
				if packageContentFile and os.path.exists(packageContentFile):
					os.unlink(packageContentFile)
				raise

			overallProgressSubject.addToState(1)

			if productProgressObserver:
				productProgressSubject.detachObserver(productProgressObserver)

		if overallProgressObserver:
			overallProgressSubject.detachObserver(overallProgressObserver)
