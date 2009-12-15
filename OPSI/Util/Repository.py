#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
   = = = = = = = = = = = = = = = = = = = = =
   =   opsi python library - Repository    =
   = = = = = = = = = = = = = = = = = = = = =
   
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
import re, stat, base64, urllib, os, shutil
try:
	from hashlib import md5
except ImportError:
	from md5 import md5
from OPSI.web2 import responsecode
from OPSI.web2.dav import davxml

# OPSI imports
from OPSI.Logger import *
from OPSI.Types import *

# Get Logger instance
logger = Logger()

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# =       Repositories                                                                =
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def getRepository(url, username=u'', password=u'', maxBandwidth=0):
	url          = forceUnicode(url)
	username     = forceUnicode(username)
	password     = forceUnicode(password)
	maxBandwidth = forceInt(maxBandwidth)
	if re.search('^file://', url):
		return FileRepository(url, username, password, maxBandwidth)
	if re.search('^webdavs*://', url):
		return WebDAVRepository(url, username, password, maxBandwidth)
	raise RepositoryError(u"Repository url '%s' not supported" % url)
	
class Repository:
	def __init__(self, url, username=u'', password=u'', maxBandwidth=0):
		''' maxBandwidth in bit/s'''
		self._url          = forceUnicode(url)
		self._username     = forceUnicode(username)
		self._password     = forceUnicode(password)
		self._path         = u''
		self._maxBandwidth = forceInt(maxBandwidth)
		if self._maxBandwidth:
			self._maxBandwidth = self._maxBandwidth/8
			if (self._maxBandwidth < 1):
				self._maxBandwidth = 1
	
	def __unicode__(self):
		return u'<%s %s>' % (self.__class__.__name__, self._url)
	
	def __str__(self):
		return unicode(self).encode("utf-8")
	
	__repr__ = __unicode__
	
	def _transfer(self, src, dst, progressSubject=None):
		buf = True
		waitTime = 0.0
		bufferSize = 64*1024
		if self._maxBandwidth:
			if (self._maxBandwidth < bufferSize*2):
				bufferSize = int(self._maxBandwidth/2)
			if (bufferSize < 512):
				bufferSize = 512
		
		while(buf):
			t1 = time.time()
			buf = src.read(bufferSize)
			read = len(buf)
			if (read > 0):
				if isinstance(dst, HTTPConnection) or isinstance(dst, HTTPSConnection):
					dst.send(buf)
				else:
					dst.write(buf)
				time.sleep(waitTime)
				t2 = time.time()
				dt = t2-t1
				if self._maxBandwidth and (self._maxBandwidth > 0) and (dt > 0):
					speed = int(read/dt)
					wt = 0
					if (speed > 0) and (speed > self._maxBandwidth):
						wt = ( (float(speed)/float(self._maxBandwidth)) ** (0.1) )
					elif (speed > 0) and (speed < self._maxBandwidth):
						wt = ( (float(self._maxBandwidth)/float(speed)) ** (0.1) )
					if wt:
						while (wt > 1):
							wt -= 1
						if (wt > 0.2):
							wt = 0.2
						if (speed > self._maxBandwidth):
							waitTime += wt
						else:
							waitTime -= wt
						if (waitTime < 0):
							waitTime = 0.00001
				if progressSubject:
					progressSubject.addToState(read)
	
	def setMaxBandwidth(self, maxBandwidth):
		''' maxBandwidth in bit/s'''
		self._maxBandwidth = forceInt(maxBandwidth)
		if self._maxBandwidth:
			self._maxBandwidth = int(self._maxBandwidth/8)
			if (self._maxBandwidth < 1):
				self._maxBandwidth = 1
	
	def content(self, destination=u''):
		raise RepositoryError(u"Not implemented")
	
	def fileInfo(self, destination):
		raise RepositoryError(u"Not implemented")
	
	def upload(self, source, destination):
		raise RepositoryError(u"Not implemented")
	
	def download(self, source, destination, progressObserver=None):
		raise RepositoryError(u"Not implemented")
	
	def delete(self, destination):
		raise RepositoryError(u"Not implemented")
	
	def makeDirectory(self, destination):
		raise RepositoryError(u"Not implemented")
	
class FileRepository(Repository):
	def __init__(self, url, username=u'', password=u'', maxBandwidth=0):
		Repository.__init__(self, url, username, password, maxBandwidth)
		
		match = re.search('^file://(/[^/]+.*)$', self._url)
		if not match:
			raise RepositoryError(u"Bad url: '%s'" % self._url)
		self._path = match.group(1)
		
	def _absolutePath(self, destination):
		destination = forceUnicode(destination)
		if destination.startswith('/'):
			destination = destination[1:]
		return self._path + u'/' + destination
	
	def content(self, destination=''):
		content = []
		destination = self._absolutePath(destination)
		try:
			for e in os.listdir(destination):
				fs = os.stat(os.path.join(destination, e))
				type = 'file'
				if os.path.isdir(os.path.join(destination, e)):
					type = 'dir'
				content.append({
					'name': e,
					'size': fs[stat.ST_SIZE],
					'type': type })
		except:
			raise RepositoryError(u"Not a directory: '%s'" % destination)
		return content
		
	def fileInfo(self, destination):
		destination = self._absolutePath(destination)
		info = {}
		try:
			fs = os.stat(destination)
			info['size'] = fs[stat.ST_SIZE]
			return info
		except Exception, e:
			raise RepositoryError(u"Failed to get file info for '%s': %s" % (destination, e))
	
	def download(self, source, destination, progressObserver=None):
		size = self.fileInfo(source)['size']
		source = self._absolutePath(source)
		destination = forceUnicode(destination)
		
		logger.debug(u"Length of binary data to download: %d" % size)
		
		progressSubject = ProgressSubject(id='download', end=size)
		progressSubject.setMessage( os.path.basename(source) + ' >> ' + self._path )
		
		if progressObserver: progressSubject.attachObserver(progressObserver)
		
		(src, dst) = (None, None)
		try:
			src = open(source, 'rb')
			dst = open(destination, 'wb')
			self._transfer(src, dst, progressSubject)
			src.close()
			dst.close()
		except Exception, e:
			if src: src.close()
			if dst: dst.close()
			raise RepositoryError(u"Failed to download '%s' to '%s': %s" \
						% (source, destination, e))
	
	def upload(self, source, destination, progressObserver=None):
		source = forceUnicode(source)
		destination = self._absolutePath(destination)
		
		fs = os.stat(source)
		size = fs[stat.ST_SIZE]
		logger.debug(u"Length of binary data to upload: %d" % size)
		
		progressSubject = ProgressSubject(id='upload', end=size)
		progressSubject.setMessage( os.path.basename(source) + u' >> ' + self._path )
		
		if progressObserver: progressSubject.attachObserver(progressObserver)
		
		(src, dst) = (None, None)
		try:
			src = open(source, 'rb')
			dst = open(destination, 'wb')
			self._transfer(src, dst, progressSubject)
			src.close()
			dst.close()
		except Exception, e:
			if src: src.close()
			if dst: dst.close()
			raise RepositoryError(u"Failed to upload '%s' to '%s': %s" \
						% (source, destination, e))
	
	def delete(self, estination):
		destination = self._absolutePath(destination)
		os.unlink(destination)
	
	def makeDirectory(self, destination):
		destination = self._absolutePath(destination)
		if not os.path.isdir(destination):
			os.mkdir(destination)
		
	
class WebDAVRepository(Repository):
	def __init__(self, url, username=u'', password=u'', maxBandwidth=0):
		Repository.__init__(self, url, username, password, maxBandwidth)
		
		match = re.search('^(webdavs*)://([^:]+:*[^:]+):(\d+)(/.*)$', self._url)
		if not match:
			raise RepositoryError(u"Bad url: '%s'" % self._url)
		
		self._protocol = match.group(1)
		self._host = match.group(2)
		if (self._host.find('@') != -1):
			(username, self._host) = self._host.split('@', 1)
			password = ''
			if (username.find(':') != -1):
				(username, password) = username.split(':', 1)
			if not self._username and username: self._username = username
			if not self._password and password: self._password = password
		self._port = forceInt(match.group(3))
		self._path = match.group(4)
		self._auth = 'Basic '+ base64.encodestring( urllib.unquote(self._username + ':' + self._password) ).strip()
		self._connection = None
		self._cookie = ''
		
	def _absolutePath(self, destination):
		destination = forceUnicode(destination)
		if destination.startswith('/'):
			destination = destination[1:]
		return self._path + '/' + destination
	
	def _connect(self):
		logger.debug(u"WebDAVRepository _connect()")
		if self._protocol.endswith('s'):
			self._connection = HTTPSConnection(self._host, self._port)
		else:
			self._connection = HTTPConnection(self._host, self._port)
		
		self._connection.putrequest('PROPFIND', urllib.quote(self._absolutePath('/')))
		if self._cookie:
			# Add cookie to header
			self._connection.putheader('cookie', self._cookie)
		self._connection.putheader('authorization', self._auth)
		self._connection.putheader('depth', '0')
		self._connection.endheaders()
		
		response = self._connection.getresponse()
		if (response.status != responsecode.MULTI_STATUS):
			raise RepositoryError(u"Failed to connect to '%s://%s:%s': %s" \
				% (self._protocol, self._host, self._port, response.status))
		# We have to read the response!
		response.read()
		
		# Get cookie from header
		cookie = response.getheader('set-cookie', None)
		if cookie:
			# Store cookie 
			self._cookie = cookie.split(';')[0].strip()
	
	def _getContent(self, destination=''):
		destination = forceUnicode(destination)
		content = []
		if not destination.endswith('/'):
			destination += '/'
		
		self._connect()
		
		self._connection.putrequest('PROPFIND', urllib.quote(destination))
		self._connection.putheader('depth', '1')
		if self._cookie:
			# Add cookie to header
			self._connection.putheader('cookie', self._cookie)
		self._connection.putheader('authorization', self._auth)
		self._connection.endheaders()
		
		response = self._connection.getresponse()
		if (response.status != responsecode.MULTI_STATUS):
			raise RepositoryError(u"Failed to list dir '%s': %s" \
				% (destination, response.status))
		
		msr = davxml.WebDAVDocument.fromString(response.read())
		if not msr.root_element.children[0].childOfType(davxml.PropertyStatus).childOfType(davxml.PropertyContainer).childOfType(davxml.ResourceType).children:
			raise RepositoryError(u"Not a directory: '%s'" % destination)
		for child in msr.root_element.children[1:]:
			#<prop>
			#	<resourcetype/>
			#	<getetag>W/"1737A0-373-47DFF2F3"</getetag>
			#	<getcontenttype>text/plain</getcontenttype>
			#	<getcontentlength>883</getcontentlength>
			#	<getlastmodified>Tue, 18 Mar 2008 17:50:59 GMT</getlastmodified>
			#	<creationdate>2008-03-18T17:50:59Z</creationdate>
			#	<displayname>connect.vnc</displayname>
			#</prop>
			pContainer = child.childOfType(davxml.PropertyStatus).childOfType(davxml.PropertyContainer)
			info = { 'size': long(0), 'type': 'file' }
			info['name'] = str(pContainer.childOfType(davxml.DisplayName))
			if (str(pContainer.childOfType(davxml.GETContentLength)) != 'None'):
				info['size'] = long( str(pContainer.childOfType(davxml.GETContentLength)) )
			if pContainer.childOfType(davxml.ResourceType).children:
				info['type'] = 'dir'
			
			content.append(info)
		
		return content
	
	def content(self, destination=u''):
		result = []
		destination = self._absolutePath(destination)
		#for c in self._getContent(destination):
		#	result.append( c['name'] )
		return self._getContent(destination)
		return result
	
	def fileInfo(self, destination):
		destination = forceUnicode(destination)
		info = {}
		try:
			path = self._absolutePath(u'/'.join(destination.split('/')[:-1]))
			name = destination.split('/')[-1]
			for c in self._getContent(path):
				if (c['name'] == name):
					info['size'] = c['size']
					return info
			raise Exception(u'File not found')
		except Exception, e:
			raise RepositoryError(u"Failed to get file info for '%s': %s" % (destination, e))
	
	def download(self, source, destination, progressObserver=None):
		destination = forceUnicode(destination)
		size = self.fileInfo(source)['size']
		source = self._absolutePath(source)
		
		logger.debug(u"Length of binary data to download: %d" % size)
		
		progressSubject = ProgressSubject(id='upload', end=size)
		progressSubject.setMessage( os.path.basename(source) + u' >> ' + self._path )
		
		if progressObserver: progressSubject.attachObserver(progressObserver)
		
		dst = None
		try:
			self._connect()
			self._connection.putrequest('GET', urllib.quote(source))
			if self._cookie:
				# Add cookie to header
				self._connection.putheader('cookie', self._cookie)
			self._connection.putheader('authorization', self._auth)
			self._connection.endheaders()
			
			response = self._connection.getresponse()
			if (response.status != responsecode.OK):
				raise Exception(response.status)
			
			dst = open(destination, 'wb')
			self._transfer(response, dst, progressSubject)
			dst.close()
			
		except Exception, e:
			logger.logException(e)
			#if self._connection: self._connection.close()
			if dst: dst.close()
			raise RepositoryError(u"Failed to download '%s' to '%s': %s" \
						% (source, destination, e))
		logger.debug2(u"WebDAV download done")
	
	def upload(self, source, destination, progressObserver=None):
		source = forceUnicode(source)
		destination = self._absolutePath(destination)
		
		fs = os.stat(source)
		size = fs[stat.ST_SIZE]
		logger.debug(u"Length of binary data to upload: %d" % size)
		
		progressSubject = ProgressSubject(id='upload', end=size)
		progressSubject.setMessage( os.path.basename(source) + u' >> ' + self._path )
		
		if progressObserver: progressSubject.attachObserver(progressObserver)
		
		src = None
		try:
			self._connect()
			self._connection.putrequest('PUT', urllib.quote(destination))
			if self._cookie:
				# Add cookie to header
				self._connection.putheader('cookie', self._cookie)
			self._connection.putheader('authorization', self._auth)
			self._connection.putheader('content-length', size)
			self._connection.endheaders()
			
			src = open(source, 'rb')
			self._transfer(src, self._connection, progressSubject)
			src.close()
			
			response = self._connection.getresponse()
			if (response.status != responsecode.CREATED) and (response.status != responsecode.NO_CONTENT):
				raise Exception(response.status)
			# We have to read the response!
			response.read()
		except Exception, e:
			logger.logException(e)
			#if self._connection: self._connection.close()
			if src: src.close()
			raise RepositoryError(u"Failed to upload '%s' to '%s': %s" \
						% (source, destination, e))
		logger.debug2(u"WebDAV upload done")
	
	def delete(self, destination):
		self._connect()
		
		destination = self._absolutePath(destination)
		
		self._connection.putrequest('DELETE', urllib.quote(destination))
		if self._cookie:
			# Add cookie to header
			self._connection.putheader('cookie', self._cookie)
		self._connection.putheader('authorization', self._auth)
		self._connection.endheaders()
		
		response = self._connection.getresponse()
		if (response.status != responsecode.NO_CONTENT):
			raise RepositoryError(u"Failed to delete '%s': %s" \
				% (destination, response.status))
		# We have to read the response!
		response.read()


class DepotToLocalDirectorySychronizer(object):
	def __init__(self, sourceDepot, destinationDirectory, productIds=[], maxBandwidth=0):
		self._sourceDepot = sourceDepot
		self._destinationDirectory = forceUnicode(destinationDirectory)
		self._productIds = forceUnicodeList(productIds)
		self._maxBandwidth = forceInt(maxBandwidth)
		if not os.path.isdir(self._destinationDirectory):
			os.mkdir(self._destinationDirectory)
	
	def _md5sum(self, filename):
		f = open(filename, 'rb')
		m = md5()
		while True:
			d = f.read(8096)
			if not d:
				break
			m.update(d)
		f.close()
		return m.hexdigest()
	
	def _synchronizeDirectories(self, source, destination, progressSubject=None):
		source = forceUnicode(source)
		destination = forceUnicode(destination)
		logger.debug(u"   Syncing directory %s to %s" % (source, destination))
		if not os.path.isdir(destination):
			os.mkdir(destination)
		
		for f in os.listdir(destination):
			relSource = (source + '/' + f).split('/', 1)[1]
			if (relSource == self._productId + u'.files'):
				continue
			if self._fileInfo.has_key(relSource):
				continue
			
			logger.info(u"      Deleting '%s'" % relSource)
			path = os.path.join(destination, f)
			if os.path.isdir(path) and not os.path.islink(path):
				shutil.rmtree(path)
			else:
				os.remove(path)
			
		for f in self._sourceDepot.content(source):
			source = forceUnicode(source)
			(s, d) = (source + u'/' + f['name'], os.path.join(destination, f['name']))
			relSource = s.split(u'/', 1)[1]
			if not self._fileInfo.has_key(relSource):
				continue
			if (f['type'] == 'dir'):
				self._synchronizeDirectories(s, d, progressSubject)
			else:
				bytes = 0
				logger.debug(u"      Syncing %s: %s" % (relSource, self._fileInfo[relSource]))
				if (self._fileInfo[relSource]['type'] == 'l'):
					self._linkFiles[relSource] = self._fileInfo[relSource]['target']
					continue
				elif (self._fileInfo[relSource]['type'] == 'f'):
					bytes = int(self._fileInfo[relSource]['size'])
					if os.path.exists(d):
						md5s = self._md5sum(d)
						logger.debug(u"      Destination file '%s' already exists (size: %s, md5sum: %s)" % (d, bytes, md5s))
						if (os.path.getsize(d) == bytes) and (md5s == self._fileInfo[relSource]['md5sum']):
							if progressSubject: progressSubject.addToState(bytes)
							continue
				logger.info(u"      Downloading file '%s'" % f['name'])
				if progressSubject: progressSubject.setMessage( _(u"Downloading file '%s'") % f['name'] )
				self._sourceDepot.download(s, d)
				if progressSubject: progressSubject.addToState(bytes)
				
	def synchronize(self, productProgressObserver=None, overallProgressObserver=None):
		
		if not self._productIds:
			logger.info(u"Getting product dirs of depot '%s'" % self._sourceDepot)
			for c in self._sourceDepot.content():
				self._productIds.append(c['name'])
		
		overallProgressSubject = ProgressSubject(id = 'sync_products_overall', type = 'product_sync', end = len(self._productIds), fireAlways = True)
		overallProgressSubject.setMessage( _(u'Synchronizing products') )
		if overallProgressObserver: overallProgressSubject.attachObserver(overallProgressObserver)
		
		for self._productId in self._productIds:
			productProgressSubject = ProgressSubject(id = 'sync_product_' + self._productId, type = 'product_sync', fireAlways = True)
			productProgressSubject.setMessage( _(u"Synchronizing product %s") % self._productId )
			if productProgressObserver: productProgressSubject.attachObserver(productProgressObserver)
			
			self._linkFiles = {}
			logger.notice(u"Syncing product %s of depot %s with local directory %s" \
					% (self._productId, self._sourceDepot, self._destinationDirectory))
			
			productDestinationDirectory = os.path.join(self._destinationDirectory, self._productId)
			if not os.path.isdir(productDestinationDirectory):
				os.mkdir(productDestinationDirectory)
			
			logger.info(u"Downloading file info file")
			from OPSI import Product
			fileInfoFile = os.path.join(productDestinationDirectory, u'%s.files' % self._productId)
			self._sourceDepot.download(u'%s/%s.files' % (self._productId, self._productId), fileInfoFile)
			self._fileInfo = Product.readFileInfoFile(fileInfoFile)
			
			bytes = 0
			for value in self._fileInfo.values():
				if value.has_key('size'):
					bytes += int(value['size'])
			productProgressSubject.setMessage( _(u"Synchronizing product %s (%.2f kByte)") % (self._productId, (bytes/1024)) )
			productProgressSubject.setEnd(bytes)
			
			self._synchronizeDirectories(self._productId, productDestinationDirectory, productProgressSubject)
			
			fs = self._linkFiles.keys()
			fs.sort()
			for f in fs:
				t = self._linkFiles[f]
				cwd = os.getcwd()
				os.chdir(productDestinationDirectory)
				try:
					if os.path.exists(f):
						if os.path.isdir(f) and not os.path.islink(f):
							shutil.rmtree(f)
						else:
							os.remove(f)
					if (os.name == 'posix'):
						parts = len(f.split('/'))
						parts -= len(t.split('/'))
						for i in range(parts):
							t = os.path.join('..', t)
						logger.info(u"Symlink '%s' to '%s'" % (f, t))
						os.symlink(t, f)
					else:
						t = os.path.join(productDestinationDirectory, t)
						f = os.path.join(productDestinationDirectory, f)
						logger.info(u"Copying '%s' to '%s'" % (t, f))
						if os.path.isdir(t):
							shutil.copytree(t, f)
						else:
							shutil.copyfile(t, f)
				finally:
					os.chdir(cwd)
			overallProgressSubject.addToState(1)
			if productProgressObserver: productProgressSubject.detachObserver(productProgressObserver)
		
		if overallProgressObserver: overallProgressSubject.detachObserver(overallProgressObserver)







