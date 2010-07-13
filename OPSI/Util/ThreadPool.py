#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Repository    =
   = = = = = = = = = = = = = = = = = = = = =
   
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
   
   @copyright:	uib GmbH <info@uib.de>
   @author: Christian Kampka <c.kampka@uib.de>
   @license: GNU General Public License version 2
"""

__version__ = '4.0'

import threading, Queue, copy
from Queue import Queue, Empty
from OPSI.Logger import *
from time import sleep
logger = Logger()
class StopJob(object):
	pass

class ThreadPoolException(Exception):
	pass

class ThreadPool(object):
	
	def __init__(self, min = 5, max = 20, autostart = True):
		self.min = min
		self.max = max
		self.started = False
		self.worker = []
		self.queue = Queue()
		
		if autostart:
			self.start()
	
	def start(self):
		self.started = True
		self.adjustSize()

	def adjustSize(self, min=None, max=None):
		if not min:
			min = self.min
		if not max:
			max = self.max
		
		if not min >= 0 or not min < max:
			raise ThreadPoolException("Threadpool size is invalid: min=%s, max=%s"%(min,max))
		
		self.min = min
		self.max = max
		
			
		if self.started:
			while len(self.worker) > self.max:
				self.stopWorker()
		
			while len(self.worker) < self.min:
				self.startWorker()
		
			
	def addJob(self, function, callback = None, *args, **kwargs):
		if not self.started:
			raise ThreadPoolException("Pool is not running.")
		self.queue.put((function, callback, args, kwargs))
		while len(self.worker) < min(self.queue.qsize(), self.max):
			self.startWorker()
			
	def startWorker(self):
		logger.debug("Starting new worker %s" % (len(self.worker)+1))
		
		worker = Worker(self.queue, len(self.worker)+1)
		self.worker.append(worker)
		
	def stopWorker(self):
		worker = self.worker.pop()
		worker.stop()
		
	def stop(self):
		logger.debug("Stopping threadpool")
		self.started = False
		
		workers = copy.copy(self.worker)
		
		while(len(self.worker)):
			self.queue.put(StopJob())
			self.worker.pop()
		
		for worker in workers:
			worker.join()
			
			
	def __del__(self):
		if self.started:
			self.stop()
		
class Worker(threading.Thread):
	def __init__(self, queue, name=None):
		threading.Thread.__init__(self, name=name)
		self.running = True
		self.queue = queue
		self.daemon = True
		self.start()
		
	def run(self):

		while self.running:
			
			try:
				if not self.queue.empty():
					object = self.queue.get(block=False)
				
					if object:
						if isinstance(object, StopJob):
							self.stop()
						else:
							function, callback, args, kwargs = object
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
						self.queue.task_done()
			except Empty:
				sleep(0.00001)

	def stop(self):
		logger.debug("Stopping worker %s" % self.name)
		self.running = False
		


Pool = ThreadPool()

## Decorator to launch a function as a thread job
def poolJob(callback=None):
	def runPoolJob(function):
		def _run(*args, **kwargs):
			Pool.addJob(function, callback, *args, **kwargs)
		return _run
	return runPoolJob
