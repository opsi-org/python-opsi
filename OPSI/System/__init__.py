#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
opsi python library - System

This module is part of the desktop management solution opsi
(open pc server integration) http://www.opsi.org

Copyright (C) 2006 - 2013 uib GmbH

http://www.uib.de/

All rights reserved.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

@copyright:	uib GmbH <info@uib.de>
@author: Jan Schneider <j.schneider@uib.de>
@license: GNU General Public License version 2
"""

__version__ = '4.0'

import os
import shutil

if (os.name == 'posix'):
	from Posix import *
if (os.name == 'nt'):
	from Windows import *

from OPSI.Types import *


class SystemHook(SystemSpecificHook):
	def __init__(self):
		pass

	def pre_getDirectorySize(self, path):
		return path

	def post_getDirectorySize(self, path, result):
		return result

	def error_getDirectorySize(self, path, result, exception):
		pass

	def pre_getSize(self, path):
		return path

	def post_getSize(self, path, result):
		return result

	def error_getSize(self, path, result, exception):
		pass

	def pre_countFiles(self, path):
		return path

	def post_countFiles(self, path, result):
		return result

	def error_countFiles(self, path, result, exception):
		pass

	def pre_getCountAndSize(self, path):
		return path

	def post_getCountAndSize(self, path, result):
		return result

	def error_getCountAndSize(self, path, result, exception):
		pass

	def pre_copy(self, src, dst, progressSubject):
		return (src, dst, progressSubject)

	def post_copy(self, src, dst, progressSubject):
		return None

	def error_copy(self, src, dst, progressSubject, exception):
		pass


def getDirectorySize(path):
	path = os.path.abspath(forceFilename(path))
	for hook in hooks:
		path = hook.pre_getDirectorySize(path)

	size = 0
	try:
		for r in os.listdir(path):
			a = os.path.join(path, r)
			if os.path.islink(a):
				continue
			if os.path.isfile(a):
				size += os.path.getsize(a)
			if os.path.isdir(a):
				size += getDirectorySize(a)
	except Exception as e:
		for hook in hooks:
			hook.error_getDirectorySize(path, size, e)
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
			logger.debug(u"Getting size of files in dir '%s'" % path)
			for r in os.listdir(path):
				size += getSize(os.path.join(path, r))
	except Exception as e:
		for hook in hooks:
			hook.error_getSize(path, size, e)
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
			logger.debug(u"Counting files in dir '%s'" % path)
			for r in os.listdir(path):
				count += countFiles(os.path.join(path, r))
	except Exception as e:
		for hook in hooks:
			hook.error_countFiles(path, count, e)
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
			logger.debug2(u"Is file: %s" % path)
			(count, size) = (1, os.path.getsize(path))
		elif os.path.isdir(path):
			logger.debug2(u"Is dir: %s" % path)
			logger.debug(u"Counting and getting sizes of files in dir '%s'" % path)
			for r in os.listdir(path):
				(c, s) = getCountAndSize(os.path.join(path, r))
				count += c
				size += s
	except Exception, e:
		for hook in hooks:
			hook.error_getCountAndSize(path, (count, size), e)
		raise

	for hook in hooks:
		(count, size) = hook.post_getCountAndSize(path, (count, size))

	return (count, size)


def mkdir(newDir, mode=0750):
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
	Copy from source to destination.

	The copy process will follow these rules:
	src = file,  dst = file              => overwrite dst
	src = file,  dst = dir               => copy into dst
	src = file,  dst = not existent      => create dst directories, copy src to dst
	src = dir,   dst = file              => error
	src = dir,   dst = dir               => copy src dir into dst
	src = dir,   dst = not existent      => create dst, copy content of src into dst
	src = dir/*, dst = dir/not existent  => create dst if not exists, copy content of src into dst
	'''
	for hook in hooks:
		(src, dst, progressSubject) = hook.pre_copy(src, dst, progressSubject)

	try:
		src = forceFilename(src)
		dst = forceFilename(dst)

		copySrcContent = False

		if src.endswith('/*.*') or src.endswith('\\*.*'):
			src = src[:-4]
			copySrcContent = True

		elif src.endswith('/*') or src.endswith('\\*'):
			src = src[:-2]
			copySrcContent = True

		if copySrcContent and not os.path.isdir(src):
			raise Exception(u"Source directory '%s' not found" % src)

		logger.info(u"Copying from '%s' to '%s'" % (src, dst))
		(count, size) = (0, 0)
		if progressSubject:
			progressSubject.reset()
			(count, size) = getCountAndSize(src)
			progressSubject.setEnd(size)

		_copy(src, dst, copySrcContent, 0, count, size, progressSubject)
		logger.info(u'Copy done')
		if progressSubject:
			progressSubject.setState(size)
	except Exception, e:
		for hook in hooks:
			hook.error_copy(src, dst, progressSubject, e)
		raise

	for hook in hooks:
		hook.post_copy(src, dst, progressSubject)


def _copy(src, dst, copySrcContent=False, fileCount=0, totalFiles=0, totalSize=0, progressSubject=None):
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
			sizeString = "%d Byte" % size
			if (size > 1024*1024):
				sizeString = "%0.2f MByte" % ( float(size)/(1024*1024) )
			elif (size > 1024):
				sizeString = "%0.2f kByte" % ( float(size)/(1024) )
			progressSubject.setMessage(u"[%s/%s] %s (%s)" \
					% (countLenFormat % fileCount, totalFiles, os.path.basename(src), sizeString ) )

		try:
			shutil.copy2(src, dst)
		except OSError as e:
			if (e.errno != 1):
				raise
			# Operation not permitted
			logger.debug(e)

		if progressSubject:
			progressSubject.addToState(size)

	elif os.path.isdir(src):
		if not os.path.isdir(dst):
			os.makedirs(dst)
		elif not copySrcContent:
			dst = os.path.join(dst, os.path.basename(src))
		for r in os.listdir(src):
			fileCount = _copy(os.path.join(src, r), os.path.join(dst,r), True, fileCount, totalFiles, totalSize, progressSubject)

	return fileCount
