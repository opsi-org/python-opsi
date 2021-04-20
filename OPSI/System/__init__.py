# -*- coding: utf-8 -*-

# Copyright (c) uib GmbH <info@uib.de>
# License: AGPL-3.0
"""
System library.

This library holds functionality to work with different operating
systems. For the every day use you should import the method / class you
want to use directly from this module.
Because most functions are implemented for Windows and POSIX systems you
should end up with runnable commands.
"""

from __future__ import absolute_import

import os
import platform
import shutil
import psutil

from OPSI.Logger import Logger
from OPSI.Types import forceFilename

logger = Logger()

if platform.system().lower() == 'linux':
	from .Linux import *
elif platform.system().lower() == 'windows':
	from .Windows import *
elif platform.system().lower() == 'darwin':
	from .Darwin import *
else:
	logger.error("Unable to import System library for system %s", platform.system().lower())

class SystemHook(SystemSpecificHook):
	def __init__(self):  # pylint: disable=super-init-not-called
		pass

	def pre_getDirectorySize(self, path):  # pylint: disable=no-self-use
		return path

	def post_getDirectorySize(self, path, result):  # pylint: disable=no-self-use,unused-argument
		return result

	def error_getDirectorySize(self, path, result, exception):  # pylint: disable=no-self-use
		pass

	def pre_getSize(self, path):  # pylint: disable=no-self-use
		return path

	def post_getSize(self, path, result):  # pylint: disable=no-self-use,unused-argument
		return result

	def error_getSize(self, path, result, exception):  # pylint: disable=no-self-use
		pass

	def pre_countFiles(self, path):  # pylint: disable=no-self-use
		return path

	def post_countFiles(self, path, result):  # pylint: disable=no-self-use,unused-argument
		return result

	def error_countFiles(self, path, result, exception):  # pylint: disable=no-self-use
		pass

	def pre_getCountAndSize(self, path):  # pylint: disable=no-self-use
		return path

	def post_getCountAndSize(self, path, result):  # pylint: disable=no-self-use,unused-argument
		return result

	def error_getCountAndSize(self, path, result, exception):  # pylint: disable=no-self-use
		pass

	def pre_copy(self, src, dst, progressSubject):  # pylint: disable=no-self-use
		return (src, dst, progressSubject)

	def post_copy(self, src, dst, progressSubject):  # pylint: disable=no-self-use,unused-argument
		return None

	def error_copy(self, src, dst, progressSubject, exception):  # pylint: disable=no-self-use,unused-argument
		pass


def getDirectorySize(path):
	path = os.path.abspath(forceFilename(path))
	for hook in hooks:
		path = hook.pre_getDirectorySize(path)

	size = 0
	try:
		for element in os.listdir(path):
			absolutePath = os.path.join(path, element)
			if os.path.islink(absolutePath):
				continue
			if os.path.isfile(absolutePath):
				size += os.path.getsize(absolutePath)
			elif os.path.isdir(absolutePath):
				size += getDirectorySize(absolutePath)
	except Exception as error:
		for hook in hooks:
			hook.error_getDirectorySize(path, size, error)
		raise

	for hook in hooks:
		size = hook.post_getDirectorySize(path, size)

	return size


def getSize(path):
	path = os.path.abspath(forceFilename(path))
	for hook in hooks:
		path = hook.pre_getSize(path)

	size = 0
	try:
		if os.path.islink(path):
			pass
		elif os.path.isfile(path):
			size = os.path.getsize(path)
		elif os.path.isdir(path):
			logger.debug(u"Getting size of files in dir '%s'", path)
			for element in os.listdir(path):
				size += getSize(os.path.join(path, element))
	except Exception as error:
		for hook in hooks:
			hook.error_getSize(path, size, error)
		raise

	for hook in hooks:
		size = hook.post_getSize(path, size)

	return size


def countFiles(path):
	path = os.path.abspath(forceFilename(path))
	for hook in hooks:
		path = hook.pre_countFiles(path)

	count = 0
	try:
		if os.path.islink(path):
			pass
		elif os.path.isfile(path):
			count = 1
		elif os.path.isdir(path):
			logger.debug(u"Counting files in dir '%s'", path)
			for element in os.listdir(path):
				count += countFiles(os.path.join(path, element))
	except Exception as error:
		for hook in hooks:
			hook.error_countFiles(path, count, error)
		raise

	for hook in hooks:
		count = hook.post_countFiles(path, count)

	return count


def getCountAndSize(path):
	path = os.path.abspath(forceFilename(path))

	for hook in hooks:
		path = hook.pre_getCountAndSize(path)

	(count, size) = (0, 0)
	try:
		if os.path.isfile(path):
			logger.debug2(u"Is file: %s", path)
			(count, size) = (1, os.path.getsize(path))
		elif os.path.isdir(path):
			logger.debug2(u"Is dir: %s", path)
			logger.debug(u"Counting and getting sizes of files in dir %s", path)
			for element in os.listdir(path):
				(elementCount, elementSize) = getCountAndSize(os.path.join(path, element))
				count += elementCount
				size += elementSize
	except Exception as error:
		for hook in hooks:
			hook.error_getCountAndSize(path, (count, size), error)
		raise

	for hook in hooks:
		(count, size) = hook.post_getCountAndSize(path, (count, size))

	return (count, size)


def mkdir(newDir, mode=0o750):
	"""
	Create a new directory.

	If newDir is a  already existing directory this will complete silently.
	If newDir is a file an exception will be risen.
	If parent directories do not exist they are created aswell.
	"""
	newDir = os.path.abspath(forceFilename(newDir))

	if os.path.isdir(newDir):
		pass
	elif os.path.isfile(newDir):
		raise OSError(u"A file with the same name as the desired dir, '%s', already exists." % newDir)
	else:
		(head, tail) = os.path.split(newDir)
		if head and not os.path.isdir(head):
			mkdir(head, mode=mode)
		if tail:
			os.mkdir(newDir)
			os.chmod(newDir, mode)


def copy(src, dst, progressSubject=None):
	'''
	Copy from `src` to `dst`.

	The copy process will follow these rules:

	* src = file, dst = file: overwrite dst
	* src = file, dst = dir: copy into dst
	* src = file, dst = not existent: create dst directories, copy src to dst
	* src = dir, dst = file: Exception
	* src = dir, dst = dir: copy src dir into dst
	* src = dir, dst = not existent: create dst, copy content of src into dst
	* src = dir/*, dst = dir/not existent: create dst if not exists, copy content of src into dst

	'''
	for hook in hooks:
		(src, dst, progressSubject) = hook.pre_copy(src, dst, progressSubject)

	try:
		src = forceFilename(src)
		dst = forceFilename(dst)

		copySrcContent = False

		if src.endswith(('/*.*', '\\*.*')):
			src = src[:-4]
			copySrcContent = True

		elif src.endswith(('/*', '\\*')):
			src = src[:-2]
			copySrcContent = True

		if copySrcContent and not os.path.isdir(src):
			raise IOError(u"Source directory '%s' not found" % src)

		logger.info(u"Copying from '%s' to '%s'", src, dst)
		(count, size) = (0, 0)
		if progressSubject:
			progressSubject.reset()
			(count, size) = getCountAndSize(src)
			progressSubject.setEnd(size)

		_copy(src, dst, copySrcContent, 0, count, size, progressSubject)
		logger.info(u'Copy done')
		if progressSubject:
			progressSubject.setState(size)
	except Exception as err:
		for hook in hooks:
			hook.error_copy(src, dst, progressSubject, err)
		raise

	for hook in hooks:
		hook.post_copy(src, dst, progressSubject)


def _copy(src, dst, copySrcContent=False, fileCount=0, totalFiles=0, totalSize=0, progressSubject=None):  # pylint: disable=too-many-arguments,too-many-branches
	src = forceFilename(src)
	dst = forceFilename(dst)

	if os.path.isfile(src):
		fileCount += 1
		size = 0
		if not os.path.exists(dst):
			parent = os.path.dirname(dst)
			if not os.path.isdir(parent):
				os.makedirs(parent)

		if progressSubject:
			countLen = len(str(totalFiles))
			countLenFormat = '%' + str(countLen) + 's'
			size = os.path.getsize(src)

			if size > 1024 * 1024:
				sizeString = "%0.2f MByte" % (float(size) / (1024 * 1024))
			elif size > 1024:
				sizeString = "%0.2f kByte" % (float(size) / 1024)
			else:
				sizeString = "%d Byte" % size

			progressSubject.setMessage(
				u"[%s/%s] %s (%s)" % (
					countLenFormat % fileCount, totalFiles,
					os.path.basename(src), sizeString
				)
			)

		try:
			shutil.copy2(src, dst)
		except OSError as error:
			logger.debug(error)
			# Operation not permitted
			if error.errno != 1:
				raise

		if progressSubject:
			progressSubject.addToState(size)

	elif os.path.isdir(src):
		if not os.path.isdir(dst):
			os.makedirs(dst)
		elif not copySrcContent:
			dst = os.path.join(dst, os.path.basename(src))

		for element in os.listdir(src):
			fileCount = _copy(
				os.path.join(src, element),
				os.path.join(dst, element),
				True,
				fileCount,
				totalFiles,
				totalSize,
				progressSubject
			)

	return fileCount
