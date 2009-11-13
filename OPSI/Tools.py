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
import json, os, random

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get logger instance
logger = Logger()

RANDOM_DEVICE = '/dev/urandom'

def randomString(length):
	string = u''
	for i in range(length):
		string = string + random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
	return unicode(string)

def generateOpsiHostKey():
	key = u''
	if (os.name == 'posix'):
		logger.debug(u"Opening random device '%s' to generate opsi host key" % RANDOM_DEVICE)
		r = open(RANDOM_DEVICE)
		key = r.read(16)
		r.close()
		logger.debug("Random device closed")
		key = unicode(key.encode("hex"))
	else:
		logger.debug(u"Using python random module to generate opsi host key")
		while (len(key) < 32):
			key += random.choice([u'0',u'1',u'2',u'3',u'4',u'5',u'6',u'7',u'8',u'9',u'a',u'b',u'c',u'd',u'e',u'f'])
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
		if hasattr(json, 'dumps'):
			# python 2.6 json module
			text+= json.dumps(obj)
		else:
			text+= json.write(obj)
	return text

def jsonObjToHtml(jsonObj, level=0):
	hspace = level*10
	html = ''
	if hasattr(jsonObj, 'toHash'):
		jsonObj = jsonObj.toHash()
	
	if ( type(jsonObj) == type([]) ):
		html += ' '*hspace + '[ <br />'
		for i in range( len(jsonObj) ):
			if type(jsonObj[i]) != type({}) and type(jsonObj[i]) != type([]):
				html += ' '*hspace
			html += jsonObjToHtml(jsonObj[i], level+1)
			
			if (i < len(jsonObj)-1):
				html += ',<br />'
		html += '<br />' + ' '*hspace + ']'
	elif ( type(jsonObj) == type({}) ):
		html += ' '*hspace + '{ <br />'
		i = 0
		for (key, value) in jsonObj.items():
			html += ' '*hspace + '"<font class="json_key">' + key +  '</font>": '
			if type(value) == type({}) or type(value) == type([]):
				html += '<br />'
			html += jsonObjToHtml(jsonObj[key], level+1)
			
			if (i < len(jsonObj)-1):
				html += ',<br />'
			i+=1
		html += '<br />' + ' '*hspace + '}'
	else:
		if hasattr(json, 'dumps'):
			# python 2.6 json module
			html += json.dumps(jsonObj).replace('<', '&lt;').replace('>', '&gt;')
		else:
			html += json.write(jsonObj).replace('<', '&lt;').replace('>', '&gt;')
	return html.replace('\\n', '<br />' + ' '*hspace)

