#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - System    =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006 - 2010 uib GmbH
   
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

import os, shutil

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
		raise exception
	
	
	def pre_getSize(self, path):
		return path
	
	def post_getSize(self, path, result):
		return result
	
	def error_getSize(self, path, result, exception):
		raise exception
	
	
	def pre_countFiles(self, path):
		return path
	
	def post_countFiles(self, path, result):
		return result
	
	def error_countFiles(self, path, result, exception):
		raise exception
	
	
	def pre_getCountAndSize(self, path):
		return path
	
	def post_getCountAndSize(self, path, result):
		return result
	
	def error_getCountAndSize(self, path, result, exception):
		raise exception
	
	
	def pre_copy(self, src, dst, progressSubject):
		return (src, dst, progressSubject)
	
	def post_copy(self, src, dst, progressSubject):
		return None
	
	def error_copy(self, src, dst, progressSubject, exception):
		raise exception

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
	except Exception, e:
		for hook in hooks:
			hook.error_getDirectorySize(path, size, e)
		
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
	except Exception, e:
		for hook in hooks:
			hook.error_getSize(path, size, e)
	
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
	except Exception, e:
		for hook in hooks:
			hook.error_countFiles(path, count, e)
	
	for hook in hooks:
		count = hook.post_countFiles(path, count)
	
	return count

def getCountAndSize(path):
	path = os.path.abspath(forceFilename(path))
	
	for hook in hooks:
		path = hook.pre_getCountAndSize(path)
	
	(count, size) = (0, 0)
	try:
		#if os.path.islink(path):
		#	logger.debug(u"Is link: %s" % path)
		#	pass
		#el
		if os.path.isfile(path):
			logger.debug(u"Is file: %s" % path)
			(count, size) = (1, os.path.getsize(path))
		elif os.path.isdir(path):
			logger.debug(u"Is dir: %s" % path)
			logger.debug(u"Counting and getting sizes of files in dir '%s'" % path)
			for r in os.listdir(path):
				(c, s) = getCountAndSize(os.path.join(path, r))
				count += c
				size += s
	except Exception, e:
		for hook in hooks:
			hook.error_getCountAndSize(path, (count, size), e)
	
	for hook in hooks:
		(count, size) = hook.post_getCountAndSize(path, (count, size))
	
	return (count, size)

def mkdir(newDir):
	"""
	- already exists, silently complete
	- regular file in the way, raise an exception
	- parent directory(ies) does not exist, make them as well
	"""
	newDir = os.path.abspath(forceFilename(newDir))
	
	if os.path.isdir(newDir):
		pass
	elif os.path.isfile(newDir):
		raise OSError(u"A file with the same name as the desired dir, '%s', already exists." % newDir)
	else:
		(head, tail) = os.path.split(newDir)
		if head and not os.path.isdir(head):
			mkdir(head)
		if tail:
			os.mkdir(newDir)
	
def copy(src, dst, progressSubject=None):
	for hook in hooks:
		(src, dst, progressSubject) = hook.pre_copy(src, dst, progressSubject)
	
	'''
	src = file,  dst = file              => overwrite dst
	src = file,  dst = dir               => copy into dst
	src = file,  dst = not existent      => create dst directories, copy src to dst
	src = dir,   dst = file              => error
	src = dir,   dst = dir               => copy src dir into dst
	src = dir,   dst = not existent      => create dst, copy content of src into dst
	src = dir/*, dst = dir/not existent  => create dst if not exists, copy content of src into dst
	'''
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
		#progressSubject.setMessage(u'Preparing copy')
		#progressSubject.setMessage(u'Copying from %s to %s' % (src, dst))
		progressSubject.reset()
		(count, size) = getCountAndSize(src)
		progressSubject.setEnd(size)
	
	try:
		_copy(src, dst, copySrcContent, 0, count, size, progressSubject)
		logger.info(u'Copy done')
		if progressSubject:
			progressSubject.setState(size)
	except Exception, e:
		for hook in hooks:
			hook.error_copy(src, dst, progressSubject, e)
	
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
		except os.error, e:
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
	



if (__name__ == "__main__"):
	#logger.setConsoleLevel(LOG_DEBUG)
	from OPSI.Util.Message import ProgressSubject, ProgressObserver
	from OPSI.UI import UIFactory
	ui = UIFactory()
	
	progressSubject = ProgressSubject(id = u'copy_test', title = u'Copy test')
	
	class SimpleProgressObserver(ProgressObserver):
		def messageChanged(self, subject, message):
			print u"%s" % message
		
		def progressChanged(self, subject, state, percent, timeSpend, timeLeft, speed):
			print u"state: %s, percent: %0.2f%%, timeSpend: %0.2fs, timeLeft: %0.2fs, speed: %0.2f" \
				% (state, percent, timeSpend, timeLeft, speed)
	
	class TestHook(SystemHook):
		def __init__(self):
			self._copyBox = None
		
		def pre_copy(self, src, dst, progressSubject):
			#progressSubject.attachObserver(SimpleProgressObserver())
			self._copyBox = ui.createCopyProgressBox(width = 120, height = 20, title = u'Copy from %s to %s' % (src, dst), text = u'')
			self._copyBox.show()
			progressSubject.attachObserver(self._copyBox)
			return (src, dst, progressSubject)
		
		def post_copy(self, src, dst, progressSubject):
			time.sleep(1)
			self._copyBox.hide()
			return None
		
	hook = TestHook()
	addHook(hook)
	#progressSubject.attachObserver(SimpleProgressObserver())
	#progressBox = ui.createProgressBox(width = 120, height = 20, title = u'Progress', text = u'')
	#progressSubject.attachObserver(progressBox)
	
	testDir = '/tmp/opsi_system_copy_test'
	if os.path.exists(testDir):
		shutil.rmtree(testDir)
	os.makedirs(testDir)
	
	srcDir = os.path.join(testDir, 'src')
	dstDir = os.path.join(testDir, 'dst')
	os.makedirs(srcDir)
	os.makedirs(dstDir)
	
	# src = file,  dst = file           => overwrite dst
	srcfile = os.path.join(srcDir, 'testfile')
	f = open(srcfile, 'w')
	f.write('new')
	f.close()
	dstfile = os.path.join(dstDir, 'testfile')
	f = open(dstfile, 'w')
	f.write('old')
	f.close()
	copy(srcfile, dstfile, progressSubject)
	
	f = open(dstfile)
	data = f.read()
	f.close()
	
	assert data == 'new'
	
	# src = file,  dst = dir            => copy into dst
	dstfile = os.path.join(dstDir, 'testfile2')
	copy(srcfile, dstfile, progressSubject)
	f = open(dstfile)
	data = f.read()
	f.close()
	
	assert data == 'new'
	
	# src = file,  dst = not existent   => create dst directories, copy src to dst
	dstfile = os.path.join(dstDir, 'newdir', 'testfile')
	copy(srcfile, dstfile, progressSubject)
	f = open(dstfile)
	data = f.read()
	f.close()
	
	assert data == 'new'
	
	shutil.rmtree(srcDir)
	shutil.rmtree(dstDir)
	os.makedirs(srcDir)
	os.makedirs(dstDir)
	
	# src = dir,   dst = file           => error
	testSrcDir = os.path.join(srcDir, 'testdir')
	os.makedirs(testSrcDir)
	
	testDstDir = os.path.join(dstDir, 'testdir')
	f = open(testDstDir, 'w')
	f.close()
	
	try:
		copy(testSrcDir, testDstDir, progressSubject)
	except OSError:
		pass
	else:
		raise Exception("Dst file %s exists" % testDstDir)
	
	#src = dir,   dst = dir            => copy src dir into dst
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testSrcDir, filename)
		f = open(a, 'w')
		f.write('x'*10*1024*1024)
		f.close()
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testSrcDir, dirname)
		os.mkdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			f = open(a2, 'w')
			f.write('x'*20*1024*1024)
			f.close()
	
	os.remove(testDstDir)
	os.mkdir(testDstDir)
	copy(testSrcDir, testDstDir, progressSubject)
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, os.path.basename(testSrcDir), filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, os.path.basename(testSrcDir), dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	copy(testSrcDir, testDstDir, progressSubject)
	
	for name in os.listdir(os.path.join(testDstDir, os.path.basename(testSrcDir))):
		assert name in ('file1', 'file2', 'file3', 'dir1', 'dir2', 'dir3')
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, os.path.basename(testSrcDir), dirname)
		for name in os.listdir(a):
			assert name in ('file1', 'file2', 'file3')
	
	
	# src = dir,   dst = not existent   => create dst, copy content of src into dst
	shutil.rmtree(dstDir)
	os.makedirs(dstDir)
	
	copy(testSrcDir, testDstDir, progressSubject)
	
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	# src = dir/*, dst = not file       => create dst if not exists, copy content of src into dst
	shutil.rmtree(dstDir)
	os.makedirs(dstDir)
	
	copy(testSrcDir + '/*.*', testDstDir, progressSubject)
	
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	shutil.rmtree(dstDir)
	os.makedirs(dstDir)
	
	copy(testSrcDir + '/*', testDstDir, progressSubject)
	
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	shutil.rmtree(dstDir)
	os.makedirs(testDstDir)
	
	copy(testSrcDir + '/*.*', testDstDir, progressSubject)
	
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	shutil.rmtree(dstDir)
	os.makedirs(testDstDir)
	
	copy(testSrcDir + '/*', testDstDir, progressSubject)
	
	for filename in ('file1', 'file2', 'file3'):
		a = os.path.join(testDstDir, filename)
		assert os.path.isfile(a)
	for dirname in ('dir1', 'dir2', 'dir3'):
		a = os.path.join(testDstDir, dirname)
		assert os.path.isdir(a)
		for filename in ('file1', 'file2', 'file3'):
			a2 = os.path.join(a, filename)
			assert os.path.isfile(a2)
	
	
	if ui: ui.exit()
	
	
	
	
	
	
	
	
	
	
	
	
	
	




