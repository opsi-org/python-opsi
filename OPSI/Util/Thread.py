#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Thread    =
   = = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2010 uib GmbH
   
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
   
   @copyright:  uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>, Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

# imports
import threading, ctypes, time
from Queue import Queue, Empty

# OPSI imports
from OPSI.Logger import *

logger = Logger()

GlobalPool = None
def getGlobalThreadPool(*args, **kwargs):
	global GlobalPool
	if not GlobalPool:
		GlobalPool = ThreadPool(*args, **kwargs)
	else:
		size = kwargs.get('size', 0)
		GlobalPool.increaseUsageCount()
		if (GlobalPool.size < size):
			GlobalPool.adjustSize(size)
	return GlobalPool

def _async_raise(tid, excobj):
	res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(excobj))
	if (res == 0):
		logger.error(u"_async_raise: nonexistent thread id")
		raise ValueError(u"nonexistent thread id")
	elif (res > 1):
		# if it returns a number greater than one, you're in trouble,
		# and you should call it again with exc=NULL to revert the effect
		ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
		logger.error(u"_async_raise: PyThreadState_SetAsyncExc failed")
		raise SystemError(u"PyThreadState_SetAsyncExc failed")

class KillableThread(threading.Thread):
	def raise_exc(self, excobj):
		if not self.isAlive():
			logger.error(u"Cannot terminate, thread must be started")
			return
		for (tid, tobj) in threading._active.items():
			if tobj is self:
				_async_raise(tid, excobj)
				return

	# the thread was alive when we entered the loop, but was not found 
	# in the dict, hence it must have been already terminated. should we raise
	# an exception here? silently ignore?

	def terminate(self):
		# must raise the SystemExit type, instead of a SystemExit() instance
		# due to a bug in PyThreadState_SetAsyncExc
		self.raise_exc(SystemExit)

class ThreadPoolException(Exception):
	pass


class ThreadPool(object):
	
	def __init__(self, size = 20, autostart = True):
		self.size = int(size)
		self.started = False
		self.worker = []
		self.workerLock = threading.Lock()
		self.jobQueue = Queue()
		self.usageCount = 1
		if autostart:
			self.start()
	
	def increaseUsageCount(self):
		self.usageCount += 1
	
	def decreaseUsageCount(self):
		self.usageCount -= 1
		if (self.usageCount <= 0):
			self.stop()
	
	free = decreaseUsageCount
	
	def start(self):
		self.started = True
		self.adjustSize(self.size)
	
	def adjustSize(self, size):
		size = int(size)
		self.workerLock.acquire()
		try:
			if (size < 1):
				raise ThreadPoolException(u"Threadpool size %d is invalid" % size)
			
			self.size = size
			if self.started:
				if (len(self.worker) > self.size):
					self.__deleteWorkers(num = len(self.worker) - self.size)
				if (len(self.worker) < self.size):
					self.__createWorkers(num = self.size - len(self.worker))
		finally:
			self.workerLock.release()
		
	def __deleteWorker(self, wait=False):
		logger.debug(u"Deleting a worker")
		self.__deleteWorkers(1, wait = wait)
	
	def __deleteWorkers(self, num, wait=False):
		logger.debug(u"Deleting %d workers" % num)
		deleteWorkers = []
		for worker in self.worker:
			if not worker.busy and not worker in deleteWorkers:
				deleteWorkers.append(worker)
				worker.stop()
				num -= 1
				if (num == 0):
					break
		if (num > 0):
			for worker in self.worker:
				if not worker in deleteWorkers:
					deleteWorkers.append(worker)
					worker.stop()
					num -= 1
					if (num == 0):
						break
		
		worker = []
		for worker in self.worker:
			if not worker in deleteWorkers:
				worker.append(worker)
		self.worker = worker
		if wait:
			for worker in deleteWorkers:
				worker.join(60)
		
	def __createWorker(self):
		logger.debug(u"Creating new worker %s" % (len(self.worker)+1))
		self.__createWorkers(1)
	
	def __createWorkers(self, num):
		logger.debug(u"Creating %d new workers" % num)
		newWorkers = []
		while (num > 0):
			worker = Worker(self, len(self.worker)+1)
			self.worker.append(worker)
			newWorkers.append(worker)
			num -= 1
		
	def addJob(self, function, callback = None, *args, **kwargs):
		logger.debug(u"New job added: %s(%s, %s)"% (callback, args, kwargs))
		if not self.started:
			raise ThreadPoolException(u"Pool is not running.")
		self.jobQueue.put( (function, callback, args, kwargs) )
		
	def stop(self):
		logger.debug(u"Stopping ThreadPool")
		self.workerLock.acquire()
		self.started = False
		try:
			self.__deleteWorkers(num = len(self.worker), wait = True)
		finally:
			self.workerLock.release()
	
class Worker(threading.Thread):
	def __init__(self, threadPool, name=None):
		threading.Thread.__init__(self, name=name)
		self.threadPool = threadPool
		self.name = name
		self.busy = False
		self.stopped = False
		self.start()
	
	def run(self):
		while True:
			if self.stopped:
				break
			try:
				object = self.threadPool.jobQueue.get(block = True, timeout = 1)
				if object:
					self.busy = True
					(function, callback, args, kwargs) = object
					success = False
					try:
						result = function(*args, **kwargs) 
						success = True
						errors = None
					except Exception, e:
						logger.debug(e)
						result = None
						errors = e
					
					if callback:
						callback(success, result, errors)
					self.threadPool.jobQueue.task_done()
					self.busy = False
			except Empty:
				pass
	
	def stop(self):
		self.stopped = True



