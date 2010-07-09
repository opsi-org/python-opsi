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

import threading, Queue
from OPSI.Logger import *

logger = Logger()

class ThreadPoolException(Exception):
	pass

class ThreadPool(object):
	
	def __init__(self, min = 5, max = 20, autostart = True):
		self.min = min
		self.max = max
		self.started = False
		self.worker = []
		self.queue = Queue.Queue()
		
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
			while len(self.worker) > max:
				self.stopWorker()
		
			while len(self.worker) < min:
				self.startWorker()
			
	def addJob(self, function, callback = None, *args, **kwargs):
		self.queue.put((function, callback, args, kwargs))
		while len(self.worker) < min(self.queue.qsize(), self.max):
			self.startWorker()
			
	def startWorker(self):
		worker = Worker(self.queue)
		self.worker.append(worker)
		
	def stopWorker(self):
		worker = self.worker.pop()
		worker.stop()
	
	def stop(self):
		for worker in range(len(self.worker)):
			self.stopWorker()
		self.started = False
		
class Worker(threading.Thread):
	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.stoped = False
		self.queue = queue
		self.daemon = True
		self.start()
		
	def run(self):

		while not self.stoped:
			function, callback, args, kwargs = self.queue.get()
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

	def stop(self):
		self.stoped = True
		