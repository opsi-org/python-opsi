#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - JsonRpc     =
   = = = = = = = = = = = = = = = = = = = =
   
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
   @author: Jan Schneider <j.schneider@uib.de>
   @license: GNU General Public License version 2
"""

import time

from OPSI.Logger import *
from OPSI.Types import OpsiRpcError
from OPSI.Object import serialize, deserialize

logger = Logger()

class JsonRpc(object):
	def __init__(self, instance, interface, rpc):
		self._instance = instance
		self._interface = interface
		self.started   = None
		self.ended     = None
		self.type      = rpc.get('type')
		self.tid       = rpc.get('tid', rpc.get('id'))
		self.action    = rpc.get('action')
		self.method    = rpc.get('method')
		self.params    = rpc.get('params', rpc.get('data'))
		if not self.params:
			self.params = []
		self.result    = None
		self.exception = None
		self.traceback = None
		if not self.tid:
			raise Exception(u"No transaction id ((t)id) found in rpc")
		if not self.method:
			raise Exception(u"No method found in rpc")
	
	def isStarted(self):
		return bool(self.started)
	
	def hasEnded(self):
		return bool(self.ended)
	
	def getMethodName(self):
		if self.action:
			return u'%s_%s' % (self.action, self.method)
		return self.method
	
	def getDuration(self):
		if not self.started or not self.ended:
			return None
		return round(self.ended - self.started, 3)
		
	def execute(self, result=None):
		# Execute rpc
		self.result = None
		params = []
		for param in self.params:
			params.append(param)
		try:
			self.started = time.time()
			
			methodInterface = None
			for m in self._interface:
				if (self.getMethodName() == m['name']):
					methodInterface = m
					break
			if not methodInterface:
				raise OpsiRpcError(u"Method '%s' is not valid" % self.getMethodName())
			
			keywords = {}
			if methodInterface['keywords']:
				l = 0
				if methodInterface['args']:
					l += len(methodInterface['args'])
				if methodInterface['varargs']:
					l += len(methodInterface['varargs'])
				if (len(params) >= l):
					if not type(params[-1]) is types.DictType:
						raise Exception(u"kwargs param is not a dict: %s" % params[-1])
					for (key, value) in params.pop(-1).items():
						keywords[str(key)] = deserialize(value)
			
			params = deserialize(params)
			
			pString = forceUnicode(params)[1:-1]
			if keywords:
				pString += u', ' + forceUnicode(keywords)
			if (len(pString) > 200):
				pString = pString[:200] + u'...'
			
			logger.notice(u"-----> Executing: %s(%s)" % (self.getMethodName(), pString))
			
			instance = self._instance
			if keywords:
				self.result = eval( "instance.%s(*params, **keywords)" % self.getMethodName() )
			else:
				self.result = eval( "instance.%s(*params)" % self.getMethodName() )
			
			logger.info(u'Got result')
			logger.debug2(self.result)
		
		except Exception, e:
			logger.logException(e, LOG_INFO)
			logger.error(u'Execution error: %s' % forceUnicode(e))
			self.exception = e
			self.traceback = []
			tb = sys.exc_info()[2]
			while (tb != None):
				f = tb.tb_frame
				c = f.f_code
				self.traceback.append(u"     line %s in '%s' in file '%s'" % (tb.tb_lineno, c.co_name, c.co_filename))
				tb = tb.tb_next
		self.ended = time.time()
		
	def getResponse(self):
		response = {}
		if (self.type == 'rpc'):
			response['tid']    = self.tid
			response['action'] = self.action
			response['method'] = self.method
			if self.exception:
				response['type']    = 'exception'
				response['message'] = { 'class': self.exception.__class__.__name__, 'message': forceUnicode(self.exception) }
				response['where']   = self.traceback
			else:
				response['type']   = 'rpc'
				response['result'] = self.result
		else:
			response['id'] = self.tid
			if self.exception:
				response['error']  = { 'class': self.exception.__class__.__name__, 'message': forceUnicode(self.exception) }
				response['result'] = None
			else:
				response['error']  = None
				response['result'] = self.result
		return response




