#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = =
   =   opsi python library - Tools   =
   = = = = = = = = = = = = = = = = = =
   
   This module is part of the desktop management solution opsi
   (open pc server integration) http://www.opsi.org
   
   Copyright (C) 2006, 2007, 2008 uib GmbH
   
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

__version__ = '3.5'

# Imports
import json, os

# OPSI imports
from OPSI.Logger import *

# Get logger instance
logger = Logger()

RANDOM_DEVICE = '/dev/urandom'

def generateOpsiHostKey():
	key = ''
	if (os.name == 'posix'):
		logger.debug(u"Opening random device '%s' to generate opsi host key" % RANDOM_DEVICE)
		r = open (RANDOM_DEVICE)
		key = r.read(16)
		r.close()
		logger.debug("Random device closed")
		key = key.encode("hex")
	else:
		logger.debug(u"Using python random module to generate opsi host key")
		while (len(key) < 32):
			key += random.choice(['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'])
	return key

def timestamp(secs=0, dateOnly=False):
	''' Returns a timestamp of the current system time format: YYYY-mm-dd[ HH:MM:SS] '''
	if not secs:
		secs = time.time()
	if dateOnly:
		return time.strftime( u"%Y-%m-%d", time.localtime(secs) )
	else:
		return time.strftime( u"%Y-%m-%d %H:%M:%S", time.localtime(secs) )

def objectToBeautifiedText(obj, level=0):
	hspace = level*10
	text = u''
	if ( type(obj) == type([]) ):
		text += u' '*hspace + u'[ \n'
		for i in range( len(obj) ):
			if type(obj[i]) != type({}) and type(obj[i]) != type([]):
				text += u' '*hspace
			text += objectToBeautifiedText(obj[i], level+1)
			
			if (i < len(obj)-1):
				text += u',\n'
		text += u'\n' + u' '*hspace + u']'
	elif ( type(obj) == type({}) ):
		text += u' '*hspace + u'{ \n'
		i = 0
		for (key, value) in obj.items():
			text += u' '*hspace + u'"' + key + u'" : '
			if type(value) == type({}) or type(value) == type([]):
				text += u'\n'
			text += objectToBeautifiedText(obj[key], level+1)
			
			if (i < len(obj)-1):
				text += u',\n'
			i+=1
		text += u'\n' + u' '*hspace + u'}'
	else:
		text += json.dumps(obj)
		#if hasattr(json, 'dumps'):
		#	# python 2.6 json module
		#	text+= json.dumps(obj)
		#else:
		#	text+= json.write(obj)
	return text

